"""EMSC — Seismic Portal, servicio de "standing order" por WebSocket.

Documentación: https://www.seismicportal.eu/realtime.html
Endpoint: wss://www.seismicportal.eu/standing_order/websocket

Es la fuente más rápida de las tres: empuja el evento en segundos, antes incluso
de que la magnitud esté afinada — por eso conviene tratarla como primera señal y
no como fuente autoritativa (`dedup.SOURCE_PRIORITY` la deja detrás de SGC y
USGS para decidir qué reporte manda, pero no para decidir qué tan rápido se
entera el sistema de que algo pasó).

Cada mensaje es un JSON con `action` ("create"/"update"/"delete") y `data`
(un GeoJSON `Feature`). Este adaptador ignora `"delete"` — es una retractación de
un evento falso positivo, y manejarla correctamente exigiría poder retirar un
incidente ya creado, lo que excede el alcance de este puerto (`poll()` solo
añade). Queda anotado como limitación conocida, no como un caso silenciosamente
tratado igual que los demás.

`poll()` no abre la conexión: drena lo que `run()` haya acumulado en un buffer
interno desde la última llamada. Se separa así a propósito — permite testear el
parseo sin un WebSocket real y sin temporizadores (`run()` sobre un
`FakeConnector` finito termina solo).

Dueño: Miguel.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime

from alert_ingestor.application.ports import AlertSourcePort, Clock, WebSocketConnector
from alert_ingestor.domain.errors import MalformedEvent
from alert_ingestor.domain.models import EventStatus, RawSeismicEvent, SeismicSource

EMSC_WEBSOCKET_URL = "wss://www.seismicportal.eu/standing_order/websocket"


class EmscWebSocketSource(AlertSourcePort):
    name = "emsc"

    def __init__(self, connector: WebSocketConnector, clock: Clock) -> None:
        self._connector = connector
        self._clock = clock
        self._buffer: list[RawSeismicEvent] = []

    async def run(self) -> None:
        """Consume el feed y acumula eventos parseados en el buffer interno.

        Sobre el conector real esto no termina — se pensó para correr como tarea
        de fondo (`asyncio.create_task`) mientras `poll()` se llama periódicamente
        desde el ciclo de ingesta. Sobre un `FakeConnector` (finito) sí termina,
        que es lo que permite probarlo con un `await` normal.
        """
        async for raw_message in self._connector.messages():
            try:
                event = self._parse(raw_message, received_at=self._clock.now_ms())
            except MalformedEvent:
                continue  # un mensaje malformado no debe tumbar la conexión
            if event is not None:
                self._buffer.append(event)

    async def poll(self) -> list[RawSeismicEvent]:
        drained, self._buffer = self._buffer, []
        return drained

    @staticmethod
    def _parse(raw_message: str, *, received_at: int) -> RawSeismicEvent | None:
        try:
            envelope = json.loads(raw_message)
        except json.JSONDecodeError as exc:
            raise MalformedEvent(f"mensaje EMSC no es JSON válido: {exc}") from exc

        action = envelope.get("action")
        if action == "delete":
            return None  # ver limitación documentada arriba

        try:
            data = envelope["data"]
            props = data["properties"]
            lon, lat, neg_depth = data["geometry"]["coordinates"]
            occurred_at = int(
                datetime.strptime(props["time"], "%Y-%m-%dT%H:%M:%S.%fZ")
                .replace(tzinfo=UTC)
                .timestamp()
                * 1000
            )
            return RawSeismicEvent(
                source=SeismicSource.EMSC,
                external_id=str(data.get("id") or props["unid"]),
                magnitude=float(props["mag"]),
                magnitude_type=props.get("magtype") or "unknown",
                lat=float(lat),
                lon=float(lon),
                depth_km=abs(float(neg_depth)) if neg_depth is not None else None,
                occurred_at=occurred_at,
                received_at=received_at,
                status=EventStatus.AUTOMATIC,
                place=props.get("flynn_region") or "",
                url=None,
                raw=envelope,
            )
        except (KeyError, TypeError, ValueError, IndexError) as exc:
            raise MalformedEvent(f"evento EMSC malformado: {exc}") from exc
