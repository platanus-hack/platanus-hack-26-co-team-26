import { useMemo, useState } from "react"

import { ForestDeployEffect } from "@/components/forest-deploy-effect"
import { ForestGraph } from "@/components/forest-graph"
import { DEPTH_GAP, SIBLING_GAP, layoutForest, type Accent, type GraphNode } from "@/lib/forest"
import { cn } from "@/lib/utils"

/**
 * Envuelve ForestGraph con un efecto de "deploy" en Three.js que corre una vez al montar
 * (o cuando cambian los datos). La interaccion (click/seleccion) siempre pasa por el grafo
 * 2D real, nunca por el canvas WebGL — este solo decide cuándo revelarlo.
 */
export function DeployableForest<T>({
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
  const positioned = useMemo(() => layoutForest(roots), [roots])
  const dataKey = positioned.map((n) => n.id).join("|")
  const [settledKey, setSettledKey] = useState<string | null>(null)
  const settled = settledKey === dataKey

  const maxX = Math.max(0, ...positioned.map((n) => n.x))
  const maxY = Math.max(0, ...positioned.map((n) => n.y))
  const width = (maxX + 1) * SIBLING_GAP
  const height = (maxY + 1) * DEPTH_GAP

  if (positioned.length === 0) return null

  return (
    <div className="inline-block border p-4">
      <div className="relative" style={{ width, height }}>
        <div className={cn("transition-opacity duration-200", !settled && "opacity-0")}>
          <ForestGraph roots={roots} accent={accent} selectedId={selectedId} onSelect={onSelect} />
        </div>
        {!settled && (
          <ForestDeployEffect
            key={dataKey}
            nodes={positioned}
            width={width}
            height={height}
            accent={accent}
            onDone={() => setSettledKey(dataKey)}
          />
        )}
      </div>
    </div>
  )
}
