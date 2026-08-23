# services/alert_ingestor — fuentes sísmicas externas → evento interno

**Propósito:** consultar EMSC/USGS/SGC, deduplicar el mismo sismo reportado por
varias fuentes con parámetros distintos, y decidir si el evento activa el resto
del sistema (Sección 12.4).

**Dueño:** Miguel.

**Etiqueta de madurez:** `APPLICATION` para EMSC y USGS — implementados, probados
(47 tests) y verificados contra las APIs reales en vivo durante el desarrollo.
`ENGINEERING` para SGC — ver nota más abajo.

---

## Las tres fuentes

| Fuente | Protocolo | Latencia | Estado |
|---|---|---|---|
| **EMSC** | WebSocket push (`wss://www.seismicportal.eu/standing_order/websocket`) | Segundos | Implementado y probado con *fakes*. Conexión verificada en vivo (TCP/TLS OK); no se observó ningún mensaje en ~100 s de escucha en el entorno de desarrollo — sin datos suficientes para confirmar la recepción de eventos reales, ver nota más abajo. |
| **USGS** | REST/GeoJSON (`https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/all_hour.geojson`) | ~1 min | Implementado, probado y **verificado en vivo**: consultado contra el feed real durante el desarrollo, devolvió 6 eventos reales de la última hora. |
| **SGC** | Sin API pública estable confirmada | — | **Deliberadamente incompleto.** Ver `adapters/sources/sgc.py`. |

### Por qué SGC no está completo

El Servicio Geológico Colombiano no publica una API REST documentada y estable
como EMSC o USGS — solo un visor web cuya URL y formato cambian con el tiempo. No
había suficiente certeza como para adivinar un endpoint y un esquema de respuesta
y afirmar que el adaptador funciona: eso habría entregado código que aparenta
funcionar sin haber podido verificarse, potencialmente apuntando a algo roto o
inexistente en producción.

Lo que sí queda resuelto:

- `SgcFeedSource` cumple `AlertSourcePort` y reutiliza `HttpClient`, así que
  integrarlo no requiere tocar el resto del pipeline (dedupe, activación).
- El parseo se inyecta (`parser=`) en vez de estar hardcodeado — confirmar el
  formato real del SGC es lo único que falta.
- `FakeSgcSource` permite probar todo el pipeline (corroboración cruzada,
  activación) como si el SGC ya estuviera integrado.

**TODO(dueño=Miguel): confirmar con el SGC el endpoint y el formato vigentes
antes de desplegar esto en producción.**

### Nota sobre la verificación de EMSC

