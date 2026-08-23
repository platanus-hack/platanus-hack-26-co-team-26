"""Adaptador SGC: la parte real (HTTP) y el límite honesto (sin parser confirmado)."""

from __future__ import annotations

import pytest
from conftest import NOW_MS, make_event

from alert_ingestor.adapters.clock import FixedClock
from alert_ingestor.adapters.http import FakeHttpClient
from alert_ingestor.adapters.sources.sgc import FakeSgcSource, SgcFeedSource
from alert_ingestor.domain.models import SeismicSource


@pytest.mark.asyncio
async def test_without_a_confirmed_parser_polling_fails_loudly() -> None:
    """No hay un formato SGC verificado — mejor un error explícito que un adaptador
    que aparenta funcionar sin haber podido probarse contra la fuente real."""
    http = FakeHttpClient({"https://ejemplo.sgc.gov.co/ultimos-sismos": {}})
    source = SgcFeedSource(http, FixedClock(NOW_MS), base_url="https://ejemplo.sgc.gov.co/ultimos-sismos")

    with pytest.raises(NotImplementedError):
        await source.poll()


@pytest.mark.asyncio
async def test_base_url_is_required() -> None:
    with pytest.raises(TypeError):
        SgcFeedSource(FakeHttpClient(), FixedClock(NOW_MS))  # falta base_url


@pytest.mark.asyncio
async def test_injected_parser_is_used_once_the_format_is_known() -> None:
    """Demuestra el punto de extensión: proveer `parser=` es lo único que hace
    falta el día que se confirme el formato real del SGC."""
    url = "https://ejemplo.sgc.gov.co/ultimos-sismos"
    http = FakeHttpClient({url: {"eventos": [{"id": "sgc-1"}]}})

    def fake_parser(body: dict, received_at: int) -> list:
        return [make_event(source=SeismicSource.SGC, external_id=e["id"]) for e in body["eventos"]]

    source = SgcFeedSource(http, FixedClock(NOW_MS), base_url=url, parser=fake_parser)
    events = await source.poll()
    assert [e.external_id for e in events] == ["sgc-1"]


@pytest.mark.asyncio
async def test_fake_sgc_source_serves_queued_batches_for_pipeline_tests() -> None:
    fake = FakeSgcSource()
    fake.queue([make_event(source=SeismicSource.SGC, external_id="sgc-1")])

    first = await fake.poll()
    second = await fake.poll()
    assert len(first) == 1
    assert second == []
