"""Punto de entrada de `alert_ingestor`: un worker en bucle, sin superficie HTTP
propia — este servicio alimenta eventos internos, no los expone (ver
`docs/architecture/OVERVIEW.md` §11: "alert_ingestor (SGC/CAP/USGS → evento
interno)"). Notificar a otros servicios (`EventBusPort`/`NotificationPort`) queda
fuera de este cambio: hoy no hay Redis ni FCM cableados en ningún servicio del
monorepo, y esto se limita a registrar la decisión.

Arranque:

    python -m alert_ingestor.bootstrap.main

Variables de entorno:

| Variable | Para qué | Si falta |
|---|---|---|
| `ALERT_INGESTOR_POLL_INTERVAL_S` | Segundos entre ciclos de ingesta | 15 |

SGC no se cablea aquí todavía: `SgcFeedSource` no tiene parser confirmado (ver
`adapters/sources/sgc.py`) y añadirlo sin uno solo produciría un
`NotImplementedError` en el primer ciclo.
"""

from __future__ import annotations

import asyncio
import logging
import os

from alert_ingestor.adapters.clock import SystemClock
from alert_ingestor.adapters.http import HttpxClient
from alert_ingestor.adapters.ids import SecureIdGenerator
from alert_ingestor.adapters.persistence.memory import InMemoryIncidentRepository
from alert_ingestor.adapters.sources.emsc import EMSC_WEBSOCKET_URL, EmscWebSocketSource
from alert_ingestor.adapters.sources.usgs import UsgsFeedSource
from alert_ingestor.adapters.websocket import WebsocketsConnector
from alert_ingestor.application.ingest import AlertIngestionService

logger = logging.getLogger("alert_ingestor")

DEFAULT_POLL_INTERVAL_S = 15.0


def build_service() -> tuple[AlertIngestionService, list[asyncio.Task]]:
    """Cablea las fuentes reales disponibles hoy (EMSC + USGS).

    SGC se añade aparte y solo si `ALERT_INGESTOR_SGC_URL` está definida — sin
    endpoint confirmado no tiene sentido intentar conectarla (ver
    `adapters/sources/sgc.py`).
    """
    clock = SystemClock()
    connector = WebsocketsConnector(EMSC_WEBSOCKET_URL)
    emsc = EmscWebSocketSource(connector, clock)
    usgs = UsgsFeedSource(HttpxClient(), clock)

    background_tasks = [asyncio.create_task(emsc.run(), name="emsc-websocket")]

    service = AlertIngestionService(
        sources=[emsc, usgs],
        repository=InMemoryIncidentRepository(),
        clock=clock,
        ids=SecureIdGenerator(),
    )
    return service, background_tasks


async def run_forever(interval_s: float = DEFAULT_POLL_INTERVAL_S) -> None:
    service, background_tasks = build_service()
    logger.info("alert_ingestor arrancado — ciclo cada %.0fs", interval_s)
    try:
        while True:
            result = await service.run_cycle()
            for error in result.errors:
                logger.warning("fuente %s no disponible: %s", error.source, error.message)
            for decision in result.new_activations:
                logger.warning(
                    "ACTIVACIÓN: incidente %s — %s",
                    decision.incident.id,
                    decision.reason,
                )
            await asyncio.sleep(interval_s)
    finally:
        for task in background_tasks:
            task.cancel()


def main() -> None:
    logging.basicConfig(level=logging.INFO)
    interval = float(os.environ.get("ALERT_INGESTOR_POLL_INTERVAL_S", DEFAULT_POLL_INTERVAL_S))
    asyncio.run(run_forever(interval))


if __name__ == "__main__":
    main()
