"""run_shell — la tool de Acme para consultar logs del sistema.

Deliberadamente vulnerable: `command` llega directo a `subprocess.run(..., shell=True)`
sin sanitizar. Es el sink de la superficie `cmd_injection` que el harness compiler
(specs/diagrams/real-case-flow.md) esta hecho para encontrar y luego cerrar (T2).
"""

from __future__ import annotations

import re
import subprocess

from langchain_core.tools import tool

# Metacaracteres de shell que un sanitizador de entrada (enforcement de D5) removeria.
# Mismo patron que usa el modulo de ataque cmd_injection real (D3) para armar su payload
# (`logs & <egress>`) -- reusarlo garantiza que la regresion T2 neutralice exactamente lo
# que el Sandbox real dispara, no una aproximacion propia que podria no coincidir.
_SHELL_METACHARS = re.compile(r"[;&|`$><\n\r()]|\$\(")


def sanitize_command(user_input: str) -> str:
    """Sanitizador minimo (stand-in del enforcement real de D5/McpProxyGuard).

    Se usa cuando el Sandbox real (D3) corre la regresion (`AEG_SANITIZE=1`, ver
    src/agent.py::handle_user_message) para que T2 cierre por un HECHO (el egress ya no
    ocurre), no por un truco.
    """
    return _SHELL_METACHARS.sub("", user_input)


@tool
def run_shell(command: str) -> str:
    """Run a shell command to inspect system logs and return its output."""
    result = subprocess.run(
        command, shell=True, capture_output=True, text=True, timeout=10, check=False
    )
    return result.stdout + result.stderr
