"""harness_spec.json + regression_spec — salida del Designer (D2).

Ver specs/01-data-contracts.md §3 y §6.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

Isolation = Literal["strong", "medium", "weak"]
SandboxBackend = Literal["docker", "subprocess"]


class Honeypot(BaseModel):
    enabled: bool = True
    url: str


class SandboxProfile(BaseModel):
    backend: SandboxBackend = "docker"
    isolation: Isolation = "strong"
    network: str = "deny-all"
    honeypot: Honeypot | None = None
    escape_probe: bool = True  # leccion OpenAI/HF: verificar aislamiento activamente
    syscall_monitor: list[str] = Field(default_factory=list)  # ["execve", "connect", "open"]
    filesystem: str = "ephemeral"
    timeout_ms: int = 60000


class Canary(BaseModel):
    kind: str  # "token"
    plant_at: str  # "env:FAKE_SECRET"
    value: str  # "aeg-canary-7f3a"


class Surface(BaseModel):
    target: str  # "tool.shell"
    threat_ref: str  # "threat.1"
    attack_modules: list[str] = Field(default_factory=list)
    oracles: list[str] = Field(default_factory=list)
    canaries: list[Canary] = Field(default_factory=list)


class Budget(BaseModel):
    max_tokens: int = 200000
    max_cost_usd: float = 2.0
    max_steps: int = 40


class HarnessSpec(BaseModel):
    schema_version: Literal["1.0"] = "1.0"
    harness_id: str  # "hspec-support-a1b2c3"
    generated_from: str  # "customer-support-agent@a1b2c3"
    designer: str = "template-composer-v1"
    sandbox: SandboxProfile
    surfaces: list[Surface] = Field(default_factory=list)
    budget: Budget = Field(default_factory=Budget)
    seeds: list[int] = Field(default_factory=lambda: [42, 1337])
    priority_order: list[str] = Field(default_factory=list)


class RegressionSurface(BaseModel):
    target: str
    replay_payload: str  # "finding.1.payload" — reproduce el payload exacto
    attack_modules: list[str] = Field(default_factory=list)
    oracles: list[str] = Field(default_factory=list)
    expected_result: Literal["resisted"] = "resisted"


class RegressionSpec(BaseModel):
    schema_version: Literal["1.0"] = "1.0"
    harness_id: str  # "hspec-regression-finding.1"
    regression_for: str  # "finding.1"
    mitigation_applied: str  # "policy.1"
    designer: str = "template-composer-v1"
    sandbox: SandboxProfile
    surfaces: list[RegressionSurface] = Field(default_factory=list)
    seeds: list[int] = Field(default_factory=lambda: [42])
