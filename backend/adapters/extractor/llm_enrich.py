"""Pasada LLM opcional (specs/03-components.md #C1): refina side_effects, trust_level y
descripciones de tools MCP.

Guardrails anti-alucinacion:
- Sin `ANTHROPIC_API_KEY` es un no-op garantizado — no intenta red. Los tests y CI corren
  sin secretos.
- El LLM solo puede tocar campos de entidades cuyo `id` ya detecto `ast`. Cualquier `id`
  que mencione y no exista en la arquitectura base se descarta silenciosamente (con
  warning) — no puede inventar tools, mcp_servers ni data_flows nuevos.
- Cualquier excepcion durante la llamada (red, validacion, parseo) hace que se conserve
  la extraccion ast-only sin romper el pipeline.
"""

from __future__ import annotations

import logging
import os

from pydantic import BaseModel, Field

from contracts import AgentArchitecture

logger = logging.getLogger(__name__)

_VALID_SIDE_EFFECTS = {"none", "read", "write", "destructive"}
_VALID_TRUST_LEVELS = {"first_party", "third_party", "unknown"}


class _ToolPatch(BaseModel):
    id: str
    side_effects: str | None = None


class _McpServerPatch(BaseModel):
    id: str
    trust_level: str | None = None


class _McpToolPatch(BaseModel):
    server_id: str
    name: str
    description: str | None = None


class _EnrichmentPatch(BaseModel):
    tools: list[_ToolPatch] = Field(default_factory=list)
    mcp_servers: list[_McpServerPatch] = Field(default_factory=list)
    mcp_tools: list[_McpToolPatch] = Field(default_factory=list)


def enrich(arch: AgentArchitecture) -> AgentArchitecture:
    if not os.getenv("ANTHROPIC_API_KEY"):
        return arch

    try:
        patch = _ask_llm(arch)
    except Exception:
        logger.warning(
            "la pasada LLM de enriquecimiento fallo; se conserva la extraccion ast-only",
            exc_info=True,
        )
        return arch

    return _apply_patch(arch, patch)


def _ask_llm(arch: AgentArchitecture) -> _EnrichmentPatch:
    from langchain_anthropic import ChatAnthropic

    model = ChatAnthropic(model="claude-haiku-4-5-20251001", temperature=0)
    structured = model.with_structured_output(_EnrichmentPatch)
    prompt = (
        "Sobre esta arquitectura de agente ya extraida por ast, refina SOLO "
        "side_effects, trust_level y descripciones de tools MCP existentes. "
        "No inventes tools, mcp_servers ni ids nuevos.\n\n" + arch.model_dump_json(indent=2)
    )
    result = structured.invoke(prompt)
    if not isinstance(result, _EnrichmentPatch):
        raise TypeError(f"salida LLM inesperada: {type(result)!r}")
    return result


def _apply_patch(arch: AgentArchitecture, patch: _EnrichmentPatch) -> AgentArchitecture:
    known_tool_ids = {t.id for t in arch.tools}
    known_server_ids = {s.id for s in arch.mcp_servers}
    data = arch.model_dump()

    for tp in patch.tools:
        if tp.id not in known_tool_ids:
            logger.warning("LLM propuso side_effects para tool inexistente %r; descartado", tp.id)
            continue
        if tp.side_effects not in _VALID_SIDE_EFFECTS:
            continue
        for t in data["tools"]:
            if t["id"] == tp.id:
                t["side_effects"] = tp.side_effects

    for sp in patch.mcp_servers:
        if sp.id not in known_server_ids:
            logger.warning(
                "LLM propuso trust_level para mcp_server inexistente %r; descartado", sp.id
            )
            continue
        if sp.trust_level not in _VALID_TRUST_LEVELS:
            continue
        for s in data["mcp_servers"]:
            if s["id"] == sp.id:
                s["trust_level"] = sp.trust_level

    for mtp in patch.mcp_tools:
        if mtp.server_id not in known_server_ids:
            logger.warning(
                "LLM propuso description para mcp_server inexistente %r; descartado",
                mtp.server_id,
            )
            continue
        for s in data["mcp_servers"]:
            if s["id"] != mtp.server_id:
                continue
            tool_names = {t["name"] for t in s["tools"]}
            if mtp.name not in tool_names:
                logger.warning(
                    "LLM propuso description para mcp tool inexistente %r; descartado", mtp.name
                )
                continue
            for t in s["tools"]:
                if t["name"] == mtp.name and mtp.description:
                    t["description"] = mtp.description

    return AgentArchitecture.model_validate(data)
