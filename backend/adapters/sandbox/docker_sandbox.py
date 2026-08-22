"""DockerSandbox — aislamiento fuerte (network_disabled + fs efímero). Mismo SandboxPort.

Adaptador para el venue cuando haya Docker. Estructura la ejecución igual que
SubprocessSandbox pero dentro de un contenedor con `network_disabled=True` (deny-all real)
y un honeypot en una red interna Docker. Si `docker` no está disponible, `run` lo dice
claro y sugiere el fallback (SubprocessSandbox) — que es el puerto intercambiable del pitch.

MVP: stub honesto. La lógica de ataques/canary/oráculo es idéntica a SubprocessSandbox
(se compartirá al implementar el contenedor); no se finge que corre si Docker no está.
"""

from __future__ import annotations

from contracts import HarnessSpec
from domain.types import ExecutionTrace


class DockerSandbox:
    def __init__(self, image: str = "python:3.12-slim") -> None:
        self.image = image
        self._client = None

    def _ensure_client(self):
        if self._client is not None:
            return self._client
        try:
            import docker  # type: ignore
        except ImportError as e:  # pragma: no cover
            raise RuntimeError(
                "DockerSandbox requiere el SDK `docker` y un daemon corriendo. "
                "En dev sin Docker usa SubprocessSandbox (mismo SandboxPort)."
            ) from e
        try:
            self._client = docker.from_env()
            self._client.ping()
        except Exception as e:  # pragma: no cover
            raise RuntimeError(
                "No hay daemon Docker accesible. Usa SubprocessSandbox como fallback."
            ) from e
        return self._client

    def run(self, agent_ref: str, spec: HarnessSpec) -> ExecutionTrace:  # noqa: ARG002
        self._ensure_client()
        # TODO(D3, venue): construir imagen del target-agent, correr con network_disabled=True,
        # montar honeypot en red interna, plantar canary, recolectar hits, escape_probe real
        # (contained=True esperado con network_disabled). Reusa la lógica de SubprocessSandbox.
        raise NotImplementedError(
            "DockerSandbox pendiente para el venue. Aislamiento fuerte con network_disabled. "
            "En dev el skeleton corre con SubprocessSandbox."
        )
