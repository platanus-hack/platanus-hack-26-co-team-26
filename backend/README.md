# Harness Compiler — backend

Ver `../specs/` para el diseño completo (SDD). Este paquete implementa el pipeline como un
grafo LangGraph tras puertos hexagonales.

## Layout

```
contracts/   los schemas del sistema como modelos Pydantic (fuente de verdad)
domain/      puertos (ports.py) + el grafo LangGraph (graph.py) + tipos internos
adapters/    implementaciones de los puertos (fakes.py = mocks del caso "Acme")
api/         FastAPI: arranque de run + stream SSE + honeypot
storage/     SQLite + writer de runs/<id>/   (por construir)
tests/       walking skeleton end-to-end
```

## Setup (uv)

```bash
# instalar uv si no lo tienes:  curl -LsSf https://astral.sh/uv/install.sh | sh
uv sync
```

## Correr

```bash
# walking skeleton (fakes) — debe cerrar el loop T2 en `resisted`:
uv run python -m tests.test_skeleton

# tests:
uv run pytest

# API + SSE (para el dashboard de D4):
uv run uvicorn api.main:app --reload
#   POST /runs                -> {run_id, events_url}
#   GET  /runs/{run_id}/events -> stream SSE de HarnessEvent
#   GET  /collect?d=<canary>   -> honeypot
```

## Cómo enchufar tu adaptador real

1. Implementa tu puerto de `domain/ports.py` en `adapters/<tu_area>/`.
2. Reemplaza el fake correspondiente en el composition root: `api/main.py::_build_deps`
   (y en `tests/test_skeleton.py::_deps`).
3. El resto del grafo no cambia — eso es la arquitectura hexagonal.

## Estado

- ✅ Contratos Pydantic (los 6 schemas)
- ✅ Puertos (9 Protocols) + grafo LangGraph con loop T2
- ✅ Fakes + walking skeleton (cierra T2)
- ✅ API FastAPI + SSE + honeypot (skeleton contra fakes)
- ⬜ Adaptadores reales (cada dev su área)
- ⬜ `storage/` SQLite + persistencia `runs/<id>/`
