"""Cliente HTTP. `HttpxClient` es el real; `FakeHttpClient` sirve respuestas
enlatadas para que los tests de los adaptadores de fuente no toquen la red.
"""

from __future__ import annotations

from alert_ingestor.application.ports import HttpClient
from alert_ingestor.domain.errors import SourceUnavailable


class HttpxClient(HttpClient):
    """Adaptador real sobre `httpx.AsyncClient`.

    Import perezoso de `httpx` dentro del método: así el resto del paquete
    (dominio, aplicación, incluso este módulo) se puede importar sin tener
    `httpx` instalado — solo hace falta para de verdad hacer la petición.
    """

    def __init__(self, timeout_s: float = 10.0) -> None:
        self._timeout_s = timeout_s

    async def get_json(self, url: str) -> dict:
        import httpx

        try:
            async with httpx.AsyncClient(timeout=self._timeout_s) as client:
                response = await client.get(url)
                response.raise_for_status()
                return response.json()
        except httpx.HTTPError as exc:
            raise SourceUnavailable(f"{url}: {exc}") from exc


class FakeHttpClient(HttpClient):
    """*Fake* determinista: devuelve `responses[url]`, en orden si es una lista."""

    def __init__(self, responses: dict[str, dict | list[dict]] | None = None) -> None:
        self._responses = responses or {}
        self._calls: list[str] = []

    def set_response(self, url: str, body: dict) -> None:
        self._responses[url] = body

    def queue_responses(self, url: str, bodies: list[dict]) -> None:
        self._responses[url] = list(bodies)

    async def get_json(self, url: str) -> dict:
        self._calls.append(url)
        body = self._responses.get(url)
        if body is None:
            raise SourceUnavailable(f"sin respuesta programada para {url}")
        if isinstance(body, list):
            if not body:
                raise SourceUnavailable(f"respuestas agotadas para {url}")
            return body.pop(0)
        return body

    @property
    def calls(self) -> list[str]:
        return list(self._calls)
