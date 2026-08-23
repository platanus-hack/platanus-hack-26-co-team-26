"""Servicio Geológico Colombiano — fuente oficial para sismos en Colombia.

**Estado: incompleto a propósito.** A diferencia de EMSC y USGS, el SGC no
publica una API REST pública estable y documentada — solo un visor web y un RSS
cuya URL exacta cambia con el tiempo. No hay suficiente certeza sobre el
endpoint vigente ni sobre la forma de su respuesta como para escribir un parser
y afirmar que funciona; hacerlo habría significado adivinar una URL y entregar
código que aparenta funcionar sin haber podido verificarlo.

Lo que SÍ se entrega, listo para conectar en cuanto alguien confirme el
endpoint real:

- El adaptador cumple `AlertSourcePort` y usa la misma abstracción `HttpClient`
  que USGS, así que integrarlo al resto del pipeline (dedupe, activación) no
  requiere tocar nada más.
- `parse_sgc_payload()` está aislado como función pura e inyectable
  (`parser` en el constructor) para que, una vez conocida la forma real de la
  respuesta, sea lo único que haya que escribir — sin tocar la obtención HTTP.
- `FakeSgcSource` permite probar el resto del pipeline (dedupe cruzado,
  corroboración, activación) como si el SGC ya estuviera integrado.

Dueño: Miguel. **TODO(dueño=Miguel): confirmar con el SGC (o con su equipo de
datos abiertos) el endpoint y el esquema vigentes antes de desplegar esto.**
"""

from __future__ import annotations

from collections.abc import Callable

from alert_ingestor.application.ports import AlertSourcePort, Clock, HttpClient
from alert_ingestor.domain.models import RawSeismicEvent

#: Firma que debe cumplir el parser una vez se conozca el formato real del SGC.
SgcParser = Callable[[dict, int], list[RawSeismicEvent]]


class SgcFeedSource(AlertSourcePort):
    """Adaptador real, con la obtención HTTP resuelta y el parseo pendiente.

    `base_url` es obligatorio — a propósito no hay un valor por defecto. Un
    endpoint adivinado que falle en silencio (o, peor, que responda 200 con una
    página HTML que no es la esperada) sería peor que no tener el adaptador.
    """

    name = "sgc"

    def __init__(
        self,
        http: HttpClient,
        clock: Clock,
        *,
        base_url: str,
        parser: SgcParser | None = None,
    ) -> None:
        self._http = http
        self._clock = clock
        self._base_url = base_url
        self._parser = parser or _unconfirmed_parser

    async def poll(self) -> list[RawSeismicEvent]:
        body = await self._http.get_json(self._base_url)
        return self._parser(body, self._clock.now_ms())


def _unconfirmed_parser(_body: dict, _received_at: int) -> list[RawSeismicEvent]:
    raise NotImplementedError(
        "SgcFeedSource no tiene parser: confirme el formato real del feed del SGC "
        "y provea `parser=` al construirlo. No se adivinó un esquema para evitar "
        "entregar un adaptador que aparenta funcionar sin haberlo podido probar."
    )


class FakeSgcSource(AlertSourcePort):
    """*Fake* para probar el resto del pipeline como si el SGC ya estuviera
    integrado. No hace red ni depende de `base_url`."""

    name = "sgc"

    def __init__(self, batches: list[list[RawSeismicEvent]] | None = None) -> None:
        self._batches = batches or []

    def queue(self, events: list[RawSeismicEvent]) -> None:
        self._batches.append(events)

    async def poll(self) -> list[RawSeismicEvent]:
        if not self._batches:
            return []
        return self._batches.pop(0)
