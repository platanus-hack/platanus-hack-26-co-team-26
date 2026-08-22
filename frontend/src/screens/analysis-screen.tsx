import { useCallback, useEffect, useMemo, useRef, useState } from "react"
import { Loader2, Play, TriangleAlert } from "lucide-react"

import { Button } from "@/components/ui/button"
import { Separator } from "@/components/ui/separator"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { DeployableForest } from "@/components/deployable-forest"
import { Eyebrow } from "@/components/eyebrow"
import { NodeDetail } from "@/components/node-detail"
import { PerfSummary } from "@/components/perf-summary"
import { fetchArchitecture, fetchThreatAnalysis, startRun } from "@/lib/api"
import {
  buildExecutionForest,
  buildSecurityForest,
  flattenExecNodes,
  type GraphNode,
} from "@/lib/forest"
import { readSession, writeSession } from "@/lib/storage"
import type { AgentArchitecture, ThreatAnalysis } from "@/lib/types"

type Status = "idle" | "starting" | "analyzing" | "ready" | "error"
type Tree = "security" | "performance"

const POLL_MS = 1200
const POLL_TIMEOUT_MS = 45_000
const STORAGE_KEY = "harness-compiler:analysis"

interface PersistedAnalysis {
  runId: string
  architecture: AgentArchitecture | null
  analysis: ThreatAnalysis
}

function readPersisted(): PersistedAnalysis | null {
  return readSession<PersistedAnalysis>(STORAGE_KEY)
}

