"""contracts/ — los schemas del sistema como modelos Pydantic (fuente de verdad).

Ver specs/01-data-contracts.md para la referencia humana. Un artefacto que no valida
contra estos modelos es un bug del productor, no del consumidor.
"""

from contracts.architecture import (
    AgentArchitecture,
    AgentInfo,
    AgentLoop,
    DataFlow,
    FlowEndpoint,
    McpServer,
    McpTool,
    Rag,
    Secret,
    Tool,
    ToolParameter,
)
from contracts.finding import Finding, OracleEvidence
from contracts.harness_spec import (
    Budget,
    Canary,
    Honeypot,
    HarnessSpec,
    RegressionSpec,
    RegressionSurface,
    SandboxProfile,
    Surface,
)
from contracts.policy import Policy
from contracts.telemetry import HarnessEvent
from contracts.threat_analysis import Threat, ThreatAnalysis

__all__ = [
    # architecture
    "AgentArchitecture",
    "AgentInfo",
    "AgentLoop",
    "DataFlow",
    "FlowEndpoint",
    "McpServer",
    "McpTool",
    "Rag",
    "Secret",
    "Tool",
    "ToolParameter",
    # threat_analysis
    "Threat",
    "ThreatAnalysis",
    # harness_spec
    "Budget",
    "Canary",
    "Honeypot",
    "HarnessSpec",
    "RegressionSpec",
    "RegressionSurface",
    "SandboxProfile",
    "Surface",
    # finding
    "Finding",
    "OracleEvidence",
    # policy
    "Policy",
    # telemetry
    "HarnessEvent",
]
