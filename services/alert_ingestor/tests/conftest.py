"""Fixtures compartidas: eventos de ejemplo con forma realista de cada fuente."""

from __future__ import annotations

from alert_ingestor.domain.models import EventStatus, RawSeismicEvent, SeismicSource

#: 2026-08-22T12:00:00Z
NOW_MS = 1787472000000
MIN_MS = 60_000


def usgs_feature(
    *,
    id: str = "us7000abcd",
    mag: float = 6.1,
    lon: float = -75.51,
    lat: float = 5.07,
    depth_km: float = 10.0,
    time_ms: int = NOW_MS,
    updated_ms: int | None = None,
    place: str = "12 km SE of Manizales, Colombia",
    status: str = "automatic",
) -> dict:
    """Forma real del feed GeoJSON de USGS
    (https://earthquake.usgs.gov/earthquakes/feed/v1.0/geojson.php)."""
    return {
        "type": "Feature",
        "id": id,
        "properties": {
            "mag": mag,
            "place": place,
            "time": time_ms,
            "updated": updated_ms if updated_ms is not None else time_ms,
            "url": f"https://earthquake.usgs.gov/earthquakes/eventpage/{id}",
            "status": status,
            "magType": "mww",
            "type": "earthquake",
        },
        "geometry": {"type": "Point", "coordinates": [lon, lat, depth_km]},
    }


def usgs_feed(features: list[dict]) -> dict:
    return {"type": "FeatureCollection", "metadata": {"count": len(features)}, "features": features}


def emsc_message(
    *,
    action: str = "create",
    unid: str = "20260822_0000042",
    mag: float = 6.0,
    lon: float = -75.5,
    lat: float = 5.08,
    depth_km: float = 12.0,
    time_iso: str = "2026-08-22T12:00:03.500000Z",
    region: str = "COLOMBIA",
) -> str:
    """Forma real de un mensaje del standing-order websocket de EMSC
    (https://www.seismicportal.eu/realtime.html)."""
    import json

    return json.dumps(
        {
            "action": action,
            "data": {
                "type": "Feature",
                "id": unid,
                "geometry": {"type": "Point", "coordinates": [lon, lat, -depth_km]},
                "properties": {
                    "lastupdate": time_iso,
                    "time": time_iso,
                    "lat": lat,
                    "lon": lon,
                    "depth": depth_km,
                    "mag": mag,
                    "magtype": "ML",
                    "unid": unid,
                    "auth": "EMSC",
                    "source_id": "EMSC",
                    "source_cat": "EMSC-RTS",
                    "flynn_region": region,
                    "evtype": "ke",
                },
            },
        }
    )


def make_event(
    *,
    source: SeismicSource = SeismicSource.USGS,
    external_id: str = "ev-1",
    magnitude: float = 6.0,
    lat: float = 5.07,
    lon: float = -75.51,
    occurred_at: int = NOW_MS,
    received_at: int | None = None,
) -> RawSeismicEvent:
    """Constructor corto para tests que no necesitan la forma cruda de la fuente."""
    return RawSeismicEvent(
        source=source,
        external_id=external_id,
        magnitude=magnitude,
        magnitude_type="Mw",
        lat=lat,
        lon=lon,
        depth_km=10.0,
        occurred_at=occurred_at,
        received_at=received_at if received_at is not None else occurred_at + 5_000,
        status=EventStatus.AUTOMATIC,
        place="prueba",
    )
