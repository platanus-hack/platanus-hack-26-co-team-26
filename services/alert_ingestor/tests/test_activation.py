"""Política de activación: umbral individual vs. corroborado."""

from __future__ import annotations

from conftest import make_event

from alert_ingestor.domain.activation import decide_activation
from alert_ingestor.domain.models import ActivationPolicy, SeismicIncident, SeismicSource


def incident(*reports) -> SeismicIncident:
    return SeismicIncident(id="inc-1", primary=reports[0], corroborating=tuple(reports[1:]))


def test_high_magnitude_activates_with_a_single_source() -> None:
    decision = decide_activation(incident(make_event(magnitude=6.5)))
    assert decision.should_activate
    assert "Magnitud 6.5" in decision.reason


def test_low_magnitude_single_source_does_not_activate() -> None:
    decision = decide_activation(incident(make_event(magnitude=3.0)))
    assert not decision.should_activate


def test_moderate_magnitude_corroborated_by_two_sources_activates() -> None:
    decision = decide_activation(
        incident(
            make_event(source=SeismicSource.EMSC, magnitude=3.8),
            make_event(source=SeismicSource.USGS, external_id="ev-2", magnitude=3.6),
        )
    )
    assert decision.should_activate
    assert "corroborada por 2 fuentes" in decision.reason


def test_moderate_magnitude_single_source_does_not_activate_even_if_above_corroborated_floor() -> None:
    decision = decide_activation(incident(make_event(magnitude=3.8)))
    assert not decision.should_activate


def test_two_sources_below_corroborated_floor_does_not_activate() -> None:
    decision = decide_activation(
        incident(
            make_event(source=SeismicSource.EMSC, magnitude=2.0),
            make_event(source=SeismicSource.USGS, external_id="ev-2", magnitude=2.1),
        )
    )
    assert not decision.should_activate


def test_custom_policy_is_respected() -> None:
    strict = ActivationPolicy(
        min_magnitude_single_source=7.0,
        min_magnitude_corroborated=5.0,
        min_corroborating_sources=3,
    )
    decision = decide_activation(incident(make_event(magnitude=6.5)), strict)
    assert not decision.should_activate
