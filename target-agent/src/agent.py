"""Acme support agent — entrypoint (ver specs/diagrams/real-case-flow.md).

Blanco de prueba deliberadamente vulnerable para el Harness Compiler: `run_shell` recibe
input del usuario directo a un sink de shell sin sanitizar, hay un servidor MCP third-party
(Notion) en el loop, y una API key vive en el contexto del agente.

D1 (Extractor) parsea este archivo y tools/ con `ast` — nada de esto necesita ejecutarse
para que la extraccion funcione. TAMBIEN es ejecutable como script para que el Sandbox
real (D3, `adapters/sandbox/subprocess_sandbox.py`) lo corra en subproceso aislado:

    python target-agent/src/agent.py --message "mensaje del usuario"

Imprime una linea JSON a stdout (la ExecutionTrace del sandbox la parsea). El canary y
`HONEYPOT_URL` que planta el sandbox llegan solos al subproceso de `run_shell` (hereda el
env del proceso padre) -- no hace falta leerlos aca. `AEG_SANITIZE=1` (que el sandbox
planta en la regresion T2) sí se maneja explícitamente: ver `handle_user_message`.

Conectar un loop LLM real que orqueste estas tools con un modelo de verdad (en vez de
"toda consulta va directo a run_shell") queda fuera del alcance de los criterios de
aceptacion del Extractor (specs/03-components.md #C1) — es roadmap, no bloquea T1/T2.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

# Permite correr este archivo como script suelto (asi lo invoca el Sandbox real, D3) ademas
# de importarlo como paquete -- con imports relativos normales, `python src/agent.py` directo
# revienta con "attempted relative import with no known parent package".
sys.path.insert(0, str(Path(__file__).resolve().parent))

from tools.email import send_email
from tools.shell import run_shell, sanitize_command

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
    # Sin sanitizar por defecto — a proposito. Salvo que el Sandbox real este corriendo la
    # regresion T2 (enforcement de D5 aplicado, simulado via AEG_SANITIZE=1): ahi si se
    # limpia, para que el loop cierre por un HECHO (el egress deja de ocurrir), no un truco.
    if os.environ.get("AEG_SANITIZE") == "1":
        message = sanitize_command(message)
    return run_shell.invoke({"command": message})


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Acme Support Agent (blanco de prueba)")
    parser.add_argument("--message", required=True, help="mensaje del usuario (untrusted)")
    args = parser.parse_args(argv)

    result = handle_user_message(args.message)
    # Una sola linea JSON: el Sandbox real (D3) la parsea para la ExecutionTrace.
    print(
        json.dumps(
            {"agent": AGENT_NAME, "action": "run_shell", "input": args.message, "result": result},
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
