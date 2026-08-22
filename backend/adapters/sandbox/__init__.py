"""adapters/sandbox/ — C4 (owner D3, Alex).

Executor + Sandbox: levanta el agente objetivo en aislamiento y dispara los ataques del
harness_spec, observando la ExecutionTrace que alimenta al oráculo.

- SubprocessSandbox : backend por defecto en dev (no requiere Docker). Aislamiento medio.
- DockerSandbox     : aislamiento fuerte (network_disabled, fs efímero). Mismo puerto.
- Honeypot          : servidor HTTP interno que registra egress (canary => exploited).
"""

from __future__ import annotations

from adapters.sandbox.docker_sandbox import DockerSandbox
from adapters.sandbox.honeypot import Honeypot
from adapters.sandbox.subprocess_sandbox import SubprocessSandbox

__all__ = ["SubprocessSandbox", "DockerSandbox", "Honeypot"]
