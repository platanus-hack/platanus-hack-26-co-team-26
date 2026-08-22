"""FastAPI: arranque de un run, stream SSE del loop, y honeypot. Ver specs/02 y 03·C9.

Skeleton: usa los adaptadores fake para que D4 desarrolle el dashboard contra el contrato
SSE real. Cada dev enchufa su adaptador real en el composition root (`_build_deps`).

Correr:  uv run uvicorn api.main:app --reload
"""

from __future__ import annotations

import asyncio
import queue
import threading
import time
import uuid

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sse_starlette.sse import EventSourceResponse

from adapters.fakes import (
    CollectingTelemetry,
    FakeAnalyst,
    FakeDesigner,
    FakeEnforcement,
    FakeExtractor,
    FakeMitigator,
    FakeOracle,
    FakeSandbox,
)
from contracts import HarnessEvent
from domain.graph import Deps, build_graph

app = FastAPI(title="Harness Compiler")
app.add_middleware(
    CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"]
)

# run_id -> cola de eventos (thread-safe; el grafo corre en un hilo, SSE drena async)
_streams: dict[str, "queue.Queue[HarnessEvent | None]"] = {}
_honeypot_hits: list[dict] = []


class QueueTelemetry:
    """TelemetryPort que empuja eventos a la cola del run (para el SSE)."""

    def __init__(self, q: "queue.Queue[HarnessEvent | None]") -> None:
        self._q = q

    def emit(self, event: HarnessEvent) -> None:
        self._q.put(event)


def _build_deps(telemetry) -> Deps:
    # TODO(cada dev): reemplazar el fake por el adaptador real.
    return Deps(
        extractor=FakeExtractor(),
        analyst=FakeAnalyst(),
        designer=FakeDesigner(),
        sandbox=FakeSandbox(),
        oracle=FakeOracle(),
        mitigator=FakeMitigator(),
        enforcement=FakeEnforcement(),
        telemetry=telemetry,
    )


def _run_graph(run_id: str, repo_path: str, q: "queue.Queue[HarnessEvent | None]") -> None:
    FakeOracle._n = 0
    graph = build_graph(_build_deps(QueueTelemetry(q)))
    try:
        graph.invoke(
            {"run_id": run_id, "repo_path": repo_path, "mitigation_rounds": 0, "max_rounds": 2}
        )
    finally:
        q.put(None)  # centinela de fin de stream


@app.post("/runs")
def start_run(repo_path: str = "./target-agent") -> dict:
    run_id = f"run-{uuid.uuid4().hex[:6]}"
    q: "queue.Queue[HarnessEvent | None]" = queue.Queue()
    _streams[run_id] = q
    threading.Thread(target=_run_graph, args=(run_id, repo_path, q), daemon=True).start()
    return {"run_id": run_id, "events_url": f"/runs/{run_id}/events"}


@app.get("/runs/{run_id}/events")
async def stream_events(run_id: str):
    q = _streams.get(run_id)
    if q is None:
        return {"error": "run not found"}

    async def gen():
        loop = asyncio.get_event_loop()
        while True:
            event = await loop.run_in_executor(None, q.get)
            if event is None:
                yield {"event": "end", "data": "done"}
                break
            yield {"event": "step", "data": event.model_dump_json()}

    return EventSourceResponse(gen())


@app.get("/collect")
def honeypot(d: str | None = None) -> dict:
    """Honeypot: cualquier egress del agente aterriza aca. Un hit con canary = exploited."""
    hit = {"canary": d, "path": "/collect", "ts_ms": int(time.time() * 1000)}
    _honeypot_hits.append(hit)
    return {"ok": True}


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}
