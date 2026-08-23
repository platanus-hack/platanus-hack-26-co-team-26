"""USGS Earthquake Hazards Program — feed GeoJSON público, sin API key.

Documentación: https://earthquake.usgs.gov/earthquakes/feed/v1.0/geojson.php
Feed por defecto: `all_hour.geojson` — todos los sismos detectados en la última
hora, revisado por USGS cada minuto aproximadamente. Otros feeds disponibles
(`all_day`, `significant_week`, `2.5_hour`, ...) se seleccionan por nombre.

Cada `feature` trae un `id` estable y una marca `updated` (epoch ms) que cambia
cuando USGS revisa el evento (p. ej. ajusta la magnitud). Este adaptador solo
devuelve entradas nuevas o con `updated` más reciente que la última vista —
sin ese filtro, cada `poll()` reportaría de nuevo TODO el contenido del feed.

Dueño: Miguel.
"""

from __future__ import annotations

from alert_ingestor.application.ports import AlertSourcePort, Clock, HttpClient
from alert_ingestor.domain.errors import MalformedEvent
from alert_ingestor.domain.models import EventStatus, RawSeismicEvent, SeismicSource

USGS_FEED_BASE = "https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary"


class UsgsFeedSource(AlertSourcePort):
    name = "usgs"

    def __init__(
        self,
        http: HttpClient,
        clock: Clock,
        *,
        feed: str = "all_hour",
        base_url: str = USGS_FEED_BASE,
    ) -> None:
        self._http = http
        self._clock = clock
        self._url = f"{base_url}/{feed}.geojson"
        self._last_updated: dict[str, int] = {}

    async def poll(self) -> list[RawSeismicEvent]:
        body = await self._http.get_json(self._url)
        received_at = self._clock.now_ms()

        fresh: list[RawSeismicEvent] = []
        for feature in body.get("features", []):
            try:
                event = self._parse(feature, received_at=received_at)
            except (KeyError, TypeError, ValueError, IndexError) as exc:
                raise MalformedEvent(f"evento USGS malformado: {exc}") from exc

            last_seen = self._last_updated.get(event.external_id)
            updated_at = feature.get("properties", {}).get("updated", event.occurred_at)
            if last_seen is not None and updated_at <= last_seen:
                continue  # ya lo reportamos y no ha cambiado desde entonces
            self._last_updated[event.external_id] = updated_at
            fresh.append(event)
        return fresh

    @staticmethod
    def _parse(feature: dict, *, received_at: int) -> RawSeismicEvent:
        props = feature["properties"]
        lon, lat, depth_km = feature["geometry"]["coordinates"]
        return RawSeismicEvent(
            source=SeismicSource.USGS,
            external_id=feature["id"],
            magnitude=float(props["mag"]),
            magnitude_type=props.get("magType") or "unknown",
            lat=float(lat),
            lon=float(lon),
            depth_km=float(depth_km) if depth_km is not None else None,
            occurred_at=int(props["time"]),
            received_at=received_at,
            status=EventStatus.REVIEWED if props.get("status") == "reviewed" else EventStatus.AUTOMATIC,
            place=props.get("place") or "",
            url=props.get("url"),
            raw=feature,
        )
