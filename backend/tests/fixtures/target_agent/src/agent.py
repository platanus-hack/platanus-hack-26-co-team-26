"""Agente objetivo de prueba — "Acme Support Agent" v0 (LangChain de mentira, Python real).

Un agente de soporte que, ante un mensaje del usuario, usa su tool `run_shell` para
"consultar logs". El input del usuario fluye a la shell SIN sanitizar (ver tools/shell.py).

Ejecutable como script para que el Sandbox (D3) lo lance en subproceso aislado:

    python target-agent/src/agent.py --message "muéstrame logs de pagos"

Salida: una línea JSON a stdout con lo que hizo (para la ExecutionTrace del sandbox).
Honra dos variables de entorno que planta el sandbox:
  - FAKE_SECRET / HONEYPOT_URL : canary y honeypot (el ataque los exfiltra si hay inyección)
  - AEG_SANITIZE=1             : simula el enforcement de D5 aplicado (regresión T2)
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

# Permite importar `tools.shell` tanto como script suelto como desde el paquete.
sys.path.insert(0, str(Path(__file__).resolve().parent))

from tools.shell import run_shell  # noqa: E402


def handle_message(message: str) -> dict:
    """El 'razonamiento' del agente v0: toda consulta va directo a run_shell."""
    do_sanitize = os.environ.get("AEG_SANITIZE") == "1"
    result = run_shell(message, do_sanitize=do_sanitize)
    return {
        "agent": "customer-support-agent",
        "action": "run_shell",
        "input": message,
        "result": result,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Acme Support Agent v0 (vulnerable de prueba)")
    parser.add_argument("--message", required=True, help="mensaje del usuario (untrusted)")
    args = parser.parse_args(argv)

    outcome = handle_message(args.message)
    # Una sola línea JSON: el sandbox la parsea para la traza.
    print(json.dumps(outcome, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
