"""Puertos del hexágono `alert_ingestor` (ADR-0001).

Regla del proyecto: todo puerto nuevo trae interfaz + adaptador real + *fake*
determinista. `HttpClient` y `WebSocketConnector` son deliberadamente más finos
que "usa httpx" o "usa websockets" directamente: permiten inyectar un *fake* que
no toca la red, para que los tests de los adaptadores sean deterministas y
rápidos — la misma razón por la que `found_persons` inyecta `Clock` en vez de
llamar a `time.time()`.

Dueño: Miguel.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import AsyncIterator

from alert_ingestor.domain.models import RawSeismicEvent, SeismicIncident


class HttpClient(ABC):
    """Cliente HTTP mínimo. Adaptadores: `HttpxClient` (real), `FakeHttpClient`."""

    @abstractmethod
    async def get_json(self, url: str) -> dict: ...


class WebSocketConnector(ABC):
    """Conexión persistente a un feed que empuja eventos.

    Adaptadores: `WebsocketsConnector` (real, sobre la librería `websockets`),
    `FakeConnector` (una secuencia fija de mensajes para tests).
    """

    @abstractmethod
    def messages(self) -> AsyncIterator[str]: ...


class AlertSourcePort(ABC):
    """Fuente de eventos sísmicos externos.

    Equivalente en intención a `AlertSourcePort` de
    `services/shared/src/api/application/ports.py`, pero tipado sobre
    `RawSeismicEvent` en vez de `dict` — y declarado aquí, no importado de
    `shared`, porque hoy `pip install -e services/shared` no instala (ver
    `__init__.py` del paquete). Cuando eso se arregle, conviene reconciliar ambos
    en uno solo; hacerlo ahora habría acoplado este servicio a un paquete que ni
    siquiera se puede instalar.
    """

    name: str

    @abstractmethod
    async def poll(self) -> list[RawSeismicEvent]:
        """Eventos nuevos desde la última llamada. Lista vacía si no hay novedad."""


class IncidentRepository(ABC):
    """Dónde persisten los incidentes consolidados. Adaptadores: `InMemory`,
    y en el futuro `PostgisIncidentRepo` de `services/shared` una vez instalable."""

    @abstractmethod
    async def upsert(self, incident: SeismicIncident) -> None: ...

    @abstractmethod
    async def recent(self, *, since_ms: int) -> list[SeismicIncident]: ...


class Clock(ABC):
    """Tiempo inyectable. Igual que en `found_persons` — se duplica a propósito:
    son ~10 líneas, y acoplar dos hexágonos de servicios distintos por un reloj
    saldría más caro que repetirlo."""

    @abstractmethod
    def now_ms(self) -> int: ...


class IdGenerator(ABC):
    """Identificadores de incidente. Opacos: no correlativos."""

    @abstractmethod
    def new_id(self) -> str: ...
