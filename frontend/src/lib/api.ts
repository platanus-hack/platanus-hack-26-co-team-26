import type { AgentArchitecture, ApiError, StartRunResponse, ThreatAnalysis } from "@/lib/types"

const API_BASE = import.meta.env.VITE_API_URL ?? "http://localhost:8000"

export async function startRun(repoPath = "./target-agent"): Promise<StartRunResponse> {
  const res = await fetch(`${API_BASE}/runs?repo_path=${encodeURIComponent(repoPath)}`, {
    method: "POST",
  })
  if (!res.ok) throw new Error(`POST /runs failed: ${res.status}`)
  return res.json()
}

/** null mientras el analista todavia no termino ("analyze" step en el SSE). */
export async function fetchThreatAnalysis(runId: string): Promise<ThreatAnalysis | null> {
  const res = await fetch(`${API_BASE}/runs/${runId}/threat_analysis`)
  const data: ThreatAnalysis | ApiError = await res.json()
  if ("error" in data) return null
  return data
}

/** null mientras el extractor todavia no termino ("extract" step en el SSE). */
export async function fetchArchitecture(runId: string): Promise<AgentArchitecture | null> {
  const res = await fetch(`${API_BASE}/runs/${runId}/architecture`)
  const data: AgentArchitecture | ApiError = await res.json()
  if ("error" in data) return null
  return data
}
