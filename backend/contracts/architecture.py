"""architecture.json — salida del Extractor (D1). Ver specs/01-data-contracts.md §1."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

SideEffect = Literal["none", "read", "write", "destructive"]
SourceTrust = Literal["untrusted", "trusted", "unknown"]
ToolKind = Literal["shell", "http", "sql", "filesystem", "code_exec"]
TrustLevel = Literal["first_party", "third_party", "unknown"]


class ToolParameter(BaseModel):
    name: str
    type: str
    source_trust: SourceTrust


class Tool(BaseModel):
    id: str  # p.ej. "tool.shell"
    name: str
    kind: ToolKind
    defined_at: str  # "src/tools/shell.ts:18"
    side_effects: SideEffect
    requires_approval: bool = False
    parameters: list[ToolParameter] = Field(default_factory=list)
    reachable_binaries: list[str] = Field(default_factory=list)


class McpTool(BaseModel):
    name: str
    schema_hash: str
    description_hash: str
    description: str
    side_effects: SideEffect


class McpServer(BaseModel):
    id: str  # "mcp.notion"
    name: str
    url: str
    transport: str  # "sse" | "stdio" | ...
    trust_level: TrustLevel
    tools: list[McpTool] = Field(default_factory=list)


class FlowEndpoint(BaseModel):
    kind: str  # "user_input" | "shell_exec" | ...
    at: str


class DataFlow(BaseModel):
    id: str  # "flow.1"
    source: FlowEndpoint
    sink: FlowEndpoint
    path: list[str] = Field(default_factory=list)
    sanitized: bool


class Secret(BaseModel):
    id: str  # "secret.api_key"
    at: str
    kind: str  # "api_key" | ...
    in_context: bool


class Rag(BaseModel):
    present: bool
    vector_store: str | None = None
    ingestion_trusted: bool = False
    retrieval_at: str | None = None


class AgentLoop(BaseModel):
    max_iterations: int | None = None
    budget_enforced: bool = False


class AgentInfo(BaseModel):
    name: str
    runtime: str  # "python" | "typescript" | ...
    entrypoint: str


class AgentArchitecture(BaseModel):
    schema_version: Literal["1.0"] = "1.0"
    agent: AgentInfo
    tools: list[Tool] = Field(default_factory=list)
    mcp_servers: list[McpServer] = Field(default_factory=list)
    data_flows: list[DataFlow] = Field(default_factory=list)
    secrets: list[Secret] = Field(default_factory=list)
    rag: Rag | None = None
    agent_loop: AgentLoop = Field(default_factory=AgentLoop)
