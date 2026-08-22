import { useCallback, useEffect, useMemo, useRef, useState } from "react"
import { animate, svg as animeSvg } from "animejs"
import { Loader2, Play } from "lucide-react"

import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Eyebrow } from "@/components/eyebrow"
import { Separator } from "@/components/ui/separator"
import { startRun } from "@/lib/api"
import { subscribeToRun } from "@/lib/sse"
import { readSession, writeSession } from "@/lib/storage"
import { cn } from "@/lib/utils"
import type { HarnessEvent, Step } from "@/lib/types"

type RunStatus = "idle" | "starting" | "running" | "closed" | "error"
type NodeStatus = "unreached" | "active" | "done"

interface StepPoint {
  step: Step
  x: number
  y: number
}

const STEP_LABEL_ES: Record<Step, string> = {
  extract: "extracción",
  analyze: "análisis",
  design: "diseño",
  execute: "ejecución",
  oracle: "oráculo",
  mitigate: "mitigación",
  enforce: "aplicación",
  regenerate: "regeneración",
}

// Fila 1: extract -> analyze -> design -> execute -> oracle.
// Fila 2 (el loop T2, de derecha a izquierda): mitigate -> enforce -> regenerate.
const PIPELINE: StepPoint[] = [
  { step: "extract", x: 60, y: 60 },
  { step: "analyze", x: 260, y: 60 },
  { step: "design", x: 460, y: 60 },
  { step: "execute", x: 660, y: 60 },
  { step: "oracle", x: 860, y: 60 },
  { step: "mitigate", x: 660, y: 220 },
  { step: "enforce", x: 460, y: 220 },
  { step: "regenerate", x: 260, y: 220 },
]
const CLOSED_POINT = { x: 60, y: 220 }
const START_POINT = { x: PIPELINE[0].x - 70, y: PIPELINE[0].y }

const NODE_W = 92
const NODE_H = 32
const SVG_WIDTH = 940
const SVG_HEIGHT = 280

// [start virtual, ...PIPELINE, closed] — un segmento fijo entre cada par consecutivo. El
// punto 0 (virtual) no tiene caja; todos los demas si (mismo NODE_W/NODE_H que las cajas).
const ALL_POINTS = [START_POINT, ...PIPELINE.map((p) => ({ x: p.x, y: p.y })), CLOSED_POINT]
const CLOSED_INDEX = ALL_POINTS.length - 1
const HAS_BOX = ALL_POINTS.map((_, i) => i > 0)

/** Punto donde una linea desde `center` hacia (dirX,dirY) cruza el borde de una caja
 * NODE_W x NODE_H centrada en `center` — asi los segmentos terminan en el borde, no en el
 * centro (si terminaran en el centro, se verian "por debajo" de la caja cuando esta se
 * pone translucida, ej. durante animate-pulse). */
function edgePoint(center: { x: number; y: number }, dirX: number, dirY: number) {
  const halfW = NODE_W / 2 + 3
  const halfH = NODE_H / 2 + 3
  const tx = dirX !== 0 ? halfW / Math.abs(dirX) : Infinity
  const ty = dirY !== 0 ? halfH / Math.abs(dirY) : Infinity
  const t = Math.min(tx, ty)
  return { x: center.x + dirX * t, y: center.y + dirY * t }
}

const SEGMENTS = ALL_POINTS.slice(0, -1).map((from, i) => {
  const to = ALL_POINTS[i + 1]
  const dx = to.x - from.x
  const dy = to.y - from.y
  const len = Math.hypot(dx, dy) || 1
  const ux = dx / len
  const uy = dy / len
  return {
    from: HAS_BOX[i] ? edgePoint(from, ux, uy) : from,
    to: HAS_BOX[i + 1] ? edgePoint(to, -ux, -uy) : to,
  }
})

function pointIndexForStep(step: Step): number {
  const idx = PIPELINE.findIndex((p) => p.step === step)
  return idx === -1 ? 0 : idx + 1
}

