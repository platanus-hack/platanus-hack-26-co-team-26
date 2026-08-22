"""El pipeline como StateGraph de LangGraph. Ver specs/02-architecture-ports.md.

El loop T2 (mitigar -> regenerar -> re-ejecutar) es un edge condicional: si el oraculo
marca algun finding `exploited`, entra al ciclo de mitigacion; cuando la regresion vuelve
`resisted`, cierra (END). El `budget.max_steps` acota el loop; nunca es infinito.

Nodos deterministas: extract, design, execute, oracle, regenerate, enforce.
Nodos LLM: analyze, mitigate.  (solo 2 nodos tocan el modelo)
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Annotated, Any

from langgraph.graph import END, START, StateGraph
from typing_extensions import TypedDict

from contracts import (
    AgentArchitecture,
    Finding,
    HarnessEvent,
    HarnessSpec,
    Policy,
    RegressionSpec,
    ThreatAnalysis,
)
from domain.ports import (
    ArchitectureExtractorPort,
    EnforcementPort,
    HarnessDesignerPort,
    MitigationPort,
    OraclePort,
    SandboxPort,
    SecurityAnalystPort,
    TelemetryPort,
)
from domain.types import ExecutionTrace


@dataclass
class Deps:
    """Contenedor de adaptadores inyectados al grafo (composition root)."""

    extractor: ArchitectureExtractorPort
    analyst: SecurityAnalystPort
    designer: HarnessDesignerPort
    sandbox: SandboxPort
    oracle: OraclePort
    mitigator: MitigationPort
    enforcement: EnforcementPort
    telemetry: TelemetryPort


def _merge(a: list, b: list) -> list:
    return a + b


class GraphState(TypedDict, total=False):
    run_id: str
    repo_path: str
    architecture: AgentArchitecture
    analysis: ThreatAnalysis
    harness_spec: HarnessSpec
    trace: ExecutionTrace
    findings: Annotated[list[Finding], _merge]
    policies: Annotated[list[Policy], _merge]
    regression: RegressionSpec | None
    mitigation_rounds: int
    max_rounds: int


def build_graph(deps: Deps):
    """Construye y compila el StateGraph con los adaptadores dados."""

    def _emit(state: GraphState, step: str, status: str, **detail: Any) -> None:
        deps.telemetry.emit(
            HarnessEvent(
                run_id=state["run_id"],
                step=step,  # type: ignore[arg-type]
                status=status,  # type: ignore[arg-type]
                artifact_ref=detail.pop("artifact_ref", None),
                verdict=detail.pop("verdict", None),
                ts_ms=int(time.time() * 1000),
                detail=detail,
            )
        )

    # --- nodos ---------------------------------------------------------------
    def extract(state: GraphState) -> GraphState:
        _emit(state, "extract", "started")
        arch = deps.extractor.extract(state["repo_path"])
        _emit(state, "extract", "done", artifact_ref=arch.agent.name)
        return {"architecture": arch}

    def analyze(state: GraphState) -> GraphState:
        _emit(state, "analyze", "started")
        analysis = deps.analyst.analyze(state["architecture"])
        _emit(state, "analyze", "done", threats=len(analysis.threats))
        return {"analysis": analysis}

    def design(state: GraphState) -> GraphState:
        _emit(state, "design", "started")
        spec = deps.designer.design(state["analysis"])
        _emit(state, "design", "done", artifact_ref=spec.harness_id)
        return {"harness_spec": spec}

    def execute(state: GraphState) -> GraphState:
        _emit(state, "execute", "started")
        trace = deps.sandbox.run(state["repo_path"], state["harness_spec"])
        _emit(state, "execute", "done", contained=trace.escape_probe_contained)
        return {"trace": trace}

    def oracle(state: GraphState) -> GraphState:
        _emit(state, "oracle", "started")
        finding = deps.oracle.evaluate(state["trace"])
        _emit(state, "oracle", "done", artifact_ref=finding.id, verdict=finding.oracle_verdict)
        return {"findings": [finding]}

    def mitigate(state: GraphState) -> GraphState:
        _emit(state, "mitigate", "started")
        finding = _latest_exploited(state)
        policy = deps.mitigator.propose(finding)
        deps.enforcement.apply(policy)
        _emit(state, "mitigate", "done", artifact_ref=policy.id)
        _emit(state, "enforce", "done", artifact_ref=policy.id)
        return {"policies": [policy], "mitigation_rounds": state.get("mitigation_rounds", 0) + 1}

    def regenerate(state: GraphState) -> GraphState:
        _emit(state, "regenerate", "started")
        finding = _latest_exploited(state)
        policy = state["policies"][-1]
        regression = deps.designer.regenerate(finding, policy)
        # re-ejecuta el payload exacto y re-evalua (prueba T2)
        trace = deps.sandbox.run(state["repo_path"], _as_harness(regression))
        new_finding = deps.oracle.evaluate(trace)
        _emit(
            state, "regenerate", "done",
            artifact_ref=regression.harness_id, verdict=new_finding.oracle_verdict,
        )
        return {"regression": regression, "findings": [new_finding]}

    # --- edges condicionales -------------------------------------------------
    def after_oracle(state: GraphState) -> str:
        if _latest_exploited(state) is not None:
            return "mitigate"
        return END

    def after_regenerate(state: GraphState) -> str:
        last = state["findings"][-1]
        if last.oracle_verdict == "resisted":
            return END  # CERRADO — prueba T2
        if state.get("mitigation_rounds", 0) >= state.get("max_rounds", 2):
            return END  # corte de seguridad
        return "mitigate"  # reintentar mitigacion

    # --- ensamblado ----------------------------------------------------------
    g = StateGraph(GraphState)
    for name, fn in [
        ("extract", extract), ("analyze", analyze), ("design", design),
        ("execute", execute), ("oracle", oracle), ("mitigate", mitigate),
        ("regenerate", regenerate),
    ]:
        g.add_node(name, fn)

    g.add_edge(START, "extract")
    g.add_edge("extract", "analyze")
    g.add_edge("analyze", "design")
    g.add_edge("design", "execute")
    g.add_edge("execute", "oracle")
    g.add_conditional_edges("oracle", after_oracle, {"mitigate": "mitigate", END: END})
    g.add_edge("mitigate", "regenerate")
    g.add_conditional_edges("regenerate", after_regenerate, {"mitigate": "mitigate", END: END})

    return g.compile()


def _latest_exploited(state: GraphState) -> Finding | None:
    for f in reversed(state.get("findings", [])):
        if f.oracle_verdict == "exploited":
            return f
    return None


def _as_harness(regression: RegressionSpec) -> HarnessSpec:
    """Adapta un RegressionSpec a HarnessSpec para reusar el SandboxPort.

    La regresion re-ejecuta el payload exacto del finding sobre la misma superficie.
    D2/D3 pueden refinar el contrato luego (que el puerto acepte RegressionSpec directo);
    por ahora esta conversion mantiene el skeleton corriendo end-to-end.
    """
    from contracts import Surface

    surfaces = [
        Surface(
            target=s.target,
            threat_ref=regression.regression_for,
            attack_modules=s.attack_modules,
            oracles=s.oracles,
        )
        for s in regression.surfaces
    ]
    return HarnessSpec(
        harness_id=regression.harness_id,
        generated_from=regression.regression_for,
        designer=regression.designer,
        sandbox=regression.sandbox,
        surfaces=surfaces,
        seeds=regression.seeds,
        priority_order=[regression.regression_for],
    )
