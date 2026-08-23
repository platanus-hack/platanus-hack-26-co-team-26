"""Adaptador EMSC: parseo del mensaje real del standing-order websocket."""

from __future__ import annotations

import pytest
from conftest import NOW_MS, emsc_message

from alert_ingestor.adapters.clock import FixedClock
from alert_ingestor.adapters.sources.emsc import EmscWebSocketSource
from alert_ingestor.adapters.websocket import FakeConnector
from alert_ingestor.domain.models import SeismicSource


@pytest.mark.asyncio
async def test_run_then_poll_returns_parsed_event() -> None:
    connector = FakeConnector([emsc_message()])
    source = EmscWebSocketSource(connector, FixedClock(NOW_MS))

    await source.run()  # el FakeConnector es finito: termina solo
    events = await source.poll()

    assert len(events) == 1
    event = events[0]
    assert event.source is SeismicSource.EMSC
    assert event.external_id == "20260822_0000042"
    assert event.magnitude == 6.0
    assert event.magnitude_type == "ML"
    assert event.lat == 5.08
    assert event.lon == -75.5
    assert event.depth_km == 12.0  # signo invertido respecto a la coordenada GeoJSON
    assert event.place == "COLOMBIA"
    assert event.received_at == NOW_MS


@pytest.mark.asyncio
async def test_occurred_at_is_parsed_from_iso_timestamp() -> None:
    connector = FakeConnector([emsc_message(time_iso="2026-08-22T12:00:03.500000Z")])
    source = EmscWebSocketSource(connector, FixedClock(NOW_MS))
    await source.run()
    events = await source.poll()
    assert events[0].occurred_at == 1787400003500


@pytest.mark.asyncio
async def test_poll_drains_the_buffer() -> None:
    connector = FakeConnector([emsc_message(unid="ev-1"), emsc_message(unid="ev-2")])
    source = EmscWebSocketSource(connector, FixedClock(NOW_MS))
    await source.run()

    first = await source.poll()
    second = await source.poll()
    assert len(first) == 2
    assert second == []


@pytest.mark.asyncio
async def test_delete_action_is_ignored_not_forwarded_as_new_event() -> None:
    """Limitación conocida y documentada: una retractación no retira un incidente
    ya creado, así que de momento simplemente no se reenvía como evento nuevo."""
    connector = FakeConnector(
        [emsc_message(unid="ev-1", action="create"), emsc_message(unid="ev-1", action="delete")]
    )
    source = EmscWebSocketSource(connector, FixedClock(NOW_MS))
    await source.run()
    events = await source.poll()
    assert len(events) == 1  # solo el create


@pytest.mark.asyncio
async def test_malformed_message_is_skipped_without_stopping_the_stream() -> None:
    connector = FakeConnector(["esto no es json", emsc_message(unid="ev-ok")])
    source = EmscWebSocketSource(connector, FixedClock(NOW_MS))
    await source.run()
    events = await source.poll()
    assert [e.external_id for e in events] == ["ev-ok"]


@pytest.mark.asyncio
async def test_update_action_is_parsed_like_create() -> None:
    connector = FakeConnector([emsc_message(action="update", mag=6.3)])
    source = EmscWebSocketSource(connector, FixedClock(NOW_MS))
    await source.run()
    events = await source.poll()
    assert events[0].magnitude == 6.3
