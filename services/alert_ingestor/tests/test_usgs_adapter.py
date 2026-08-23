"""Adaptador USGS: parseo del feed real y filtro de novedad por `updated`."""

from __future__ import annotations

import pytest
from conftest import NOW_MS, usgs_feature, usgs_feed

from alert_ingestor.adapters.clock import FixedClock
from alert_ingestor.adapters.http import FakeHttpClient
from alert_ingestor.adapters.sources.usgs import USGS_FEED_BASE, UsgsFeedSource
from alert_ingestor.domain.errors import MalformedEvent, SourceUnavailable
from alert_ingestor.domain.models import EventStatus, SeismicSource


def make_source(http: FakeHttpClient, clock: FixedClock) -> UsgsFeedSource:
    return UsgsFeedSource(http, clock)


@pytest.mark.asyncio
async def test_first_poll_returns_all_features() -> None:
    http = FakeHttpClient({f"{USGS_FEED_BASE}/all_hour.geojson": usgs_feed([usgs_feature()])})
    source = make_source(http, FixedClock(NOW_MS))

    events = await source.poll()
    assert len(events) == 1
    event = events[0]
    assert event.source is SeismicSource.USGS
    assert event.external_id == "us7000abcd"
    assert event.magnitude == 6.1
    assert event.lat == 5.07
    assert event.lon == -75.51
    assert event.depth_km == 10.0
    assert event.occurred_at == NOW_MS
    assert event.received_at == NOW_MS
    assert event.status is EventStatus.AUTOMATIC
    assert "Manizales" in event.place


@pytest.mark.asyncio
async def test_unchanged_event_is_not_reported_twice() -> None:
    url = f"{USGS_FEED_BASE}/all_hour.geojson"
    feature = usgs_feature()
    http = FakeHttpClient()
    http.queue_responses(url, [usgs_feed([feature]), usgs_feed([feature])])
    source = make_source(http, FixedClock(NOW_MS))

    first = await source.poll()
    second = await source.poll()
    assert len(first) == 1
    assert second == []


@pytest.mark.asyncio
async def test_updated_magnitude_is_reported_again() -> None:
    url = f"{USGS_FEED_BASE}/all_hour.geojson"
    original = usgs_feature(mag=6.1, updated_ms=NOW_MS)
    revised = usgs_feature(mag=6.4, updated_ms=NOW_MS + 5 * 60_000)
    http = FakeHttpClient()
    http.queue_responses(url, [usgs_feed([original]), usgs_feed([revised])])
    source = make_source(http, FixedClock(NOW_MS))

    first = await source.poll()
    second = await source.poll()
    assert first[0].magnitude == 6.1
    assert len(second) == 1
    assert second[0].magnitude == 6.4


@pytest.mark.asyncio
async def test_new_feature_alongside_unchanged_one_returns_only_the_new_one() -> None:
    url = f"{USGS_FEED_BASE}/all_hour.geojson"
    seen = usgs_feature(id="us-seen")
    new = usgs_feature(id="us-new", mag=5.0)
    http = FakeHttpClient()
    http.queue_responses(url, [usgs_feed([seen]), usgs_feed([seen, new])])
    source = make_source(http, FixedClock(NOW_MS))

    await source.poll()
    second = await source.poll()
    assert [e.external_id for e in second] == ["us-new"]


@pytest.mark.asyncio
async def test_reviewed_status_is_mapped() -> None:
    url = f"{USGS_FEED_BASE}/all_hour.geojson"
    http = FakeHttpClient({url: usgs_feed([usgs_feature(status="reviewed")])})
    events = await make_source(http, FixedClock(NOW_MS)).poll()
    assert events[0].status is EventStatus.REVIEWED


@pytest.mark.asyncio
async def test_malformed_feature_raises_malformed_event() -> None:
    url = f"{USGS_FEED_BASE}/all_hour.geojson"
    broken = usgs_feature()
    del broken["properties"]["mag"]
    http = FakeHttpClient({url: usgs_feed([broken])})

    with pytest.raises(MalformedEvent):
        await make_source(http, FixedClock(NOW_MS)).poll()


@pytest.mark.asyncio
async def test_source_unavailable_propagates() -> None:
    http = FakeHttpClient({})  # sin respuesta programada
    with pytest.raises(SourceUnavailable):
        await make_source(http, FixedClock(NOW_MS)).poll()


@pytest.mark.asyncio
async def test_uses_the_documented_default_feed_url() -> None:
    """El feed por defecto es el endpoint real y estable de USGS — sin API key,
    documentado en https://earthquake.usgs.gov/earthquakes/feed/v1.0/geojson.php."""
    expected = "https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/all_hour.geojson"
    http = FakeHttpClient({expected: usgs_feed([])})
    await make_source(http, FixedClock(NOW_MS)).poll()
    assert http.calls == [expected]


@pytest.mark.asyncio
async def test_custom_feed_name_changes_the_url() -> None:
    url = f"{USGS_FEED_BASE}/significant_week.geojson"
    http = FakeHttpClient({url: usgs_feed([])})
    source = UsgsFeedSource(http, FixedClock(NOW_MS), feed="significant_week")
    await source.poll()
    assert http.calls == [url]
