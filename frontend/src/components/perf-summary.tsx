import { useEffect, useMemo, useRef } from "react"
import { animate, stagger } from "animejs"

import type { ExecMetrics } from "@/lib/forest"

function summarize(nodes: ExecMetrics[]) {
  if (nodes.length === 0) {
    return { count: 0, avgFailure: 0, slowest: null as ExecMetrics | null, totalCalls: 0 }
  }
  const totalCalls = nodes.reduce((s, n) => s + n.calls, 0)
  const avgFailure = nodes.reduce((s, n) => s + n.failure_rate, 0) / nodes.length
  const slowest = nodes.reduce((a, b) => (b.avg_ms > a.avg_ms ? b : a))
  return { count: nodes.length, avgFailure, slowest, totalCalls }
}

export function PerfSummary({ nodes }: { nodes: ExecMetrics[] }) {
  const ref = useRef<HTMLDivElement>(null)
  const stats = useMemo(() => summarize(nodes), [nodes])

  useEffect(() => {
    const el = ref.current
    if (!el) return
    const tiles = el.querySelectorAll<HTMLElement>(".perf-stat")
    animate(tiles, {
      opacity: [0, 1],
      translateY: [8, 0],
      delay: stagger(90),
      duration: 340,
      ease: "outQuad",
    })
  }, [])

  if (stats.count === 0) return null

  return (
    <div ref={ref} className="grid grid-cols-3 gap-3 sm:grid-cols-3">
      <Tile label="Ubicaciones" value={`${stats.count}`} />
      <Tile label="Invocaciones totales" value={`${stats.totalCalls}×`} />
      <Tile label="Fallas promedio" value={`${Math.round(stats.avgFailure * 100)}%`} />
    </div>
  )
}

function Tile({ label, value }: { label: string; value: string }) {
  return (
    <div className="perf-stat flex flex-col gap-1 rounded-lg border bg-card/60 px-3 py-2.5">
      <span className="font-mono text-[10px] tracking-wider text-muted-foreground uppercase">
        {label}
      </span>
      <span className="font-mono text-lg text-foreground">{value}</span>
    </div>
  )
}
