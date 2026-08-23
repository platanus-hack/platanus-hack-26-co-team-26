"""Modelo de dominio: un evento sísmico reportado por una fuente, y el incidente
candidato en el que uno o varios reportes se consolidan.

Dos capas deliberadamente separadas:

- `RawSeismicEvent` — lo que UNA fuente reportó. EMSC, USGS y SGC casi nunca
  coinciden exactamente en magnitud, epicentro u hora de origen para el mismo
  sismo, sobre todo en los primeros minutos.
- `SeismicIncident` — el evento físico consolidado al que uno o más reportes
  probablemente corresponden (`domain/dedup.py` decide cuáles). Es lo que dispara
  o no una activación (`domain/activation.py`).

Dueño: Miguel.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum


class SeismicSource(StrEnum):
    """Origen del reporte. Cerrado a las tres fuentes contempladas en el README."""

    EMSC = "emsc"
    """European-Mediterranean Seismological Centre — feed en tiempo casi real."""
    USGS = "usgs"
    """U.S. Geological Survey — cobertura global, feed GeoJSON/CAP cada minuto."""
    SGC = "sgc"
    """Servicio Geológico Colombiano — fuente oficial para sismos en Colombia."""
    MANUAL = "manual"
    """Activación manual por un operador (`protocol/openapi` /v1/alerts/manual)."""


class EventStatus(StrEnum):
    """Madurez del reporte, tal como la declara la fuente."""

    AUTOMATIC = "automatic"
    """Detección algorítmica, sin revisión humana. La primera versión de un evento."""
    REVIEWED = "reviewed"
    """Un sismólogo revisó y ajustó los parámetros."""
    MANUAL = "manual"


@dataclass(frozen=True, slots=True)
class RawSeismicEvent:
    """Un reporte, tal como lo entregó una fuente, ya traducido a esta forma común.

    `raw` conserva el payload original de la fuente — no para reprocesarlo en caliente,
    sino para poder auditar después por qué una decisión de activación salió como
    salió, sin tener que confiar en que la normalización fue perfecta.
    """

    source: SeismicSource
    external_id: str
    """Identificador propio de la fuente. Único dentro de esa fuente, no entre fuentes."""
    magnitude: float
    magnitude_type: str
    """`Mw`, `ML`, `mb`, `Md`... Cada red mide con una escala distinta."""
    lat: float
    lon: float
    depth_km: float | None
    occurred_at: int
    """Epoch ms del origen del sismo (no de cuándo se recibió el reporte)."""
    received_at: int
    """Epoch ms en que este servicio ingirió el reporte. Mide la latencia real."""
    status: EventStatus
    place: str = ""
    url: str | None = None
    raw: dict = field(default_factory=dict, repr=False)

    @property
    def latency_ms(self) -> int:
        """Cuánto tardó la fuente en entregarnos el evento desde que ocurrió."""
        return max(0, self.received_at - self.occurred_at)


@dataclass(frozen=True, slots=True)
class SeismicIncident:
    """Evento físico consolidado — lo que probablemente sea el mismo sismo.

    `primary` es el reporte usado para los parámetros que se muestran (el de mayor
    prioridad de fuente, ver `dedup.SOURCE_PRIORITY`); `corroborating` son los demás
    reportes que el deduplicador decidió que describen el mismo evento.
    """

    id: str
    primary: RawSeismicEvent
    corroborating: tuple[RawSeismicEvent, ...] = ()

    @property
    def all_reports(self) -> tuple[RawSeismicEvent, ...]:
        return (self.primary, *self.corroborating)

    @property
    def sources(self) -> frozenset[SeismicSource]:
        return frozenset(r.source for r in self.all_reports)

    @property
    def source_count(self) -> int:
        return len(self.sources)

    @property
    def magnitude(self) -> float:
        """La mayor magnitud reportada. Subestimar la severidad es el error caro."""
        return max(r.magnitude for r in self.all_reports)

    @property
    def occurred_at(self) -> int:
        return self.primary.occurred_at

    @property
    def first_seen_at(self) -> int:
        """Cuándo se supo por primera vez de este evento, por cualquier fuente."""
        return min(r.received_at for r in self.all_reports)

    def merged_with(
        self, report: RawSeismicEvent, *, select_primary
    ) -> SeismicIncident:
        """Nueva instancia con `report` incorporado, recalculando cuál reporte es `primary`.

        `select_primary` se inyecta (en vez de importar `dedup.SOURCE_PRIORITY` aquí)
        para que el dominio de modelos no dependa del módulo de deduplicación.

        Se recalcula sobre **todos** los reportes en cada fusión, no solo se
        conserva el primero que llegó: así el resultado es el mismo sin importar en
        qué orden lleguen EMSC, USGS y SGC. Si SOURCE_PRIORITY se congelara en el
        primer reporte, un SGC que confirma un evento ya visto por EMSC nunca
        pasaría a mandar, que es justo lo que SOURCE_PRIORITY pretende evitar.
        """
        already_seen = {
            (r.source, r.external_id) for r in self.all_reports
        }
        if (report.source, report.external_id) in already_seen:
            return self  # la misma fuente reenvió una actualización ya vista

        reports = (*self.all_reports, report)
        primary = select_primary(reports)
        corroborating = tuple(r for r in reports if r is not primary)
        return SeismicIncident(id=self.id, primary=primary, corroborating=corroborating)


@dataclass(frozen=True, slots=True)
class ActivationPolicy:
    """Umbrales de activación. `ASSUMED` — ver `docs/validation/` para calibrarlos
    con datos reales, igual que los pesos de `protocol/docs/PRIORITIES.md`.
    """

    min_magnitude_single_source: float = 4.5
    """Magnitud que activa aunque solo la reporte una fuente."""
    min_magnitude_corroborated: float = 3.5
    """Magnitud menor pero ya confirmada por varias fuentes independientes."""
    min_corroborating_sources: int = 2
    """Fuentes independientes necesarias para usar el umbral corroborado."""


@dataclass(frozen=True, slots=True)
class ActivationDecision:
    """Resultado de evaluar un incidente contra la política."""

    incident: SeismicIncident
    should_activate: bool
    reason: str
    policy: ActivationPolicy
