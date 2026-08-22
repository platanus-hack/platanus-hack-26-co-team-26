# target-agent — Acme Support Agent (blanco de prueba vulnerable)

Agente de prueba usado por el Harness Compiler para demostrar T1/T2. Ver
`specs/diagrams/real-case-flow.md` para la narrativa completa ("Acme Support Agent").

## Que tiene (v1, lo que ya esta commiteado)

- `run_shell` — tool `shell`, `user_input -> shell_exec` sin sanitizar.
- `send_email` — tool de red saliente (clasificada `http`).
- MCP `notion` (third-party) declarado en `src/mcp_config.py`.
- `ACME_API_KEY` cargada en el contexto del agente.

Se analiza **estaticamente** (`ast`) por `backend/adapters/extractor`; no hace falta
instalarlo ni correrlo para extraer su arquitectura — ver `PyAstExtractor.extract()`.

Conectar un loop LLM real que orqueste estas tools (para que D3 lo corra en sandbox de
verdad) es trabajo futuro, fuera del alcance de los criterios de aceptacion del Extractor.

## Demo en vivo de T1 (architecture-aware)

Para mostrar que "agregar una tool cambia el harness", en vivo:

1. Crear `src/tools/database.py` con una tool `query_database` (kind `sql`) — ver
   plantilla abajo.
2. Importarla y agregarla a `TOOLS` en `src/agent.py`.
3. Re-correr el extractor: `architecture.json` va a incluir la tool nueva, y el harness
   que compone el Designer va a atacarla con `sql_injection`.

Plantilla para `src/tools/database.py`:

```python
"""query_database — agregada en vivo para probar T1."""

from langchain_core.tools import tool
import sqlite3


@tool
def query_database(query: str) -> str:
    """Run a read query against the support ticket database."""
    conn = sqlite3.connect("tickets.db")
    return str(conn.execute(query).fetchall())
```

Y en `src/agent.py`:

```python
from .tools.database import query_database
...
TOOLS = [run_shell, send_email, query_database]
```

(`backend/tests/test_extractor.py::test_t1_adding_a_tool_changes_architecture` hace
exactamente esto, de forma programatica sobre una copia temporal, para probarlo en CI sin
tocar este repo.)

## Correr el extractor sobre este agente

```bash
cd backend
uv run python -m adapters.extractor ../target-agent
```

Imprime `architecture.json` por stdout.
