"""Repositorio en memoria. *Fake* determinista y, hoy, también el único adaptador
real: no hay una base de datos que integrar todavía (ver README — la persistencia
definitiva vive en `services/shared` una vez sea instalable)."""

from __future__ import annotations

from alert_ingestor.application.ports import IncidentRepository
from alert_ingestor.domain.models import SeismicIncident


class InMemoryIncidentRepository(IncidentRepository):
    def __init__(self) -> None:
        self._by_id: dict[str, SeismicIncident] = {}

    async def upsert(self, incident: SeismicIncident) -> None:
        self._by_id[incident.id] = incident

    async def recent(self, *, since_ms: int) -> list[SeismicIncident]:
        return [
            inc
            for inc in self._by_id.values()
            if any(r.received_at >= since_ms for r in inc.all_reports)
        ]

    def get(self, incident_id: str) -> SeismicIncident | None:
        """Solo para tests: acceso directo sin pasar por `recent()`."""
        return self._by_id.get(incident_id)
