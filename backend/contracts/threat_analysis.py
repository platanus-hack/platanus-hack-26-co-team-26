"""threat_analysis.json — salida del Analista LLM (D5). Ver specs/01-data-contracts.md §2."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

Severity = Literal["low", "medium", "high", "critical"]


class Threat(BaseModel):
    id: str  # "threat.1"
    surface: str  # "tool.shell" | "mcp.notion + tool.email"
    threat_id: str  # "cmd_injection" | "exfil_chain" | ...
    taxonomy: list[str] = Field(default_factory=list)  # ["OWASP-AS106", "MITRE-ATLAS-T0051"]
    reasoning: str
    evidence_refs: list[str] = Field(default_factory=list)  # IDs de architecture.json
    confidence: float = Field(ge=0.0, le=1.0)
    severity: Severity
    attack_hypothesis: str
    recommended_modules: list[str] = Field(default_factory=list)
    recommended_oracle: list[str] = Field(default_factory=list)
    priority: int  # orden total, sin empates


class ThreatAnalysis(BaseModel):
    schema_version: Literal["1.0"] = "1.0"
    analyzed_by: str  # "claude-sonnet"
    architecture_ref: str  # "customer-support-agent@a1b2c3"
    threats: list[Threat] = Field(default_factory=list)
    notes: str | None = None
