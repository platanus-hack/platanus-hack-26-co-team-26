"""SubprocessSandbox — backend de ejecución sin Docker (aislamiento medio).

Camino por defecto en dev (la máquina no siempre tiene Docker anidado). Implementa
SandboxPort. Por cada superficie del harness_spec:

  1. resuelve los AttackModule por nombre y genera el/los AttackAttempt (payloads),
  2. planta el canary (env) + HONEYPOT_URL, levanta el honeypot interno,
  3. corre el agente objetivo en subproceso con cwd efímero, env acotado y timeout,
  4. corre `escape_probe`: intenta egress externo real para verificar contención,
  5. recolecta hits del honeypot -> ExecutionTrace (la alimenta el oráculo).

Limitaciones honestas (por eso existe DockerSandbox): un subproceso NO tiene aislamiento
de red; el `escape_probe` normalmente reportará `contained=False` en dev con internet.
Esa es justamente la lección OpenAI/HF: verificar el aislamiento, no asumirlo.

Regresión T2: si el spec es de regresión (`"regression" in harness_id`), se corre con
`AEG_SANITIZE=1` — stand-in del enforcement de D5 (McpProxyGuard) — y el payload deja de
explotar de forma REAL (el oráculo devolverá `resisted`, no por truco sino porque el egress
no ocurre).
"""

from __future__ import annotations

import json
import os
import socket
import subprocess
import sys
import tempfile
from pathlib import Path

from contracts import HarnessSpec, Surface
from domain.types import AttackAttempt, AttackContext, ExecutionTrace

from adapters.attack_modules import get_module

# Claves de entorno mínimas para que el subproceso (y `python` inyectado) funcione.
_ENV_PASSTHROUGH = (
    "PATH", "PATHEXT", "SystemRoot", "SYSTEMROOT", "COMSPEC",
    "TEMP", "TMP", "HOME", "LANG", "LC_ALL",
)
_REPO_ROOT = Path(__file__).resolve().parents[3]
# Agente objetivo ejecutable de D3 (fixture v0). El target-agent de D1 en la raíz es un
# agente @tool para extracción AST, no un script ejecutable; el sandbox usa este fixture como
# default. La integración "sandbox ejecuta el agente real de D1" es un pendiente D1↔D3.
_D3_FIXTURE_AGENT = _REPO_ROOT / "backend" / "tests" / "fixtures" / "target_agent"


