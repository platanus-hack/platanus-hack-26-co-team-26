"""Conector WebSocket. `WebsocketsConnector` es el real; `FakeConnector` reproduce
una secuencia fija de mensajes para tests deterministas.
"""

from __future__ import annotations

from collections.abc import AsyncIterator

from alert_ingestor.application.ports import WebSocketConnector
from alert_ingestor.domain.errors import SourceUnavailable


class WebsocketsConnector(WebSocketConnector):
    """Adaptador real sobre la librería `websockets`.

    Import perezoso, igual que en `HttpxClient`: el resto del paquete no necesita
    `websockets` instalado para importarse.
    """

    def __init__(self, url: str) -> None:
        self._url = url

    async def messages(self) -> AsyncIterator[str]:
        import websockets
        from websockets.exceptions import WebSocketException

        try:
            async with websockets.connect(self._url) as ws:
                async for message in ws:
                    yield message if isinstance(message, str) else message.decode("utf-8")
        except WebSocketException as exc:
            raise SourceUnavailable(f"{self._url}: {exc}") from exc


class FakeConnector(WebSocketConnector):
    """*Fake* determinista: entrega `messages` en orden y termina.

    Terminar (en vez de bloquear para siempre como un WebSocket real) es
    deliberado: permite que un test haga `await source.run()` sin necesitar
    cancelar una tarea en segundo plano.
    """

    def __init__(self, fixed_messages: list[str]) -> None:
        self._fixed_messages = fixed_messages

    async def messages(self) -> AsyncIterator[str]:
        for message in self._fixed_messages:
            yield message
