// Espejo de contracts/threat_analysis.py (backend). Ver specs/01-data-contracts.md §2 y
// specs/05-performance-thesis.md (threat_class, T3 — propuesta).

export type Severity = "low" | "medium" | "high" | "critical"
export type ThreatClass = "security" | "performance"

export interface Threat {
  id: string
  surface: string
  threat_id: string
  threat_class: ThreatClass
  taxonomy: string[]
  reasoning: string
  evidence_refs: string[]
  confidence: number
  severity: Severity
  attack_hypothesis: string
  recommended_modules: string[]
  recommended_oracle: string[]
  priority: number
}

export interface ThreatAnalysis {
  schema_version: string
  analyzed_by: string
  architecture_ref: string
  threats: Threat[]
  notes?: string | null
}

export interface StartRunResponse {
  run_id: string
  events_url: string
}

export interface ApiError {
  error: string
}

// Espejo de contracts/architecture.py — solo los campos que usa el frontend.

export interface FlowEndpoint {
  kind: string
  at: string
}

export interface DataFlow {
  id: string
  source: FlowEndpoint
  sink: FlowEndpoint
  path: string[]
  sanitized: boolean
}

export interface Tool {
  id: string
  name: string
  kind: string
  defined_at: string
  side_effects: string
  requires_approval: boolean
}

export interface McpTool {
  name: string
  description: string
  side_effects: string
}

export interface McpServer {
  id: string
  name: string
  trust_level: string
  tools: McpTool[]
}

export interface AgentLoop {
  max_iterations: number | null
  budget_enforced: boolean
}

export interface AgentInfo {
  name: string
  runtime: string
  entrypoint: string
}

export interface AgentArchitecture {
  agent: AgentInfo
  tools: Tool[]
  mcp_servers: McpServer[]
  data_flows: DataFlow[]
  agent_loop: AgentLoop
}

// Espejo de contracts/telemetry.py — contrato de eventos SSE del loop.

export type Step =
  | "extract"
  | "analyze"
  | "design"
  | "execute"
  | "oracle"
  | "mitigate"
  | "regenerate"
  | "enforce"

export type EventStatus = "started" | "done" | "error"

export interface HarnessEvent {
  run_id: string
  step: Step
  status: EventStatus
  artifact_ref?: string | null
  verdict?: string | null
  ts_ms: number
  detail: Record<string, unknown>
}
