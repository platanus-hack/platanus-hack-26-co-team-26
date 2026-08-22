"""finding.json — salida del Executor + Oraculo (D3). Ver specs/01-data-contracts.md §4."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

OracleVerdict = Literal["exploited", "resisted", "inconclusive"]
Severity = Literal["low", "medium", "high", "critical"]


class OracleEvidence(BaseModel):
    honeypot_hit: bool = False
    canary: str | None = None
    syscall: str | None = None


class Finding(BaseModel):
    schema_version: Literal["1.0"] = "1.0"
    id: str  # "finding.1"
    threat_ref: str  # "threat.1"
    surface: str  # "tool.shell"
    attack_module: str  # "cmd_injection"
    payload: str
    oracle_verdict: OracleVerdict  # HECHO, no opinion del LLM
    oracle_evidence: OracleEvidence
    repro_steps: list[str] = Field(default_factory=list)
    seed: int
    severity: Severity
