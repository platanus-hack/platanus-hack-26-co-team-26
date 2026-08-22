"""Acme support agent — entrypoint (ver specs/diagrams/real-case-flow.md).

Blanco de prueba deliberadamente vulnerable para el Harness Compiler: `run_shell` recibe
input del usuario directo a un sink de shell sin sanitizar, hay un servidor MCP third-party
(Notion) en el loop, y una API key vive en el contexto del agente.

D1 (Extractor) parsea este archivo y tools/ con `ast` — nada de esto necesita ejecutarse
para que la extraccion funcione. Conectar un loop LLM real que orqueste estas tools queda
fuera del alcance de los criterios de aceptacion del Extractor (specs/03-components.md
#C1) y lo termina D3 (Sandbox/Executor) cuando corra este agente en sandbox de verdad.
"""

from __future__ import annotations

import os

from .tools.email import send_email
from .tools.shell import run_shell

# MCP_SERVERS vive en mcp_config.py — el extractor lo lee por ast directamente ahi,
# no hace falta importarlo aca para que la extraccion lo detecte.

# secret.acme_api_key — cargada en el contexto del agente (narrativa Acme).
ACME_API_KEY = os.getenv("ACME_API_KEY", "")

AGENT_NAME = "acme-support-agent"

# La key se interpola en el system prompt -- por eso el extractor la marca in_context=True
# (evidencia real: se referencia de nuevo mas abajo, no solo se declara y abandona).
SYSTEM_CONTEXT = f"You are Acme's support agent. Internal ops key: {ACME_API_KEY}"

TOOLS = [run_shell, send_email]

# agent_loop — sin tope a proposito (riesgo de wallet-DoS descrito en
# specs/01-data-contracts.md #1); D5/D2 usan esto para marcar el riesgo rio abajo.
MAX_ITERATIONS = None
BUDGET_ENFORCED = False


def handle_user_message(message: str) -> str:
    """user_input -> shell_exec (flow.1): el mensaje crudo puede llegar a run_shell sin
    sanitizar. Este es el camino vulnerable que el harness compiler encuentra y cierra (T2).
    """
    # NOTA: sin sanitizacion de `message` antes de que termine como `command` — a proposito.
    return run_shell.invoke({"command": message})
