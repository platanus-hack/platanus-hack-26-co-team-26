import { useEffect, useMemo, useRef } from "react"
import { animate, stagger, svg as animeSvg } from "animejs"

import { cn } from "@/lib/utils"
import type { Accent, GraphNode, Tone } from "@/lib/forest"
import { DEPTH_GAP, NODE_H, NODE_W, SIBLING_GAP, layoutForest } from "@/lib/forest"

const ACCENT_BORDER: Record<Accent, string> = {
  security: "border-class-security/40 has-[[data-selected=true]]:border-class-security",
  performance: "border-class-performance/40 has-[[data-selected=true]]:border-class-performance",
}

const ACCENT_EDGE: Record<Accent, string> = {
  security: "stroke-class-security/35",
  performance: "stroke-class-performance/35",
}

const TONE_DOT: Record<Tone, string> = {
  neutral: "bg-muted-foreground/60",
  critical: "bg-severity-critical",
  high: "bg-severity-high",
  medium: "bg-severity-medium",
  low: "bg-severity-low",
  healthy: "bg-class-performance",
  degraded: "bg-severity-medium",
  failing: "bg-severity-critical",
}

export function ForestGraph<T>({
  roots,
  accent,
  selectedId,
  onSelect,
}: {
  roots: GraphNode<T>[]
  accent: Accent
  selectedId: string | null
  onSelect: (node: GraphNode<T>) => void
}) {
  const containerRef = useRef<HTMLDivElement>(null)
  const positioned = useMemo(() => layoutForest(roots), [roots])
  const byId = useMemo(() => new Map(positioned.map((n) => [n.id, n])), [positioned])
  const edges = useMemo(
    () =>
      positioned
        .filter((n) => n.parentId)
        .map((n) => ({ from: byId.get(n.parentId!)!, to: n }))
        .filter((e) => e.from),
    [positioned, byId]
  )

  const maxX = Math.max(0, ...positioned.map((n) => n.x))
  const maxY = Math.max(0, ...positioned.map((n) => n.y))
  const width = (maxX + 1) * SIBLING_GAP
  const height = (maxY + 1) * DEPTH_GAP

  const dataKey = positioned.map((n) => n.id).join("|")

  useEffect(() => {
    const el = containerRef.current
    if (!el) return
    const paths = el.querySelectorAll<SVGPathElement>(".forest-edge")
    const nodes = el.querySelectorAll<HTMLElement>(".forest-node")

    if (paths.length > 0) {
      const drawables = animeSvg.createDrawable(paths)
      animate(drawables, {
        draw: ["0 0", "0 1"],
        ease: "inOutSine",
        duration: 450,
        delay: stagger(70),
      })
    }
    if (nodes.length > 0) {
      animate(nodes, {
        opacity: [0, 1],
        translateY: [-8, 0],
        delay: stagger(55, { start: 90 }),
        duration: 360,
        ease: "outQuad",
      })
    }
  }, [dataKey])

  function slotCenterX(x: number) {
    return x * SIBLING_GAP + SIBLING_GAP / 2
  }

  function edgePath(from: { x: number; y: number }, to: { x: number; y: number }) {
    const x1 = slotCenterX(from.x)
    const y1 = from.y * DEPTH_GAP + NODE_H
    const x2 = slotCenterX(to.x)
    const y2 = to.y * DEPTH_GAP
    const midY = (y1 + y2) / 2
    return `M ${x1} ${y1} C ${x1} ${midY}, ${x2} ${midY}, ${x2} ${y2}`
  }

  if (positioned.length === 0) return null

  return (
    <div ref={containerRef} className="relative overflow-x-auto pb-2">
      <div className="relative" style={{ width, height, minWidth: NODE_W }}>
        <svg width={width} height={height} className="absolute inset-0" aria-hidden>
          {edges.map((e) => (
            <path
              key={`${e.from.id}->${e.to.id}`}
              className={cn("forest-edge fill-none stroke-[1.5]", ACCENT_EDGE[accent])}
              d={edgePath(e.from, e.to)}
            />
          ))}
        </svg>
        {positioned.map((n) => (
          <button
            key={n.id}
            type="button"
            data-selected={selectedId === n.id}
            onClick={() => {
              const original = findNode(roots, n.id)
              if (original) onSelect(original)
            }}
            className={cn(
              "forest-node group absolute flex flex-col justify-center gap-0.5 border bg-transparent px-2.5 py-1.5 text-left transition-colors hover:bg-foreground/5",
              ACCENT_BORDER[accent],
              selectedId === n.id && "shadow-[0_0_0_1px_var(--border)]"
            )}
            style={{
              left: slotCenterX(n.x) - NODE_W / 2,
              top: n.y * DEPTH_GAP,
              width: NODE_W,
              height: NODE_H,
            }}
          >
            <span className="flex items-center gap-1.5">
              <span className={cn("size-1.5 shrink-0", TONE_DOT[n.tone])} aria-hidden />
              <span className="truncate font-mono text-[11px] font-medium text-foreground">
                {n.label}
              </span>
            </span>
            {n.sublabel && (
              <span className="truncate pl-3 text-[10px] text-muted-foreground">{n.sublabel}</span>
            )}
          </button>
        ))}
      </div>
    </div>
  )
}

function findNode<T>(roots: GraphNode<T>[], id: string): GraphNode<T> | null {
  for (const root of roots) {
    if (root.id === id) return root
    const found = findNode(root.children, id)
    if (found) return found
  }
  return null
}
