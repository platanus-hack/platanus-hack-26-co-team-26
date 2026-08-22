"""Tool `run_shell` del agente objetivo de prueba (Acme Support Agent v0).

VULNERABLE A PROPÓSITO. El input del usuario se concatena en una cadena de shell y se
ejecuta con `shell=True` sin sanitizar — es la falla `cmd_injection` que Harness Compiler
debe *confirmar con verdad-fundamental* (canary → honeypot), no solo reportar.

El extractor (D1) referencia este flujo como `src/tools/shell.py:<línea de subprocess>`.
En integración real, D1 reemplaza este stub por su agente. Aquí es lo mínimo ejecutable
para que la cadena Sandbox→Ataque→Oráculo (D3) corra end-to-end hoy.
"""

from __future__ import annotations

import re
import subprocess

# Metacaracteres de shell que un sanitizador de entrada (enforcement de D5) removería.
_SHELL_METACHARS = re.compile(r"[;&|`$><\n\r()]|\$\(")


def sanitize(user_input: str) -> str:
    """Sanitizador mínimo (stand-in del enforcement de D5).

    En integración real esto lo hace `McpProxyGuard` (C8, owner D5), no la tool.
    Se deja aquí para que la regresión T2 cierre en `resisted` de forma REAL hoy:
    sin metacaracteres, el `& python -c ...` inyectado deja de ejecutarse.
    """
    return _SHELL_METACHARS.sub("", user_input)


def run_shell(user_input: str, *, do_sanitize: bool = False, timeout_s: float = 10.0) -> dict:
    """Ejecuta una 'consulta de logs' incorporando el input del usuario.

    Vulnerable: `command` = plantilla + input del usuario, ejecutado con `shell=True`.
    Si `do_sanitize` (enforcement aplicado), se limpia el input antes → inyección neutralizada.
    """
    cleaned = sanitize(user_input) if do_sanitize else user_input
    command = f"echo query: {cleaned}"  # <-- SINK: user_input llega a shell_exec sin sanitizar
    completed = subprocess.run(  # noqa: S602 (shell=True intencional: es la vulnerabilidad)
        command,
        shell=True,
        capture_output=True,
        text=True,
        timeout=timeout_s,
    )
    return {
        "command": command,
        "sanitized": do_sanitize,
        "returncode": completed.returncode,
        "stdout": completed.stdout,
        "stderr": completed.stderr,
    }