const VERDICT_STROKE: Record<string, string> = {
  exploited: "stroke-severity-critical text-severity-critical",
  resisted: "stroke-class-performance text-class-performance",
  inconclusive: "stroke-severity-medium text-severity-medium",
}

function nodeStatus(step: Step, events: HarnessEvent[], revealedIndex: number): NodeStatus {
  if (pointIndexForStep(step) > revealedIndex) return "unreached"
  const forStep = events.filter((e) => e.step === step)
  if (forStep.length === 0) return "unreached"
  return forStep.some((e) => e.status === "done") ? "done" : "active"
}

const STORAGE_KEY = "harness-compiler:loop"

interface PersistedLoop {
  runId: string
  events: HarnessEvent[]
  revealedIndex: number
  litSegments: number[]
}

function readPersisted(): PersistedLoop | null {
  return readSession<PersistedLoop>(STORAGE_KEY)
}

export function LoopScreen() {
  const persisted = useMemo(() => readPersisted(), [])
  const [status, setStatus] = useState<RunStatus>(persisted ? "closed" : "idle")
  const [runId, setRunId] = useState<string | null>(persisted?.runId ?? null)
  const [events, setEvents] = useState<HarnessEvent[]>(persisted?.events ?? [])
  const [errorMessage, setErrorMessage] = useState<string | null>(null)
  const [revealedIndex, setRevealedIndex] = useState(persisted?.revealedIndex ?? 0)
  const [litSegments, setLitSegments] = useState<Set<number>>(
    new Set(persisted?.litSegments ?? [])
  )
  const [playingSegment, setPlayingSegment] = useState<number | null>(null)

  const segmentRefs = useRef<(SVGPathElement | null)[]>([])
  const lastEnqueuedIndex = useRef(0)
  const queueRef = useRef<number[]>([])
  const playingRef = useRef(false)
  const unsubscribeRef = useRef<(() => void) | null>(null)

  // Solo persistimos una corrida ya CERRADA (no "running": la conexion SSE no sobrevive a
  // cambiar de pestana, asi que restaurar un estado "en curso" quedaria trabado para siempre).
  useEffect(() => {
    if (status === "closed" && runId) {
      writeSession<PersistedLoop>(STORAGE_KEY, {
        runId,
        events,
        revealedIndex,
        litSegments: [...litSegments],
      })
    }
  }, [status, runId, events, revealedIndex, litSegments])

  // Las lineas del pipeline se mueven todo el tiempo, como una cadena — no depende del run.
  useEffect(() => {
    const paths = segmentRefs.current.filter((p): p is SVGPathElement => !!p)
    if (paths.length === 0) return
    const controls = animate(paths, {
      strokeDashoffset: [0, -28],
      duration: 900,
      loop: true,
      ease: "linear",
    })
    return () => {
      controls.pause()
    }
  }, [])

  useEffect(() => {
    return () => {
      unsubscribeRef.current?.()
    }
  }, [])

  const drainRef = useRef<() => void>(() => {})
  const drain = useCallback(() => {
    if (playingRef.current) return
    const next = queueRef.current.shift()
    if (next === undefined) return
    playingRef.current = true
    setPlayingSegment(next)

    const pathEl = segmentRefs.current[next]
    if (!pathEl) {
      playingRef.current = false
      return
    }
    const drawable = animeSvg.createDrawable(pathEl)
    animate(drawable, {
      draw: ["0 0", "0 1"],
      duration: 450,
      ease: "inOutSine",
    }).then(() => {
      setLitSegments((prev) => new Set(prev).add(next))
      setRevealedIndex(next + 1)
      setPlayingSegment(null)
      playingRef.current = false
      drainRef.current()
    })
  }, [])
  useEffect(() => {
    drainRef.current = drain
  }, [drain])

  const enqueueTo = useCallback(
    (toIndex: number) => {
      if (toIndex === lastEnqueuedIndex.current) return
      const from = lastEnqueuedIndex.current
      for (let i = from; i < toIndex; i++) queueRef.current.push(i)
      lastEnqueuedIndex.current = toIndex
      drain()
    },
    [drain]
  )

  const handleStart = useCallback(async () => {
    unsubscribeRef.current?.()
    setStatus("starting")
    setErrorMessage(null)
    setEvents([])
    setRevealedIndex(0)
    setLitSegments(new Set())
    setPlayingSegment(null)
    queueRef.current = []
    playingRef.current = false
    lastEnqueuedIndex.current = 0

    try {
      const { run_id } = await startRun()
      setRunId(run_id)
      setStatus("running")

      unsubscribeRef.current = subscribeToRun(
        run_id,
        (event) => {
          setEvents((prev) => [...prev, event])
          enqueueTo(pointIndexForStep(event.step))
          if (event.step === "regenerate" && event.status === "done" && event.verdict === "resisted") {
            enqueueTo(CLOSED_INDEX)
            setStatus("closed")
          }
        },
        () => {
          setStatus((s) => (s === "running" ? "closed" : s))
        }
      )
    } catch (err) {
      setStatus("error")
      setErrorMessage(err instanceof Error ? err.message : "No se pudo iniciar el run.")
    }
  }, [enqueueTo])

  const nodeStatuses = useMemo(
    () =>
      Object.fromEntries(
        PIPELINE.map((p) => [p.step, nodeStatus(p.step, events, revealedIndex)])
      ) as Record<Step, NodeStatus>,
    [events, revealedIndex]
  )

  const closedLit = revealedIndex >= CLOSED_INDEX

  return (
    <div className="flex flex-col gap-8">
      <header className="flex flex-wrap items-center justify-between gap-4">
        <div className="flex flex-col gap-1">
          <Eyebrow>Harness Compiler</Eyebrow>
          <h1 className="font-display text-2xl font-semibold tracking-tight text-foreground uppercase">
            Loop en vivo
          </h1>
        </div>
        <Button onClick={handleStart} disabled={status === "starting" || status === "running"}>
          {status === "starting" || status === "running" ? (
            <Loader2 className="animate-spin" />
          ) : (
            <Play />
          )}
          {status === "closed" ? "Volver a correr" : "Iniciar corrida"}
        </Button>
      </header>

      {runId && (
        <div className="flex flex-wrap items-center gap-3 font-mono text-xs text-muted-foreground">
          <span>corrida: {runId}</span>
          {status === "closed" && (
            <Badge className="gap-1 rounded-sm bg-class-performance/15 font-mono text-[10px] text-class-performance">
              CERRADO — vulnerabilidad mitigada
            </Badge>
          )}
        </div>
      )}

      <Separator />

      {status === "idle" && (
        <p className="text-center text-sm text-muted-foreground">
          Iniciá una corrida para ver el pipeline avanzar en vivo, por SSE.
        </p>
      )}
      {status === "error" && (
        <p className="text-center text-sm text-severity-critical">{errorMessage}</p>
      )}

      <div className="inline-block overflow-x-auto border p-4">
        <div className="relative" style={{ width: SVG_WIDTH, height: SVG_HEIGHT }}>
          <svg width={SVG_WIDTH} height={SVG_HEIGHT} className="absolute inset-0" aria-hidden>
            {SEGMENTS.map((seg, i) => {
              const lit = litSegments.has(i)
              const active = playingSegment === i
              return (
                <path
                  key={i}
                  ref={(el) => {
                    segmentRefs.current[i] = el
                  }}
                  d={`M ${seg.from.x} ${seg.from.y} L ${seg.to.x} ${seg.to.y}`}
                  fill="none"
                  strokeWidth={lit || active ? 2 : 1.5}
                  strokeDasharray={lit ? "none" : "7 6"}
                  className={cn(
                    "transition-[stroke-width] duration-200",
                    lit || active
                      ? "stroke-foreground [filter:drop-shadow(0_0_5px_currentColor)]"
                      : "stroke-border"
                  )}
                />
              )
            })}
            {PIPELINE.map((p) => {
              const st = nodeStatuses[p.step]
              // El veredicto solo se pinta una vez que la luz realmente llego a este nodo —
              // si se leyera del evento crudo sin este guard, oraculo/regenerate (que traen
              // verdict) se "prenderian" apenas llega el evento, saltandose la cola.
              const lastEventForStep =
                st === "unreached"
                  ? undefined
                  : [...events].reverse().find((e) => e.step === p.step)
              const verdictStroke = lastEventForStep?.verdict
                ? VERDICT_STROKE[lastEventForStep.verdict]
                : undefined
              return (
                <g key={p.step}>
                  <rect
                    x={p.x - NODE_W / 2}
                    y={p.y - NODE_H / 2}
                    width={NODE_W}
                    height={NODE_H}
                    fill="none"
                    strokeWidth={st === "unreached" ? 1 : 1.75}
                    className={cn(
                      "transition-[stroke-width] duration-200",
                      verdictStroke
                        ? `${verdictStroke} [filter:drop-shadow(0_0_6px_currentColor)]`
                        : st === "done"
                          ? "stroke-foreground text-foreground [filter:drop-shadow(0_0_5px_currentColor)]"
                          : st === "active"
                            ? "animate-pulse stroke-foreground/70 text-foreground/70"
                            : "stroke-border"
                    )}
                  />
                  <text
                    x={p.x}
                    y={p.y + 4}
                    textAnchor="middle"
                    className={cn(
                      "font-mono text-[10px] uppercase",
                      st === "unreached" ? "fill-muted-foreground" : "fill-foreground"
                    )}
                  >
                    {STEP_LABEL_ES[p.step]}
                  </text>
                </g>
              )
            })}
            <g>
              <rect
                x={CLOSED_POINT.x - NODE_W / 2}
                y={CLOSED_POINT.y - NODE_H / 2}
                width={NODE_W}
                height={NODE_H}
                fill="none"
                strokeWidth={closedLit ? 1.75 : 1}
                className={cn(
                  "transition-[stroke-width] duration-200",
                  closedLit
                    ? "stroke-class-performance text-class-performance [filter:drop-shadow(0_0_7px_currentColor)]"
                    : "stroke-border"
                )}
              />
              <text
                x={CLOSED_POINT.x}
                y={CLOSED_POINT.y + 4}
                textAnchor="middle"
                className={cn(
                  "font-mono text-[10px] uppercase",
                  closedLit ? "fill-class-performance" : "fill-muted-foreground"
                )}
              >
                cerrado
              </text>
            </g>
          </svg>
        </div>
      </div>

      {events.length > 0 && (
        <div className="flex flex-col gap-1.5">
          <Eyebrow>Eventos</Eyebrow>
          <div className="flex max-h-48 flex-col-reverse gap-1 overflow-y-auto rounded-lg border p-2">
            {[...events].reverse().map((e, i) => (
              <div
                key={`${e.step}-${e.status}-${e.ts_ms}-${i}`}
                className="flex items-center gap-3 font-mono text-[11px] text-muted-foreground"
              >
                <span className="w-24 shrink-0 text-foreground">{STEP_LABEL_ES[e.step]}</span>
                <span className="w-16 shrink-0">
                  {e.status === "started" ? "iniciado" : e.status === "done" ? "listo" : "error"}
                </span>
                {e.verdict && (
                  <span
                    className={cn(
                      "shrink-0",
                      e.verdict === "exploited"
                        ? "text-severity-critical"
                        : e.verdict === "resisted"
                          ? "text-class-performance"
                          : "text-severity-medium"
                    )}
                  >
                    {e.verdict === "exploited"
                      ? "explotado"
                      : e.verdict === "resisted"
                        ? "resistido"
                        : "inconcluso"}
                  </span>
                )}
                {e.artifact_ref && <span className="truncate">{e.artifact_ref}</span>}
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
