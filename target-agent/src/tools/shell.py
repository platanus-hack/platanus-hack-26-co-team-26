"""run_shell — la tool de Acme para consultar logs del sistema.

Deliberadamente vulnerable: `command` llega directo a `subprocess.run(..., shell=True)`
sin sanitizar. Es el sink de la superficie `cmd_injection` que el harness compiler
(specs/diagrams/real-case-flow.md) esta hecho para encontrar y luego cerrar (T2).
"""

from __future__ import annotations

import subprocess

from langchain_core.tools import tool


@tool
def run_shell(command: str) -> str:
    """Run a shell command to inspect system logs and return its output."""
    result = subprocess.run(
        command, shell=True, capture_output=True, text=True, timeout=10, check=False
    )
    return result.stdout + result.stderr
