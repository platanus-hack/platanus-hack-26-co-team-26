"""Tests de C2 (Analista LLM). Pegan a la API real de Claude -> se saltan sin
ANTHROPIC_API_KEY. Ver criterios de aceptacion en specs/01-data-contracts.md §2 y
specs/03-components.md C2.
"""

from __future__ import annotations

import os

import pytest

from adapters.analyst.claude_analyst import KNOWN_MODULES, KNOWN_ORACLES, _evidence_ids
from adapters.fakes import FakeExtractor

pytestmark = pytest.mark.skipif(
    not os.environ.get("ANTHROPIC_API_KEY"), reason="requires ANTHROPIC_API_KEY"
)


@pytest.fixture(scope="module")
def architecture():
    return FakeExtractor().extract("./target-agent")


@pytest.fixture(scope="module")
def analysis(architecture):
    from adapters.analyst import ClaudeAnalyst

    return ClaudeAnalyst().analyze(architecture)


def test_at_least_two_threats(analysis):
    assert len(analysis.threats) >= 2


def test_has_single_surface_cmd_injection(analysis):
    assert any(
        t.threat_id == "cmd_injection" and "+" not in t.surface for t in analysis.threats
    )


def test_has_multistep_chain(analysis):
    assert any("+" in t.surface for t in analysis.threats)


def test_has_wallet_dos_when_loop_unbounded(architecture, analysis):
    """T3 (specs/05-performance-thesis.md): FakeExtractor's agent_loop has no bound."""
    assert architecture.agent_loop.max_iterations is None
    assert not architecture.agent_loop.budget_enforced
    assert any(
        t.threat_class == "performance" and t.threat_id == "wallet_dos"
        for t in analysis.threats
    )


def test_evidence_refs_are_real(architecture, analysis):
    valid_ids = _evidence_ids(architecture)
    for threat in analysis.threats:
        assert set(threat.evidence_refs) <= valid_ids


def test_recommended_names_are_known(analysis):
    for threat in analysis.threats:
        assert set(threat.recommended_modules) <= KNOWN_MODULES
        assert set(threat.recommended_oracle) <= KNOWN_ORACLES


def test_priority_is_total_order(analysis):
    priorities = [t.priority for t in analysis.threats]
    assert len(set(priorities)) == len(priorities)
