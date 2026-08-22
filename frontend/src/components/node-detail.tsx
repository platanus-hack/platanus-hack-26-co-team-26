import { ArrowRight, FlaskConical } from "lucide-react"

import { Badge } from "@/components/ui/badge"
import { Gauge } from "@/components/charts/gauge"
import { SeverityBadge } from "@/components/severity-badge"
import { isExecMetrics, isThreat, type Accent, type GraphNode } from "@/lib/forest"

const GAUGE_WIDTH = 132
const GAUGE_HEIGHT = 22

function clampPct(v: number) {
  return Math.max(0, Math.min(100, v))
}

function ChipRow({ label, values }: { label: string; values: string[] }) {
  if (values.length === 0) return null
  return (
    <div className="flex flex-col gap-1.5">
      <span className="font-mono text-[10px] tracking-wider text-muted-foreground uppercase">
        {label}
      </span>
      <div className="flex flex-wrap gap-1.5">
        {values.map((v) => (
          <Badge key={v} variant="outline" className="rounded-sm font-mono text-[11px] font-normal">
            {v}
          </Badge>
        ))}
      </div>
    </div>
  )
}

export function NodeDetail({ node, accent }: { node: GraphNode<unknown> | null; accent: Accent }) {
  if (!node) {
    return (
      <div className="flex h-full items-center justify-center rounded-lg border border-dashed p-6 text-center text-xs text-muted-foreground">
        Elige un nodo del árbol para ver el detalle.
      </div>
    )
  }

  if (isThreat(node.data)) {
    const t = node.data
    return (
      <div className="flex flex-col gap-4 rounded-lg border p-4">
        <div className="flex items-start justify-between gap-3">
          <div className="flex flex-col gap-1">
            <span className="font-mono text-sm font-medium text-foreground">{t.threat_id}</span>
            <span className="font-mono text-xs text-muted-foreground">{t.surface}</span>
          </div>
          <div className="flex flex-col items-end gap-1">
            <SeverityBadge severity={t.severity} />
            <div className="flex items-center gap-1.5">
              <Gauge
                orientation="linear"
                value={Math.round(t.confidence * 100)}
                width={GAUGE_WIDTH}
                height={GAUGE_HEIGHT}
                totalNotches={20}
                minWidth={GAUGE_WIDTH}
              />
              <span className="font-mono text-[10px] text-muted-foreground">
                {Math.round(t.confidence * 100)}%
              </span>
            </div>
          </div>
        </div>
        <p className="text-sm leading-relaxed text-foreground/90">{t.reasoning}</p>
        <div className="flex flex-col gap-1.5">
          <span className="font-mono text-[10px] tracking-wider text-muted-foreground uppercase">
            Hipótesis de ataque
          </span>
          <p className="text-sm leading-relaxed text-muted-foreground">{t.attack_hypothesis}</p>
        </div>
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
          <ChipRow label="Evidencia" values={t.evidence_refs} />
          <ChipRow label="Taxonomía" values={t.taxonomy} />
          <ChipRow label="Módulos" values={t.recommended_modules} />
          <ChipRow label="Oráculo" values={t.recommended_oracle} />
        </div>
      </div>
    )
  }

  if (isExecMetrics(node.data)) {
    const m = node.data
    return (
      <div className="flex flex-col gap-4 rounded-lg border p-4">
        <div className="flex items-start justify-between gap-3">
          <span className="font-mono text-sm font-medium text-foreground">{m.location}</span>
          {m.mocked && (
            <Badge variant="outline" className="gap-1 rounded-sm font-mono text-[10px] text-muted-foreground">
              <FlaskConical className="size-3" />
              simulado
            </Badge>
          )}
        </div>
        <div className="flex flex-col gap-3">
          <MetricGauge label="Invocaciones" value={`${m.calls}×`} pct={clampPct((m.calls / 50) * 100)} />
          <MetricGauge
            label="Duración media"
            value={`${m.avg_ms}ms`}
            pct={clampPct((m.avg_ms / 1000) * 100)}
          />
          <MetricGauge
            label="Tasa de fallas"
            value={`${Math.round(m.failure_rate * 100)}%`}
            pct={Math.round(m.failure_rate * 100)}
          />
        </div>
        <p className="text-xs leading-relaxed text-muted-foreground">
          {m.mocked
            ? "Métrica simulada — placeholder hasta que el Sandbox/Oráculo (D3) entregue duration_ms/iterations_used reales por intento (specs/05-performance-thesis.md)."
            : "Métrica observada durante la corrida."}
        </p>
      </div>
    )
  }

  // Nodo intermedio (superficie/ubicación de código): resumen de lo que cuelga de él.
  const leafCount = countLeaves(node)
  return (
    <div className="flex flex-col gap-3 rounded-lg border p-4">
      <span className="font-mono text-sm font-medium text-foreground">{node.label}</span>
      <div className="flex items-center gap-1.5 text-xs text-muted-foreground">
        <ArrowRight className="size-3" />
        {accent === "security"
          ? `${leafCount} amenaza${leafCount === 1 ? "" : "s"} dependen de esta superficie.`
          : `${leafCount} ubicación${leafCount === 1 ? "" : "es"} aguas abajo en esta cadena.`}
      </div>
    </div>
  )
}

function MetricGauge({ label, value, pct }: { label: string; value: string; pct: number }) {
  return (
    <div className="flex items-center justify-between gap-3 rounded-md border bg-muted/30 px-2.5 py-2">
      <span className="font-mono text-[10px] tracking-wider text-muted-foreground uppercase">
        {label}
      </span>
      <div className="flex items-center gap-2">
        <Gauge
          orientation="linear"
          value={pct}
          width={GAUGE_WIDTH}
          height={GAUGE_HEIGHT}
          totalNotches={20}
          minWidth={GAUGE_WIDTH}
        />
        <span className="w-14 shrink-0 text-right font-mono text-sm text-foreground">
          {value}
        </span>
      </div>
    </div>
  )
}

function countLeaves(node: GraphNode<unknown>): number {
  if (node.children.length === 0) return 1
  return node.children.reduce((sum, c) => sum + countLeaves(c), 0)
}