Durante el desarrollo, la conexión WebSocket a EMSC se estableció correctamente
(handshake TCP/TLS exitoso) pero no llegó ningún mensaje en las ventanas de
prueba (hasta ~100 s). Es un feed de sismicidad global de magnitud ≥1.5 — no
debería estar en silencio tanto tiempo, así que antes de confiar en esto para un
despliegue real conviene una prueba de escucha más larga (10–15 min) desde una
red sin restricciones de egreso, para descartar tanto "fue una ventana
tranquila" como "el endpoint cambió" o "hace falta algo más que un connect
simple". El adaptador implementa el protocolo tal como lo documenta EMSC
(https://www.seismicportal.eu/realtime.html); lo que no se pudo confirmar aquí
es la recepción de tráfico real durante la prueba.

---

## El pipeline

```
EMSC ──┐
USGS ──┼─▶ Deduplicator ──▶ decide_activation ──▶ CycleResult
SGC  ──┘   (mismo sismo,     (umbral individual        (nuevas activaciones,
(fake)      fuentes distintas) o corroborado)           incidentes tocados,
                                                          errores de fuente)
```

- **Deduplicación** (`domain/dedup.py`): dos reportes son "el mismo sismo" si
  están dentro de ±2 min, <200 km y difieren <1.5 en magnitud entre sí — umbrales
  generosos a propósito (`ASSUMED`, ver `docs/validation/`): es preferible
  fusionar de más en el primer minuto que activar tres veces el mismo evento.
  Qué reporte manda (`primary`) se recalcula en **cada** fusión según prioridad
  de fuente (SGC > USGS > EMSC para territorio de interés), no se congela en
  quien llegó primero — así el resultado no depende del orden de llegada.

- **Activación** (`domain/activation.py`): magnitud alta con una sola fuente
  activa; magnitud menor pero confirmada por ≥2 fuentes independientes también
  — una coincidencia entre redes que no comparten estaciones ni algoritmo ya es,
  en sí misma, una señal de confianza. Umbrales configurables vía
  `ActivationPolicy`, `ASSUMED` hasta calibrarse con datos reales.

- **Orquestación** (`application/ingest.py`): un ciclo (`run_cycle()`) consulta
  cada fuente, deduplica, decide activación y devuelve solo las activaciones
  **nuevas** — un incidente ya activado no se vuelve a reportar aunque otra
  fuente lo corrobore en un ciclo posterior.

---

## Arranque

```bash
cd services/alert_ingestor
python3 -m venv .venv && ./.venv/bin/pip install -e ".[dev]"
./.venv/bin/pytest -q                              # 47 tests
python -m alert_ingestor.bootstrap.main            # worker en bucle (EMSC + USGS)
```

Sin superficie HTTP propia: es un worker que alimenta eventos internos, no los
expone (`docs/architecture/OVERVIEW.md` §11). Hoy solo registra por log las
activaciones — cablear `EventBusPort`/`NotificationPort` queda para cuando esos
adaptadores existan en algún servicio del monorepo.

---

## Por qué no importa `services/shared`

`AlertSourcePort` ya está declarado en
`services/shared/src/api/application/ports.py`, y la convención del proyecto es
que los servicios importen ese kernel común. Pero hoy `pip install -e
services/shared` **no instala**: `gtsam` (usado solo por `services/localization`)
está pineado a `numpy<2`, y `services/shared` exige `numpy>=2.1` — un conflicto
irresoluble, preexistente y ajeno a este servicio.

Este hexágono queda autocontenido mientras tanto, con su propio
`AlertSourcePort` tipado sobre `RawSeismicEvent` en vez de `dict`. Cuando el
empaquetado de `shared` se arregle, conviene reconciliar ambos puertos en uno
solo — importar ahora un paquete que ni siquiera instala habría sido peor que
la duplicación temporal.

---

## Estructura

```
src/alert_ingestor/
├── domain/          # Sin frameworks.
│   ├── models.py        RawSeismicEvent, SeismicIncident, ActivationPolicy
│   ├── geo.py            Distancia haversine
│   ├── dedup.py           Deduplicator — ¿mismo sismo, fuentes distintas?
│   └── activation.py      decide_activation()
├── application/
│   ├── ports.py           AlertSourcePort, HttpClient, WebSocketConnector, ...
│   └── ingest.py          AlertIngestionService — orquesta un ciclo
├── adapters/
│   ├── http.py            HttpxClient (real) + FakeHttpClient
│   ├── websocket.py       WebsocketsConnector (real) + FakeConnector
│   ├── sources/
│   │   ├── usgs.py         Implementado y verificado en vivo
│   │   ├── emsc.py         Implementado; ver nota de verificación arriba
│   │   └── sgc.py          Shell honesto + FakeSgcSource
│   └── persistence/memory.py
└── bootstrap/main.py      Cableado + bucle del worker
```

Cada puerto tiene adaptador real y *fake* determinista, como exige
`CONTRIBUTING.md`. Los tests de los adaptadores de fuente usan fixtures con la
forma real de cada API (`tests/conftest.py`), tomada de la documentación pública
de EMSC y USGS.

---

## Qué falta

- [ ] Confirmar endpoint y formato del SGC (bloqueante para esa fuente).
- [ ] Verificar la recepción de tráfico real de EMSC desde una red sin
      restricciones de egreso, con una ventana de escucha más larga.
- [ ] Manejar `action: "delete"` de EMSC como retractación real, no solo
      ignorarla (hoy un falso positivo emsc no se retira si ya generó un incidente).
- [ ] Persistencia real (`IncidentRepository` sobre Postgres) en vez de memoria.
- [ ] Cablear `EventBusPort`/`NotificationPort` una vez existan en algún servicio.
- [ ] Reconciliar este `AlertSourcePort` con el de `services/shared` cuando ese
      paquete vuelva a instalar.
