"""Orquestador: fuentes -> dedupe -> activación, con las tres fuentes como fakes."""

from __future__ import annotations

import pytest
from conftest import NOW_MS, make_event

from alert_ingestor.adapters.clock import FixedClock
from alert_ingestor.adapters.ids import SequentialIdGenerator
from alert_ingestor.adapters.persistence.memory import InMemoryIncidentRepository
from alert_ingestor.adapters.sources.sgc import FakeSgcSource
from alert_ingestor.application.ingest import AlertIngestionService
from alert_ingestor.domain.errors import SourceUnavailable
from alert_ingestor.domain.models import ActivationPolicy, SeismicSource


class FakeAlertSource:
    """Fuente mínima conforme a `AlertSourcePort`, sin depender de HTTP/WS reales."""

    def __init__(self, name: str, batches: list[list] | None = None) -> None:
        self.name = name
        self._batches = batches or []

    def queue(self, events: list) -> None:
        self._batches.append(events)

    async def poll(self) -> list:
        if not self._batches:
            return []
        return self._batches.pop(0)


class FailingSource:
    name = "flaky"

    async def poll(self) -> list:
        raise SourceUnavailable("timeout simulado")


def build_service(sources, *, clock=None, policy=None) -> AlertIngestionService:
    return AlertIngestionService(
        sources=sources,
        repository=InMemoryIncidentRepository(),
        clock=clock or FixedClock(NOW_MS),
        ids=SequentialIdGenerator(),
        policy=policy,
    )


@pytest.mark.asyncio
async def test_high_magnitude_from_one_source_activates_immediately() -> None:
    emsc = FakeAlertSource("emsc", [[make_event(source=SeismicSource.EMSC, magnitude=6.5)]])
    service = build_service([emsc])

    result = await service.run_cycle()

    assert len(result.touched_incidents) == 1
    assert len(result.new_activations) == 1
    assert result.new_activations[0].incident.magnitude == 6.5
    assert result.errors == ()


@pytest.mark.asyncio
async def test_activation_is_reported_only_once_across_cycles() -> None:
    """Un incidente ya activado no debe volver a aparecer en new_activations solo
    porque otra fuente lo corrobora en un ciclo posterior — sería spam."""
    emsc = FakeAlertSource("emsc", [[make_event(source=SeismicSource.EMSC, magnitude=6.5, external_id="e1")]])
    usgs = FakeAlertSource(
        "usgs",
        [
            [],  # nada en el primer ciclo
            [make_event(source=SeismicSource.USGS, magnitude=6.6, external_id="e1", occurred_at=NOW_MS + 10_000)],
        ],
    )
    service = build_service([emsc, usgs])

    first = await service.run_cycle()
    second = await service.run_cycle()

    assert len(first.new_activations) == 1
    assert second.new_activations == ()  # el mismo incidente, ya activado
    assert len(second.touched_incidents) == 1  # sí se registró la corroboración


@pytest.mark.asyncio
async def test_low_magnitude_alone_does_not_activate_but_corroboration_does() -> None:
    emsc = FakeAlertSource("emsc", [[make_event(source=SeismicSource.EMSC, magnitude=3.8, external_id="e1")]])
    usgs = FakeAlertSource(
        "usgs",
        [[make_event(source=SeismicSource.USGS, magnitude=3.7, external_id="e1", occurred_at=NOW_MS + 5_000)]],
    )
    service = build_service([emsc, usgs])

    result = await service.run_cycle()

    assert len(result.new_activations) == 1
    assert result.new_activations[0].incident.source_count == 2


@pytest.mark.asyncio
async def test_one_source_failing_does_not_block_the_others() -> None:
    emsc = FakeAlertSource("emsc", [[make_event(source=SeismicSource.EMSC, magnitude=6.5)]])
    service = build_service([FailingSource(), emsc])

    result = await service.run_cycle()

    assert len(result.errors) == 1
    assert result.errors[0].source == "flaky"
    assert len(result.touched_incidents) == 1  # emsc sí se procesó


@pytest.mark.asyncio
async def test_sgc_fake_participates_in_the_same_pipeline_as_real_sources() -> None:
    sgc = FakeSgcSource()
    sgc.queue([make_event(source=SeismicSource.SGC, magnitude=5.0, external_id="e1")])
    service = build_service([sgc])

    result = await service.run_cycle()
    assert len(result.new_activations) == 1


@pytest.mark.asyncio
async def test_custom_policy_reaches_the_orchestrator() -> None:
    emsc = FakeAlertSource("emsc", [[make_event(source=SeismicSource.EMSC, magnitude=4.0)]])
    strict = ActivationPolicy(min_magnitude_single_source=9.0)
    service = build_service([emsc], policy=strict)

    result = await service.run_cycle()
    assert result.new_activations == ()


@pytest.mark.asyncio
async def test_repository_is_updated_with_every_touched_incident() -> None:
    from alert_ingestor.adapters.persistence.memory import InMemoryIncidentRepository

    emsc = FakeAlertSource("emsc", [[make_event(source=SeismicSource.EMSC, external_id="e1")]])
    repo = InMemoryIncidentRepository()
    service = AlertIngestionService(
        sources=[emsc],
        repository=repo,
        clock=FixedClock(NOW_MS),
        ids=SequentialIdGenerator(),
    )

    result = await service.run_cycle()
    incident_id = result.touched_incidents[0].id
    assert repo.get(incident_id) is not None
