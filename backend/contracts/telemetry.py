"""HarnessEvent — contrato de eventos SSE (transversal). Ver specs/02-architecture-ports.md."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

Step = Literal[
    "extract", "analyze", "design", "execute", "oracle", "mitigate", "regenerate", "enforce"
]
Status = Literal["started", "done", "error"]


class HarnessEvent(BaseModel):
    run_id: str  # "run-a1b2"
    step: Step
    status: Status
    artifact_ref: str | None = None  # "finding.1"
    verdict: str | None = None  # "exploited" | "resisted" | ...
    ts_ms: int
    detail: dict[str, Any] = Field(default_factory=dict)
