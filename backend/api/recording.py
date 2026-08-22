"""Wrappers no invasivos que capturan los artefactos completos de una corrida.

El HarnessEvent (SSE, ver contracts/telemetry.py) es deliberadamente liviano — manda
conteos/refs, no el artefacto entero. El dashboard (C9) necesita el `ThreatAnalysis`
completo para renderizar los arboles de amenazas, asi que esta capa envuelve los
adaptadores en el composition root y guarda una copia de cada resultado en memoria, por
run_id. No toca domain/graph.py (de Jorge) ni ningun contrato.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from contracts import (
    AgentArchitecture,
    Finding,
    HarnessSpec,
    Policy,
    RegressionSpec,
    ThreatAnalysis,
)
from domain.ports import (
    ArchitectureExtractorPort,
    HarnessDesignerPort,
    MitigationPort,
    OraclePort,
    SecurityAnalystPort,
)
from domain.types import ExecutionTrace


@dataclass
class RunArtifacts:
    """Ultimo/todos los artefactos conocidos de una corrida, para servir por REST."""

    architecture: AgentArchitecture | None = None
    analysis: ThreatAnalysis | None = None
    harness_spec: HarnessSpec | None = None
    findings: list[Finding] = field(default_factory=list)
    policies: list[Policy] = field(default_factory=list)
    regression: RegressionSpec | None = None


@dataclass
class RecordingExtractor:
    inner: ArchitectureExtractorPort
    store: RunArtifacts

    def extract(self, repo_path: str) -> AgentArchitecture:
        result = self.inner.extract(repo_path)
        self.store.architecture = result
        return result


@dataclass
class RecordingAnalyst:
    inner: SecurityAnalystPort
    store: RunArtifacts

    def analyze(self, arch: AgentArchitecture) -> ThreatAnalysis:
        result = self.inner.analyze(arch)
        self.store.analysis = result
        return result


@dataclass
class RecordingDesigner:
    inner: HarnessDesignerPort
    store: RunArtifacts

    def design(self, analysis: ThreatAnalysis) -> HarnessSpec:
        result = self.inner.design(analysis)
        self.store.harness_spec = result
        return result

    def regenerate(self, finding: Finding, policy: Policy) -> RegressionSpec:
        result = self.inner.regenerate(finding, policy)
        self.store.regression = result
        return result


@dataclass
class RecordingOracle:
    inner: OraclePort
    store: RunArtifacts

    def evaluate(self, trace: ExecutionTrace) -> Finding:
        result = self.inner.evaluate(trace)
        self.store.findings.append(result)
        return result


@dataclass
class RecordingMitigator:
    inner: MitigationPort
    store: RunArtifacts

    def propose(self, finding: Finding) -> Policy:
        result = self.inner.propose(finding)
        self.store.policies.append(result)
        return result
