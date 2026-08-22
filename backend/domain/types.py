"""Tipos internos del dominio (no son artefactos del contrato, no se persisten como JSON)."""

from __future__ import annotations

from pydantic import BaseModel, Field

from contracts import Surface


class AttackAttempt(BaseModel):
    """Un intento de ataque disparado por un AttackModule."""

    module_id: str
    surface: str
    payload: str
    repro_steps: list[str] = Field(default_factory=list)
    seed: int


class ExecutionTrace(BaseModel):
    """Lo que el Sandbox observa durante una corrida: intentos + señales crudas."""

    run_id: str
    attempts: list[AttackAttempt] = Field(default_factory=list)
    honeypot_hits: list[dict] = Field(default_factory=list)  # [{canary, path, ts}]
    syscalls: list[str] = Field(default_factory=list)
    escape_probe_contained: bool | None = None


class AttackContext(BaseModel):
    """Contexto que recibe un AttackModule para producir un intento."""

    run_id: str
    surface: Surface
    agent_ref: str
    seed: int
