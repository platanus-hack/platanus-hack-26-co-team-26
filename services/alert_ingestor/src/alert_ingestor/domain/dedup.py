"""Deduplicación entre fuentes: ¿estos reportes describen el mismo sismo?

El problema real: EMSC, USGS y SGC casi nunca coinciden en los primeros minutos.
Magnitud, epicentro y hasta la hora de origen difieren porque cada red usa sus
propias estaciones y algoritmos, y las primeras estimaciones automáticas se
revisan después. Sin deduplicar, un solo sismo dispararía tres "incidentes"
independientes y, peor, tres activaciones.

La estrategia es una ventana espacio-temporal generosa a propósito: es preferible
fusionar de más en el primer minuto (y desduplicar mejor cuando lleguen versiones
revisadas) que activar tres veces el mismo evento.

Dueño: Miguel.
"""

from __future__ import annotations

from dataclasses import dataclass

from alert_ingestor.domain.geo import haversine_km
from alert_ingestor.domain.models import RawSeismicEvent, SeismicIncident, SeismicSource

#: Orden de preferencia para decidir qué reporte es `primary` de un incidente
#: nuevo. SGC manda para eventos en territorio colombiano por ser la autoridad
#: local (Ley y ADR aparte: es simplemente quien mejor instrumenta la región);
#: EMSC suele llegar primero pero con parámetros menos afinados; USGS aporta
#: cobertura y buena revisión posterior. `ASSUMED` — a calibrar con datos reales.
SOURCE_PRIORITY: dict[SeismicSource, int] = {
    SeismicSource.SGC: 0,
    SeismicSource.USGS: 1,
    SeismicSource.EMSC: 2,
    SeismicSource.MANUAL: 3,
}


@dataclass(frozen=True, slots=True)
class DedupWindow:
    """Tolerancias para considerar dos reportes el mismo evento físico.

    `ASSUMED` — ver `docs/validation/`. Generosas a propósito: los valores por
    defecto priorizan no duplicar sobre no fusionar de más, porque el costo de una
    activación repetida es mayor que el de una corroboración de más en un incidente
    que de todas formas iba a activarse.
    """

    time_window_ms: int = 120_000
    """±2 min de diferencia entre horas de origen reportadas."""
    max_distance_km: float = 200.0
    """Las primeras estimaciones de epicentro entre redes pueden diferir mucho."""
    max_magnitude_delta: float = 1.5
    """Diferencia de magnitud tolerada entre fuentes para el mismo evento."""


def same_event(a: RawSeismicEvent, b: RawSeismicEvent, window: DedupWindow) -> bool:
    """¿`a` y `b` son, con margen amplio, el mismo sismo?"""
    if abs(a.occurred_at - b.occurred_at) > window.time_window_ms:
        return False
    if haversine_km(a.lat, a.lon, b.lat, b.lon) > window.max_distance_km:
        return False
    return abs(a.magnitude - b.magnitude) <= window.max_magnitude_delta


def select_primary(reports: tuple[RawSeismicEvent, ...] | list[RawSeismicEvent]) -> RawSeismicEvent:
    """Cuál de varios reportes del mismo evento debe ser el `primary`.

    Prioridad de fuente primero (`SOURCE_PRIORITY`); a igual prioridad, el que
    llegó antes. Se aplica sobre el conjunto completo de reportes en cada fusión
    (ver `SeismicIncident.merged_with`), nunca solo sobre el más reciente.
    """
    return min(reports, key=lambda r: (SOURCE_PRIORITY.get(r.source, 99), r.received_at))


class Deduplicator:
    """Mantiene los incidentes recientes y decide si un reporte nuevo es un evento
    nuevo o corrobora uno ya visto.

    Sin estado externo: quien orquesta (`application/ingest.py`) decide cuánto
    tiempo conservar los incidentes en memoria antes de descartarlos.
    """

    def __init__(self, window: DedupWindow | None = None) -> None:
        self._window = window or DedupWindow()
        self._incidents: dict[str, SeismicIncident] = {}

    def ingest(self, report: RawSeismicEvent, *, new_id: str) -> SeismicIncident:
        """Registra `report` y devuelve el incidente (nuevo o corroborado) que resulta.

        `new_id` lo genera quien llama (vía `IdGenerator`, no el dominio): el
        dominio no decide cómo se ven los identificadores, solo la lógica de fusión.
        """
        for incident in self._incidents.values():
            if same_event(incident.primary, report, self._window):
                merged = incident.merged_with(report, select_primary=select_primary)
                self._incidents[incident.id] = merged
                return merged

        incident = SeismicIncident(id=new_id, primary=report)
        self._incidents[incident.id] = incident
        return incident

    def recent(self, *, since_ms: int) -> list[SeismicIncident]:
        """Incidentes con al menos un reporte visto desde `since_ms`."""
        return [
            inc
            for inc in self._incidents.values()
            if any(r.received_at >= since_ms for r in inc.all_reports)
        ]

    def forget_older_than(self, *, cutoff_ms: int) -> None:
        """Libera incidentes cuyo último reporte es anterior a `cutoff_ms`.

        Sin esto, un proceso de larga vida acumularía en memoria cada sismo desde
        que arrancó. La ventana de deduplicación ya cerró para ellos de todas formas.
        """
        stale = [
            inc_id
            for inc_id, inc in self._incidents.items()
            if max(r.received_at for r in inc.all_reports) < cutoff_ms
        ]
        for inc_id in stale:
            del self._incidents[inc_id]
