"""Distancia y deduplicación entre fuentes."""

from __future__ import annotations

from conftest import MIN_MS, NOW_MS, make_event

from alert_ingestor.domain.dedup import Deduplicator, DedupWindow, same_event, select_primary
from alert_ingestor.domain.geo import haversine_km
from alert_ingestor.domain.models import SeismicSource


def test_haversine_zero_distance_for_same_point() -> None:
    assert haversine_km(5.07, -75.51, 5.07, -75.51) == 0.0


def test_haversine_known_distance_bogota_manizales() -> None:
    # Bogotá (4.71, -74.07) a Manizales (5.07, -75.51): ~155 km en línea recta.
    d = haversine_km(4.71, -74.07, 5.07, -75.51)
    assert 145 < d < 165


def test_same_event_true_within_all_tolerances() -> None:
    a = make_event(occurred_at=NOW_MS, lat=5.07, lon=-75.51, magnitude=6.0)
    b = make_event(occurred_at=NOW_MS + 30_000, lat=5.08, lon=-75.50, magnitude=6.3)
    assert same_event(a, b, DedupWindow())


def test_same_event_false_outside_time_window() -> None:
    a = make_event(occurred_at=NOW_MS)
    b = make_event(occurred_at=NOW_MS + 5 * MIN_MS)
    assert not same_event(a, b, DedupWindow())


def test_same_event_false_outside_distance_window() -> None:
    a = make_event(lat=5.07, lon=-75.51)  # Manizales
    b = make_event(lat=6.25, lon=-75.56)  # Medellín, ~130 km — dentro del default
    assert same_event(a, b, DedupWindow())
    far = make_event(lat=-33.45, lon=-70.66)  # Santiago de Chile
    assert not same_event(a, far, DedupWindow())


def test_same_event_false_outside_magnitude_window() -> None:
    a = make_event(magnitude=6.0)
    b = make_event(magnitude=3.5)
    assert not same_event(a, b, DedupWindow())


def test_select_primary_prefers_sgc_over_emsc_regardless_of_arrival_order() -> None:
    emsc = make_event(source=SeismicSource.EMSC, received_at=NOW_MS)
    sgc = make_event(source=SeismicSource.SGC, received_at=NOW_MS + 60_000)
    assert select_primary([emsc, sgc]) is sgc
    assert select_primary([sgc, emsc]) is sgc


def test_select_primary_breaks_ties_by_earliest_received() -> None:
    first = make_event(source=SeismicSource.USGS, received_at=NOW_MS)
    second = make_event(source=SeismicSource.USGS, external_id="ev-2", received_at=NOW_MS + 1000)
    assert select_primary([second, first]) is first


def test_dedup_ingest_creates_new_incident_for_first_report() -> None:
    dedup = Deduplicator()
    incident = dedup.ingest(make_event(external_id="ev-1"), new_id="inc-1")
    assert incident.id == "inc-1"
    assert incident.source_count == 1


def test_dedup_ingest_merges_corroborating_report_into_same_incident() -> None:
    dedup = Deduplicator()
    first = dedup.ingest(
        make_event(source=SeismicSource.EMSC, external_id="emsc-1", occurred_at=NOW_MS),
        new_id="inc-1",
    )
    merged = dedup.ingest(
        make_event(
            source=SeismicSource.USGS,
            external_id="usgs-1",
            occurred_at=NOW_MS + 20_000,
            magnitude=6.1,
        ),
        new_id="inc-2",  # se ignora: el evento se fusiona en el incidente existente
    )
    assert merged.id == first.id
    assert merged.source_count == 2
    assert merged.sources == {SeismicSource.EMSC, SeismicSource.USGS}


def test_dedup_primary_flips_to_higher_priority_source_on_corroboration() -> None:
    """El evento clave: EMSC llega primero (por ser más rápida), pero cuando SGC
    corrobora el mismo sismo, SGC pasa a ser la fuente que manda — sin importar
    que haya llegado después."""
    dedup = Deduplicator()
    dedup.ingest(
        make_event(source=SeismicSource.EMSC, external_id="emsc-1", magnitude=6.0),
        new_id="inc-1",
    )
    incident = dedup.ingest(
        make_event(
            source=SeismicSource.SGC,
            external_id="sgc-1",
            magnitude=6.2,
            received_at=NOW_MS + 90_000,
        ),
        new_id="inc-2",
    )
    assert incident.primary.source is SeismicSource.SGC
    assert incident.magnitude == 6.2  # la mayor magnitud reportada, no la del primary


def test_dedup_ignores_duplicate_update_from_same_source() -> None:
    dedup = Deduplicator()
    dedup.ingest(make_event(external_id="ev-1", received_at=NOW_MS), new_id="inc-1")
    incident = dedup.ingest(
        make_event(external_id="ev-1", received_at=NOW_MS + 1000), new_id="inc-2"
    )
    assert incident.source_count == 1
    assert len(incident.all_reports) == 1


def test_dedup_distinct_events_stay_separate() -> None:
    dedup = Deduplicator()
    dedup.ingest(make_event(external_id="ev-1", lat=5.07, lon=-75.51), new_id="inc-1")
    other = dedup.ingest(
        make_event(external_id="ev-2", lat=-33.45, lon=-70.66, occurred_at=NOW_MS + 1000),
        new_id="inc-2",
    )
    assert other.id == "inc-2"
    assert other.source_count == 1


def test_dedup_recent_filters_by_received_at() -> None:
    dedup = Deduplicator()
    dedup.ingest(
        make_event(external_id="ev-1", lat=5.07, lon=-75.51, received_at=NOW_MS),
        new_id="inc-1",
    )
    # Distinta ubicación (Chile) para que dedup no lo fusione con el anterior: lo
    # que este test verifica es el filtro por received_at, no la fusión.
    dedup.ingest(
        make_event(
            external_id="ev-2", lat=-33.45, lon=-70.66, received_at=NOW_MS + 10 * MIN_MS
        ),
        new_id="inc-2",
    )
    recent = dedup.recent(since_ms=NOW_MS + 5 * MIN_MS)
    assert {inc.id for inc in recent} == {"inc-2"}


def test_dedup_forget_older_than_evicts_stale_incidents() -> None:
    dedup = Deduplicator()
    dedup.ingest(make_event(external_id="ev-1", received_at=NOW_MS), new_id="inc-1")
    dedup.forget_older_than(cutoff_ms=NOW_MS + 1)
    assert dedup.recent(since_ms=0) == []
