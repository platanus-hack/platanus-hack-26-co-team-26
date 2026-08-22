import type { HarnessEvent } from "@/lib/types"

const API_BASE = import.meta.env.VITE_API_URL ?? "http://localhost:8000"

/** Se suscribe a GET /runs/{run_id}/events (SSE). Devuelve una funcion para desuscribirse. */
export function subscribeToRun(
  runId: string,
  onEvent: (event: HarnessEvent) => void,
  onEnd: () => void
): () => void {
  const source = new EventSource(`${API_BASE}/runs/${runId}/events`)

  source.addEventListener("step", (e) => {
    const event = JSON.parse((e as MessageEvent).data) as HarnessEvent
    onEvent(event)
  })

  source.addEventListener("end", () => {
    onEnd()
    source.close()
  })

  return () => source.close()
}
