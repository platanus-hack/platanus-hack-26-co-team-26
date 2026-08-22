// Modelo de "threat forest": un grafo de dependencias, no una lista plana. El arbol de
// seguridad se deriva 100% de datos reales (Threat.surface/evidence_refs). El arbol de
// rendimiento se deriva de architecture.data_flows[].path (real) pero le agrega METRICAS
// SIMULADAS por nodo (marcadas `mocked: true`) porque todavia no existe telemetria real de
// ejecucion — ver specs/05-performance-thesis.md. Reemplazar por datos reales cuando D3
// entregue duration_ms/iterations_used en ExecutionTrace/Finding.

import type { AgentArchitecture, Threat } from "@/lib/types"

// Layout compartido entre el grafo 2D (forest-graph.tsx) y el efecto de entrada en
// Three.js (forest-deploy-effect.tsx) — mismas coordenadas de destino en ambos. Arbol
// vertical: SIBLING_GAP separa hermanos en x, DEPTH_GAP separa niveles en y (crece hacia
// abajo).
export const SIBLING_GAP = 176
export const DEPTH_GAP = 96
export const NODE_W = 156
export const NODE_H = 42

// Aproximacion en hex de --class-security/--class-performance (oklch) para WebGL,
// que no puede leer custom properties CSS directamente en un THREE.Color.
export const ACCENT_HEX: Record<Accent, number> = {
  security: 0xe0574a,
  performance: 0x4fd6b0,
}

export type Accent = "security" | "performance"
export type Tone =
  | "neutral"
  | "critical"
  | "high"
  | "medium"
  | "low"
  | "healthy"
  | "degraded"
  | "failing"

export interface ExecMetrics {
  location: string
  calls: number
  avg_ms: number
  failure_rate: number
  mocked: boolean
}

export interface GraphNode<T = unknown> {
  id: string
  label: string
  sublabel?: string
  tone: Tone
  data?: T
  children: GraphNode<T>[]
}

export interface PositionedNode<T = unknown> {
  id: string
  label: string
  sublabel?: string
  tone: Tone
  data?: T
  x: number
  y: number
  parentId?: string
}

/**
 * Layout de arbol vertical: y = profundidad (crece hacia abajo), x = orden entre hermanos
 * (post-order; internos = promedio de hijos, para quedar centrados sobre su subarbol).
 */
export function layoutForest<T>(roots: GraphNode<T>[]): PositionedNode<T>[] {
  const result: PositionedNode<T>[] = []
  let leafOrder = 0

  function place(node: GraphNode<T>, depth: number, parentId?: string): number {
    let order: number
    if (node.children.length === 0) {
      order = leafOrder++
    } else {
      const childOrders = node.children.map((c) => place(c, depth + 1, node.id))
      order = childOrders.reduce((a, b) => a + b, 0) / childOrders.length
    }
    result.push({
      id: node.id,
      label: node.label,
      sublabel: node.sublabel,
      tone: node.tone,
      data: node.data,
      x: order,
      y: depth,
      parentId,
    })
    return order
  }

  for (const root of roots) place(root, 0)
  return result
}

/**
 * Arbol de dependencias de amenazas: superficie (tool/mcp) -> superficie -> threat.
 * Las superficies se comparten (mismo id = mismo nodo) asi que un threat single-surface y
 * uno multi-paso que usan la misma tool cuelgan del MISMO nodo de superficie.
 */
export function buildSecurityForest(threats: Threat[]): GraphNode<Threat>[] {
  const surfaceNodes = new Map<string, GraphNode<Threat>>()
  const hasParent = new Set<string>()

  function surfaceNode(id: string): GraphNode<Threat> {
    let node = surfaceNodes.get(id)
    if (!node) {
      node = { id: `surface:${id}`, label: id, tone: "neutral", children: [] }
      surfaceNodes.set(id, node)
    }
    return node
  }

  for (const t of threats.sort((a, b) => a.priority - b.priority)) {
    const parts = t.surface.split(" + ").map((s) => s.trim())
    let prev: GraphNode<Threat> | null = null
    for (const part of parts) {
      const node = surfaceNode(part)
      if (prev && !prev.children.includes(node)) {
        prev.children.push(node)
        hasParent.add(node.id)
      }
      prev = node
    }
    prev!.children.push({
      id: t.id,
      label: t.threat_id,
      sublabel: `#${t.priority} · ${Math.round(t.confidence * 100)}% conf.`,
      tone: t.severity,
      data: t,
      children: [],
    })
  }

  return [...surfaceNodes.values()]
    .filter((n) => !hasParent.has(n.id))
    .sort((a, b) => a.label.localeCompare(b.label))
}

