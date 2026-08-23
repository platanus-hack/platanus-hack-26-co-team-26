"""Orquestador: consulta cada fuente, deduplica, decide activación.

Un ciclo de ingesta (`run_cycle`) es la unidad que `bootstrap/main.py` llama en
bucle. Se diseñó como una llamada única y no como un bucle infinito interno para
que sea trivial de probar: un test llama `run_cycle` una o dos veces con fuentes
*fake* y afirma sobre el resultado, sin `asyncio.sleep` ni temporizadores.

Dueño: Miguel.
"""

from __future__ import annotations

from dataclasses import dataclass

from alert_ingestor.application.ports import (
    AlertSourcePort,
    Clock,
    IdGenerator,
    IncidentRepository,
)
from alert_ingestor.domain.activation import decide_activation
from alert_ingestor.domain.dedup import Deduplicator, DedupWindow
from alert_ingestor.domain.errors import SourceUnavailable
from alert_ingestor.domain.models import ActivationDecision, ActivationPolicy, SeismicIncident

#: Cuánto conservar un incidente en memoria tras su último reporte antes de darlo
#: por cerrado. Más allá de esto, una réplica tardía se trataría como evento nuevo
#: — aceptable: las réplicas sí son eventos nuevos.
STALE_INCIDENT_WINDOW_MS = 30 * 60_000


@dataclass(frozen=True, slots=True)
class SourceError:
    source: str
    message: str


@dataclass(frozen=True, slots=True)
class CycleResult:
    touched_incidents: tuple[SeismicIncident, ...] = ()
    """Incidentes con novedad en este ciclo (nuevos o con un reporte adicional)."""
    new_activations: tuple[ActivationDecision, ...] = ()
    """Solo las activaciones que **cruzaron el umbral en este ciclo** — no se repite
    una activación ya emitida en un ciclo anterior para el mismo incidente."""
    errors: tuple[SourceError, ...] = ()
    """Fuentes que fallaron en este ciclo. Una fuente caída no detiene a las demás."""


class AlertIngestionService:
    def __init__(
        self,
        *,
        sources: list[AlertSourcePort],
        repository: IncidentRepository,
        clock: Clock,
        ids: IdGenerator,
        policy: ActivationPolicy | None = None,
        dedup_window: DedupWindow | None = None,
    ) -> None:
        self._sources = sources
        self._repository = repository
        self._clock = clock
        self._ids = ids
        self._policy = policy or ActivationPolicy()
        self._dedup = Deduplicator(dedup_window)
        self._activated: set[str] = set()

    async def run_cycle(self) -> CycleResult:
        now = self._clock.now_ms()
        errors: list[SourceError] = []
        touched: list[SeismicIncident] = []

        for source in self._sources:
            try:
                events = await source.poll()
            except SourceUnavailable as exc:
                errors.append(SourceError(source=source.name, message=str(exc)))
                continue

            for event in events:
                incident = self._dedup.ingest(event, new_id=self._ids.new_id())
                await self._repository.upsert(incident)
                touched.append(incident)

        new_activations: list[ActivationDecision] = []
        for incident in touched:
            if incident.id in self._activated:
                continue
            decision = decide_activation(incident, self._policy)
            if decision.should_activate:
                self._activated.add(incident.id)
                new_activations.append(decision)

        self._dedup.forget_older_than(cutoff_ms=now - STALE_INCIDENT_WINDOW_MS)

        return CycleResult(
            touched_incidents=tuple(touched),
            new_activations=tuple(new_activations),
            errors=tuple(errors),
        )
