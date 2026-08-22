"""Wrapper de Semgrep — corroboracion del flujo untrusted->sink (specs/03-components.md #C1).

Nunca deja que la ausencia o el fallo de Semgrep tumbe la extraccion: si el binario no
esta instalado, o el subprocess falla/da timeout, o el JSON no parsea, se degrada a
`None` (extraccion continua solo con ast) en vez de propagar la excepcion.
"""

from __future__ import annotations

import json
import logging
import shutil
import subprocess
from pathlib import Path

logger = logging.getLogger(__name__)

RULES_DIR = Path(__file__).parent / "rules"


def run_semgrep(repo_path: Path, timeout: int = 30) -> list[dict] | None:
    """-> lista de hallazgos, o None si semgrep no pudo correr (fallback explicito)."""
    if shutil.which("semgrep") is None:
        logger.warning("semgrep no encontrado en PATH; se omite la corroboracion")
        return None
    try:
        proc = subprocess.run(
            ["semgrep", "--config", str(RULES_DIR), "--json", "--quiet", str(repo_path)],
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
        payload = json.loads(proc.stdout or "{}")
        return payload.get("results", [])
    except (subprocess.TimeoutExpired, json.JSONDecodeError, OSError) as exc:
        logger.warning("semgrep fallo (%s); se omite la corroboracion", exc)
        return None