function seededMetrics(id: string): Omit<ExecMetrics, "location" | "mocked"> {
  let h = 0
  for (let i = 0; i < id.length; i++) h = (h * 31 + id.charCodeAt(i)) >>> 0
  return {
    calls: 3 + (h % 40),
    avg_ms: 40 + (h % 900),
    failure_rate: Math.round((((h >> 3) % 100) / 100) * 35) / 100,
  }
}

function toneForFailureRate(rate: number): Tone {
  if (rate > 0.2) return "failing"
  if (rate > 0.08) return "degraded"
  return "healthy"
}

function locationNode(location: string): GraphNode<ExecMetrics> {
  const metrics = seededMetrics(location)
  return {
    id: `loc:${location}`,
    label: location.split("/").pop() ?? location,
    sublabel: `${metrics.calls}× · ${metrics.avg_ms}ms · ${Math.round(metrics.failure_rate * 100)}% fallas`,
    tone: toneForFailureRate(metrics.failure_rate),
    data: { location, mocked: true, ...metrics },
    children: [],
  }
}

/**
 * Arbol de ejecucion/rendimiento: una cadena por data_flow (real, path ya viene en
 * architecture.json) + un nodo por tool/mcp no cubierto por ningun flow + el/los threat(s)
 * "wallet_dos" (reales, propuestos por el LLM) colgando de un nodo agent_loop si aplica.
 */
export function buildExecutionForest(
  architecture: AgentArchitecture,
  performanceThreats: Threat[]
): GraphNode<ExecMetrics | Threat>[] {
  const seen = new Set<string>()
  const roots: GraphNode<ExecMetrics | Threat>[] = []

  for (const flow of architecture.data_flows) {
    const locations = flow.path.length > 0 ? flow.path : [flow.source.at, flow.sink.at]
    let root: GraphNode<ExecMetrics> | null = null
    let tail: GraphNode<ExecMetrics> | null = null
    for (const loc of locations) {
      const node = locationNode(loc)
      seen.add(loc)
      if (tail) tail.children.push(node)
      else root = node
      tail = node
    }
    if (root) roots.push(root)
  }

  for (const tool of architecture.tools) {
    if (seen.has(tool.defined_at)) continue
    seen.add(tool.defined_at)
    roots.push(locationNode(tool.defined_at))
  }

  if (architecture.agent_loop.max_iterations === null && performanceThreats.length > 0) {
    roots.unshift({
      id: "loc:agent_loop",
      label: architecture.agent.entrypoint,
      sublabel: "agent_loop · sin límite (dato real)",
      tone: "failing",
      children: performanceThreats
        .sort((a, b) => a.priority - b.priority)
        .map((t) => ({
          id: t.id,
          label: t.threat_id,
          sublabel: `#${t.priority} · ${Math.round(t.confidence * 100)}% conf.`,
          tone: t.severity,
          data: t,
          children: [],
        })),
    })
  }

  return roots
}

/** Aplana un forest a la lista de ExecMetrics reales que contiene (ignora nodos Threat). */
export function flattenExecNodes(roots: GraphNode<ExecMetrics | Threat>[]): ExecMetrics[] {
  const out: ExecMetrics[] = []
  function visit(node: GraphNode<ExecMetrics | Threat>) {
    if (isExecMetrics(node.data)) out.push(node.data)
    node.children.forEach(visit)
  }
  roots.forEach(visit)
  return out
}

export function isThreat(data: unknown): data is Threat {
  return !!data && typeof data === "object" && "attack_hypothesis" in data
}

export function isExecMetrics(data: unknown): data is ExecMetrics {
  return !!data && typeof data === "object" && "avg_ms" in data
}
