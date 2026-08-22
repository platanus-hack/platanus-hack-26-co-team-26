"""Puertos del dominio (arquitectura hexagonal). Ver specs/02-architecture-ports.md.

El dominio depende SOLO de estos Protocols. Los adaptadores en adapters/ los implementan.
Cambiar de infra (Docker->gVisor, plantillas->LLM) = nuevo adaptador, no refactor del dominio.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from contracts import (
    AgentArchitecture,
    Finding,
    HarnessEvent,
    HarnessSpec,
    Policy,
    RegressionSpec,
    Surface,
    ThreatAnalysis,
)
from domain.types import AttackAttempt, AttackContext, ExecutionTrace


@runtime_checkable
class ArchitectureExtractorPort(Protocol):
    """D1 — lee el repo del agente objetivo y produce su plano."""

    def extract(self, repo_path: str) -> AgentArchitecture: ...


@runtime_checkable
class SecurityAnalystPort(Protocol):
    """D5 (LLM) — razona el plano y propone amenazas priorizadas."""

    def analyze(self, arch: AgentArchitecture) -> ThreatAnalysis: ...


@runtime_checkable
class HarnessDesignerPort(Protocol):
    """D2 — compila el analisis a un rig ejecutable, y regenera para probar T2."""

    def design(self, analysis: ThreatAnalysis) -> HarnessSpec: ...

    def regenerate(self, finding: Finding, policy: Policy) -> RegressionSpec: ...


@runtime_checkable
class SandboxPort(Protocol):
    """D3 — levanta el agente en aislamiento fuerte y dispara los ataques del spec."""

    def run(self, agent_ref: str, spec: HarnessSpec) -> ExecutionTrace: ...


@runtime_checkable
class AttackModulePort(Protocol):
    """D3 — un ataque concreto e intercambiable (cmd_injection, indirect_injection, ...)."""

    id: str

    def applies_to(self, surface: Surface) -> bool: ...

    def attack(self, ctx: AttackContext) -> AttackAttempt: ...


@runtime_checkable
class OraclePort(Protocol):
    """D3 — dicta verdad-fundamental: exploited | resisted | inconclusive."""

    def evaluate(self, trace: ExecutionTrace) -> Finding: ...


@runtime_checkable
class MitigationPort(Protocol):
    """D5 (LLM) — propone una politica que cierra un finding confirmado."""

    def propose(self, finding: Finding) -> Policy: ...


@runtime_checkable
class EnforcementPort(Protocol):
    """D5 — aplica la politica (envuelve la tool / proxy MCP)."""

    def apply(self, policy: Policy) -> None: ...


@runtime_checkable
class TelemetryPort(Protocol):
    """Transversal — emite eventos del loop (SSE al dashboard)."""

    def emit(self, event: HarnessEvent) -> None: ...