class SubprocessSandbox:
    def __init__(
        self,
        *,
        escape_target: tuple[str, int] = ("1.1.1.1", 53),
        escape_timeout_s: float = 2.0,
    ) -> None:
        self._escape_target = escape_target
        self._escape_timeout_s = escape_timeout_s

    # -- SandboxPort ----------------------------------------------------------
    def run(self, agent_ref: str, spec: HarnessSpec) -> ExecutionTrace:
        run_id = spec.generated_from or "run-local"
        is_regression = "regression" in spec.harness_id
        seed = spec.seeds[0] if spec.seeds else 42
        agent_entry = self._resolve_entrypoint(agent_ref)

        honeypot_url = None
        hp = None
        from adapters.sandbox.honeypot import Honeypot

        attempts: list[AttackAttempt] = []
        syscalls: list[str] = []
        try:
            hp = Honeypot().start()
            honeypot_url = hp.url

            for surface in spec.surfaces:
                for attempt in self._attempts_for_surface(run_id, surface, agent_ref, seed):
                    attempts.append(attempt)
                    exec_log = self._run_agent(
                        agent_entry, attempt, surface, honeypot_url, is_regression
                    )
                    syscalls.extend(exec_log)

            contained = self._escape_probe()
            hits = list(hp.hits)
        finally:
            if hp is not None:
                hp.stop()

        return ExecutionTrace(
            run_id=run_id,
            attempts=attempts,
            honeypot_hits=hits,
            syscalls=syscalls,
            escape_probe_contained=contained,
        )

    # -- helpers --------------------------------------------------------------
    def _attempts_for_surface(
        self, run_id: str, surface: Surface, agent_ref: str, seed: int
    ) -> list[AttackAttempt]:
        out: list[AttackAttempt] = []
        for module_id in surface.attack_modules:
            module = get_module(module_id)
            if module is None or not module.applies_to(surface):
                continue
            ctx = AttackContext(
                run_id=run_id, surface=surface, agent_ref=agent_ref, seed=seed
            )
            attempt = module.attack(ctx)
            attempt.threat_ref = attempt.threat_ref or surface.threat_ref
            out.append(attempt)
        return out

    def _run_agent(
        self,
        agent_entry: Path,
        attempt: AttackAttempt,
        surface: Surface,
        honeypot_url: str,
        is_regression: bool,
    ) -> list[str]:
        """Lanza el agente objetivo con el payload. Devuelve un log tosco (proto-syscalls)."""
        env = self._sandbox_env(surface, honeypot_url, is_regression)
        with tempfile.TemporaryDirectory(prefix="aeg-sbx-") as ephemeral_cwd:
            self._materialize_artifacts(attempt, Path(ephemeral_cwd), env)
            try:
                proc = subprocess.run(
                    [sys.executable, str(agent_entry), "--message", attempt.payload],
                    cwd=ephemeral_cwd,
                    env=env,
                    capture_output=True,
                    text=True,
                    timeout=self._timeout_s(surface),
                )
            except subprocess.TimeoutExpired:
                return [f"timeout:{attempt.module_id}"]
            return [
                f"exec:{attempt.module_id}",
                f"agent_rc:{proc.returncode}",
                *(f"agent_out:{line}" for line in proc.stdout.splitlines() if line.strip()),
            ]

    def _sandbox_env(
        self, surface: Surface, honeypot_url: str, is_regression: bool
    ) -> dict[str, str]:
        env: dict[str, str] = {
            k: os.environ[k] for k in _ENV_PASSTHROUGH if k in os.environ
        }
        env["HONEYPOT_URL"] = honeypot_url
        # Planta cada canary declarado en la superficie (env:NOMBRE=valor).
        for c in surface.canaries:
            if c.plant_at.startswith("env:"):
                env[c.plant_at.split(":", 1)[1]] = c.value
        if is_regression:
            env["AEG_SANITIZE"] = "1"  # stand-in del enforcement de D5 (regresión T2)
        return env

    def _materialize_artifacts(
        self, attempt: AttackAttempt, cwd: Path, env: dict[str, str]
    ) -> None:
        """Escribe el artefacto envenenado (indirect_injection) en el cwd efímero."""
        if not attempt.artifact_path:
            return
        dest = cwd / Path(attempt.artifact_path).name
        content = attempt.payload.replace("{HONEYPOT_URL}", env.get("HONEYPOT_URL", ""))
        dest.write_text(content, encoding="utf-8")

    def _escape_probe(self) -> bool:
        """Intenta un egress externo real. `True` = el sandbox contuvo la salida.

        En subprocess (sin aislamiento de red) esto suele ser `False` si hay internet:
        es la señal honesta de que subprocess es aislamiento medio y prod debería usar Docker.
        """
        host, port = self._escape_target
        try:
            with socket.create_connection((host, port), timeout=self._escape_timeout_s):
                return False  # logró salir -> NO contenido
        except OSError:
            return True  # no pudo salir -> contenido

    def _timeout_s(self, surface: Surface) -> float:  # noqa: ARG002 (por superficie a futuro)
        return 15.0

    def _resolve_entrypoint(self, agent_ref: str) -> Path:
        """Resuelve el script del agente objetivo desde agent_ref (repo_path)."""
        candidates = []
        p = Path(agent_ref)
        if p.is_file():
            return p.resolve()
        # dir del agente -> src/agent.py
        for base in (p, Path.cwd() / agent_ref, _REPO_ROOT / agent_ref, _D3_FIXTURE_AGENT):
            candidates.append(base / "src" / "agent.py")
        for c in candidates:
            if c.is_file():
                return c.resolve()
        raise FileNotFoundError(
            f"No encontré el entrypoint del agente objetivo desde agent_ref={agent_ref!r}. "
            f"Busqué: {[str(c) for c in candidates]}"
        )
