"""policy.json — salida de la Mitigacion LLM (D5). Ver specs/01-data-contracts.md §5."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

PolicyKind = Literal["input_sanitizer", "scope_restriction", "network_deny", "approval_gate"]


class Policy(BaseModel):
    schema_version: Literal["1.0"] = "1.0"
    id: str  # "policy.1"
    for_finding: str  # "finding.1" — solo para findings exploited
    kind: PolicyKind
    target: str  # "tool.shell"
    rule: dict[str, Any] = Field(default_factory=dict)  # p.ej. {"strip_metacharacters": true}
    generated_by: str = "llm-mitigator-v1"
    enforcement_point: str  # "mcp_proxy_guard"
