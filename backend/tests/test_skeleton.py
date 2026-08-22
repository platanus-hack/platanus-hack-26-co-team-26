"""Walking skeleton: el grafo corre end-to-end con fakes y el loop T2 cierra en `resisted`.

Ejecuta:  uv run pytest        (o)  uv run python -m tests.test_skeleton
"""

from __future__ import annotations

from adapters.fakes import (
    CollectingTelemetry,
    FakeAnalyst,
    FakeDesigner,
    FakeEnforcement,
    FakeExtractor,
    FakeMitigator,
    FakeOracle,
    FakeSandbox,
)
from domain.graph import Deps, build_graph


def _deps() -> tuple[Deps, CollectingTelemetry]:
    telemetry = CollectingTelemetry()
    deps = Deps(
        extractor=FakeExtractor(),
        analyst=FakeAnalyst(),
        designer=FakeDesigner(),
        sandbox=FakeSandbox(),
        oracle=FakeOracle(),
        mitigator=FakeMitigator(),
        enforcement=FakeEnforcement(),
        telemetry=telemetry,
    )
    return deps, telemetry


def run_skeleton() -> dict:
    deps, telemetry = _deps()
    FakeOracle._n = 0
    graph = build_graph(deps)
    final = graph.invoke(
        {"run_id": "run-a1b2", "repo_path": "./target-agent",
         "mitigation_rounds": 0, "max_rounds": 2}
    )
    return final


def test_loop_closes():
    """T2: exploit confirmado -> mitigacion -> regeneracion -> resisted (CERRADO)."""
    final = run_skeleton()
    verdicts = [f.oracle_verdict for f in final["findings"]]
    assert verdicts[0] == "exploited", "el primer finding debe confirmarse por el oraculo"
    assert verdicts[-1] == "resisted", "tras la mitigacion, la regresion debe cerrar"
    assert final["policies"], "debe haberse generado una policy"


def test_architecture_aware():
    """T1: el harness_spec se deriva de la arquitectura (superficie = tool detectada)."""
    final = run_skeleton()
    spec = final["harness_spec"]
    assert any(s.target == "tool.shell" for s in spec.surfaces)
    assert spec.sandbox.escape_probe is True
    assert spec.sandbox.network == "deny-all"


if __name__ == "__main__":
    print("== Harness Compiler · walking skeleton (fakes) ==")
    result = run_skeleton()
    verdicts = [f.oracle_verdict for f in result["findings"]]
    print(f"\nfindings: {verdicts}")
    print("resultado:", "🔒 CERRADO (T2 probado)" if verdicts[-1] == "resisted"
          else "❌ no cerro")