export function AnalysisScreen() {
  const persisted = useMemo(() => readPersisted(), [])
  const [status, setStatus] = useState<Status>(persisted ? "ready" : "idle")
  const [runId, setRunId] = useState<string | null>(persisted?.runId ?? null)
  const [architecture, setArchitecture] = useState<AgentArchitecture | null>(
    persisted?.architecture ?? null
  )
  const [analysis, setAnalysis] = useState<ThreatAnalysis | null>(persisted?.analysis ?? null)
  const [errorMessage, setErrorMessage] = useState<string | null>(null)
  const [activeTree, setActiveTree] = useState<Tree>("security")
  const [selectedSecurity, setSelectedSecurity] = useState<GraphNode<unknown> | null>(null)
  const [selectedPerf, setSelectedPerf] = useState<GraphNode<unknown> | null>(null)
  const pollHandle = useRef<ReturnType<typeof setInterval> | null>(null)

  const stopPolling = useCallback(() => {
    if (pollHandle.current !== null) {
      clearInterval(pollHandle.current)
      pollHandle.current = null
    }
  }, [])

  useEffect(() => stopPolling, [stopPolling])

  useEffect(() => {
    if (status === "ready" && runId && analysis) {
      writeSession<PersistedAnalysis>(STORAGE_KEY, { runId, architecture, analysis })
    }
  }, [status, runId, architecture, analysis])

  const handleStart = useCallback(async () => {
    setStatus("starting")
    setErrorMessage(null)
    setAnalysis(null)
    setArchitecture(null)
    setSelectedSecurity(null)
    setSelectedPerf(null)
    try {
      const { run_id } = await startRun()
      setRunId(run_id)
      setStatus("analyzing")

      const deadline = Date.now() + POLL_TIMEOUT_MS
      pollHandle.current = setInterval(async () => {
        const result = await fetchThreatAnalysis(run_id)
        if (result) {
          const arch = await fetchArchitecture(run_id)
          stopPolling()
          setAnalysis(result)
          setArchitecture(arch)
          setStatus("ready")
          return
        }
        if (Date.now() > deadline) {
          stopPolling()
          setStatus("error")
          setErrorMessage("El análisis no terminó a tiempo — revisá el backend.")
        }
      }, POLL_MS)
    } catch (err) {
      setStatus("error")
      setErrorMessage(err instanceof Error ? err.message : "No se pudo iniciar el run.")
    }
  }, [stopPolling])

  const securityThreats = useMemo(
    () => analysis?.threats.filter((t) => t.threat_class === "security") ?? [],
    [analysis]
  )
  const performanceThreats = useMemo(
    () => analysis?.threats.filter((t) => t.threat_class === "performance") ?? [],
    [analysis]
  )
  const securityForest = useMemo(() => buildSecurityForest(securityThreats), [securityThreats])
  const executionForest = useMemo(
    () => (architecture ? buildExecutionForest(architecture, performanceThreats) : []),
    [architecture, performanceThreats]
  )
  const execMetrics = useMemo(() => flattenExecNodes(executionForest), [executionForest])

  return (
    <div className="flex flex-col gap-8">
      <header className="flex flex-col gap-4">
        <div className="flex flex-wrap items-center justify-between gap-4">
          <div className="flex flex-col gap-1">
            <Eyebrow>Harness Compiler</Eyebrow>
            <h1 className="font-display text-2xl font-semibold tracking-tight text-foreground uppercase">
              Análisis
            </h1>
          </div>
          <Button onClick={handleStart} disabled={status === "starting" || status === "analyzing"}>
            {status === "starting" || status === "analyzing" ? (
              <Loader2 className="animate-spin" />
            ) : (
              <Play />
            )}
            {status === "ready" ? "Volver a correr" : "Iniciar análisis"}
          </Button>
        </div>

        {analysis && (
          <div className="flex flex-wrap gap-x-6 gap-y-1 font-mono text-xs text-muted-foreground">
            <span>corrida: {runId}</span>
            <span>arquitectura: {analysis.architecture_ref}</span>
            <span>analista: {analysis.analyzed_by}</span>
          </div>
        )}
      </header>

      <Separator />

      {status === "idle" && (
        <p className="py-16 text-center text-sm text-muted-foreground">
          Corré el compilador para ver los árboles de dependencias de esta corrida.
        </p>
      )}

      {(status === "starting" || status === "analyzing") && (
        <div className="flex items-center justify-center gap-2 py-16 text-sm text-muted-foreground">
          <Loader2 className="size-4 animate-spin" />
          {status === "starting" ? "Levantando la corrida…" : "El analista está razonando el plano…"}
        </div>
      )}

      {status === "error" && (
        <div className="flex items-center justify-center gap-2 py-16 text-sm text-severity-critical">
          <TriangleAlert className="size-4" />
          {errorMessage}
        </div>
      )}

      {status === "ready" && analysis && (
        <Tabs value={activeTree} onValueChange={(v) => setActiveTree(v as Tree)}>
          <TabsList variant="line">
            <TabsTrigger value="security" className="gap-2">
              <span className="size-1.5 bg-class-security" aria-hidden />
              Vulnerabilidades
              <span className="font-mono text-[10px] text-muted-foreground">
                {securityThreats.length}
              </span>
            </TabsTrigger>
            <TabsTrigger value="performance" className="gap-2">
              <span className="size-1.5 bg-class-performance" aria-hidden />
              Rendimiento &amp; confiabilidad
              <span className="font-mono text-[10px] text-muted-foreground">
                {performanceThreats.length}
              </span>
            </TabsTrigger>
          </TabsList>

          <TabsContent value="security" className="flex flex-col gap-4 pt-4">
            <p className="text-xs text-muted-foreground">
              Amenazas explotables — confirmadas por el oráculo, no por el LLM.
            </p>
            <div className="flex flex-col gap-6 lg:flex-row">
              <div className="max-h-[70vh] flex-1 overflow-y-auto">
                <DeployableForest
                  roots={securityForest}
                  accent="security"
                  selectedId={selectedSecurity?.id ?? null}
                  onSelect={setSelectedSecurity}
                />
              </div>
              <div className="w-full shrink-0 lg:sticky lg:top-4 lg:w-96 lg:self-start">
                <NodeDetail node={selectedSecurity} accent="security" />
              </div>
            </div>
          </TabsContent>

          <TabsContent value="performance" className="flex flex-col gap-4 pt-4">
            <p className="text-xs text-muted-foreground">
              Cadena de ejecución real (data_flows) — métricas por nodo simuladas hasta que D3
              instrumente el Sandbox (specs/05).
            </p>
            <PerfSummary key={`perf-summary-${activeTree}`} nodes={execMetrics} />
            <div className="flex flex-col gap-6 lg:flex-row">
              <div className="max-h-[70vh] flex-1 overflow-y-auto">
                <DeployableForest
                  roots={executionForest}
                  accent="performance"
                  selectedId={selectedPerf?.id ?? null}
                  onSelect={setSelectedPerf}
                />
              </div>
              <div className="w-full shrink-0 lg:sticky lg:top-4 lg:w-96 lg:self-start">
                <NodeDetail node={selectedPerf} accent="performance" />
              </div>
            </div>
          </TabsContent>
        </Tabs>
      )}

      {analysis?.notes && (
        <>
          <Separator />
          <p className="font-mono text-xs text-muted-foreground">nota: {analysis.notes}</p>
        </>
      )}
    </div>
  )
}
