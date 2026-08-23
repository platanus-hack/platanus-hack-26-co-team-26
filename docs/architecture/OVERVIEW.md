# Arquitectura de HELIUS

## 1. Qué es el producto

HELIUS convierte smartphones en nodos oportunistas de evidencia, relevo y
localización cuando un sismo derriba la infraestructura de red.

- **Antes del evento** (Promesa A — Preparación): preserva contexto de ubicación,
  capacidades del dispositivo y planes de encuentro familiares, todo cifrado y
  local. Implementable con APIs existentes.
- **Durante y después de un colapso** (Promesa B — Resiliencia post-colapso):
  intercambia *bundles* de estado mediante comunicaciones device-to-device sin
  Internet (BLE, Wi-Fi Aware, Wi-Fi Direct, Nearby), usando un modelo
  Delay/Disruption Tolerant Networking (DTN) de *store-carry-forward*. Núcleo de
  ingeniería del proyecto.
- **Al recuperar conectividad**, un nodo (rescatista o el propio superviviente)
  sincroniza con la nube, que reconstruye un mapa probabilístico y trazable de
  personas, señales de actividad y ubicación de ayuda.

### Regla de oro

> No prometemos encontrar a nadie. Prometemos que la información que puede
> ayudar a encontrarte no desaparezca cuando desaparece tu infraestructura.

### Restricciones no negociables (ver `docs/glossary.md` para el detalle)

No predecimos terremotos · no hacemos triage médico (el módulo es AIB) · no
medimos SpO2 con validez clínica · no detectamos hemorragias/adrenalina/gravedad
de heridas · no convertimos a un teléfono sin la app en nodo de la malla (salvo
el portal cautivo del rescatista) · no declaramos a nadie fallecido (no existe
`DEAD`/`ALIVE`/`INJURED` en ningún enum) · RSSI no es distancia · no prometemos
cobertura iOS mientras esté en standby (ADR-0002).

### Taxonomía de madurez (obligatoria por feature)

| Etiqueta | Significado |
|---|---|
| `PROVEN` | Funciona con APIs/hardware existentes. |
| `ENGINEERING` | Viable, requiere implementación no trivial. |
| `EXPERIMENTAL` | Requiere validación empírica antes de exponerse. |
| `RESEARCH` | Potencial futuro, fuera del MVP. |
| `UNSUPPORTED` | La plataforma no lo permite. Prohibido prometerlo. |

## 2. Decisiones tecnológicas (ver `docs/architecture/ADR/`)

> Esta tabla registra la **decisión**. Para las versiones exactas instaladas, qué
> módulo consume cada dependencia y qué sigue declarado pero sin cablear, ver
> [STACK-E-INTEGRACIONES.md](STACK-E-INTEGRACIONES.md).

| Componente | Tecnología | ADR |
|---|---|---|
| App móvil | Kotlin + Jetpack Compose, API 26 mínimo, objetivo API 35 | ADR-0002 |
| Lógica de dominio y DTN | Kotlin Multiplatform (`commonMain`), un solo target activo (`androidMain`) | ADR-0003 |
| Persistencia local | SQLDelight sobre SQLite con SQLCipher | — |
| Inferencia en dispositivo | LiteRT (TensorFlow Lite) con delegado NNAPI/GPU | ADR-0006 |
| Backend | Python 3.12 + FastAPI, hexagonal | — |
| Base de datos | PostgreSQL 16 + PostGIS | — |
| Web (landing + dashboard) | TypeScript + React + Vite, MapLibre GL + deck.gl | ADR-0005 |
| Contratos | Protocol Buffers, fuente única, codegen Kotlin/Python/TypeScript | ADR-0004 |
| Observabilidad | OpenTelemetry → Grafana / Loki / Tempo | — |

## 3. Vista de contexto

```
FUENTES DE EVENTO SÍSMICO (SGC · CAP feeds · USGS · manual)
        │ Internet
        ▼
HELIUS CLOUD (FastAPI, hexagonal)
  alert-ingestor · bundle-ingestor · localization · notifier · analytics
  PostgreSQL+PostGIS · Redis · S3
        │
   ┌────┼────────────┐
   ▼    ▼             ▼
App Android   Dashboard      Landing público
(Kotlin+Compose) (React+deck.gl)
   │
   │  ═══════════ SIN INTERNET ═══════════
   ▼
ADAPTIVE TRANSPORT LAYER (androidMain)
  BLE · Wi-Fi Aware · Wi-Fi Direct · Nearby · UWB
   │
Survivor Node ──store-carry-forward──▶ Relay Node
   │
   ▼
Responder Gateway (teléfono de rescate) ──al recuperar red──▶ HELIUS Cloud
```

### Los cinco flujos que definen el sistema

1. **Preparación** (pre-evento): contexto local cifrado, puntos de encuentro, contactos, capacidades del dispositivo.
2. **Activación**: fuente sísmica → normalización CAP → decisión de activación → notificación → cambio de modo de energía.
3. **Evidencia**: sensores + interacción del usuario → `EmergencyStatus` → bundle firmado → `BundleStore` local.
4. **DTN**: descubrimiento → handshake → intercambio de inventarios (Bloom filter) → transferencia priorizada → ACK.
5. **Reconstrucción**: gateway → cloud → grafo de encuentros + observaciones RF → localización probabilística → vistas (pública / familiar / respondiente).

## 4. Arquitectura hexagonal

```
driving          APPLICATION            driven
adapters   ──▶  (casos de uso/orquestación)  ──▶  adapters
Compose          │                       BLE
REST             │      DOMAIN           SQLDelight
WS               │  entidades · VOs      Postgres
CLI              │  políticas·invariantes LiteRT
                 │  SIN framework, SIN Android   S3
```

- Los adaptadores dependen hacia adentro, nunca al revés.
- Todo puerto tiene al menos **dos** implementaciones: la real y una *fake* determinista para tests.
- En Kotlin: `expect`/`actual` es el patrón de puertos cuando la diferencia es de
  plataforma (aleatoriedad segura, reloj monótono, almacén de claves) — la lógica
  de dominio usa interfaces normales + inyección.
- Verificado en CI: `:core:domain` no importa `android.*`/`androidx.*`/`io.ktor.*`
  (Konsist en Kotlin, `import-linter` en Python).

Puertos completos: `core/src/commonMain/kotlin/co/helius/core/application/ports/`
(app) y `services/shared/src/api/application/ports.py` (backend).

## 5. Contratos del protocolo (resumen — ver `protocol/docs/PROTOCOL.md`)

- **Descubrimiento (BLE advertising):** binario compacto ≤26 B, ver `protocol/beacon/BEACON_FORMAT.md`.
- **Bundles:** Protocol Buffers (proto3). CBOR permitido solo para `raw` tier-2.
- **Tiers:** T0 (40–120 B, siempre) → T1 (1–20 KB, enlace ≥3 s) → T2 (0.1–10 MB, solo Wi-Fi Aware/Direct/Internet), orden estricto con interrupción segura.
- **Integridad:** `serialize → AEAD encrypt → chunk → FEC/interleave → transport` en emisión; `deinterleave/FEC → reassemble → hash/manifest → AEAD verify → parse` en recepción. Un bundle solo pasa a `VERIFIED` tras esa cadena completa — ver el estado del arte de comunicaciones en el `README.md` raíz.

## 6. Capa de transporte adaptativa (Android)

Cascada de decisión: BLE siempre encendido (denominador común) → escala a Wi-Fi
Aware (NAN, datapath alto throughput) → Wi-Fi Direct (grupo P2P) → Nearby
Connections (abstrae BT+Wi-Fi) → UWB (solo *ranging*, corta distancia) → acústico
(*rendezvous* experimental). Objetivo del ciclo mínimo (solo T0): **TTFC < 4 s**.

Ejecución en background por modo (Sección 7.3–7.5 del spec de referencia):

| Modo | Advertising | Scan | Notas |
|---|---|---|---|
| READY | apagado/muy bajo | oportunista | WorkManager + geofencing |
| ALERT | inmediato | agresivo 30 s | arranque de `EmergencyForegroundService` |
| TRAPPED | continuo, intervalos largos | ventanas cortas | notificación persistente, UI oscura |
| RESCUER | continuo | continuo | pantalla activa, GNSS alta precisión |

## 7. Motor DTN (`core/dtn`, 100% Kotlin, testeable en JVM sin teléfonos)

`BundleStore` (retención por tier/expiración/prioridad) · `InventoryBloom`
(intercambio de filtros, m≈8192 bits) · `ForwardingScorer` (score ponderado de
severidad/edad/batería/probabilidad de entrega) · `EncounterStateMachine`
(advertise→handshake→inventario→transferencia→ACK) · `PriorityQueue`
(anti-flooding, *max_copies* decreciente) · `DyingGasp` (volcado final a <5%
batería). Sin reloj global: causalidad reconstruida vía grafo de encuentros.

## 8. Radiofrecuencia y localización probabilística

`FSPL(dB) = 32.44 + 20·log10(f_MHz) + 20·log10(d_km)`, calibrado por escenario
con el modelo log-distance (`PL(d) = PL(d0) + 10·n·log10(d/d0) + X_σ`). La
localización es un *factor graph* sobre observaciones RSSI + GNSS del
observador — la salida **siempre** es una zona candidata con radios de confianza
(68%/95%), nunca un punto exacto. Ver el estado del arte completo de RF/FEC/DTN
en el `README.md` raíz.

**Eje vertical (mapa 3D, ADR-0009):** el factor graph se extiende con un tercer
eje —piso/profundidad— alimentado *solo* por fuentes que aportan información
vertical real: elevación UWB, diferencial de barómetro (calibrado por
edificio) y GNSS como *prior* débil. Nunca se infiere profundidad a partir de
RSSI puro. `GeoPoint` lleva `altitude_m`/`altitude_source`;
`PeerObservation` lleva los campos crudos de UWB/barómetro
(`protocol/proto/helius/v1/status.proto`, `observation.proto`). La salida
mantiene el mismo espíritu que en 2D: zona candidata + piso estimado, ambos con
incertidumbre explícita — nunca "profundidad exacta".

## 9. Motor de evidencia de actividad (Evidence of Life / Activity Engine)

Pipeline de acelerómetro (50–100 Hz en ráfagas) → magnitud → remoción de gravedad
→ ventanas de 2 s → features (RMS, energía, ZCR, entropía espectral) →
clasificador ligero → `purposeful_motion_confidence [0,1]`. Estados permitidos:
`RESPONSIVE, RECENT_INTERACTION, PURPOSEFUL_MOTION, MOTION_DETECTED,
PULSE_SIGNAL_DETECTED, NO_RECENT_EVIDENCE, UNKNOWN`. Prohibidos:
`DEAD, ALIVE, INJURED`.

## 10. Módulo AIB — Análisis e Interpretación de Biomarcadores

Ver el estado del arte completo de PPG con cámara y fusión con EMG en el
`README.md` raíz. Resumen de postura por elemento:

| Nivel | Elemento | Postura |
|---|---|---|
| Muy defendible | forma de onda, presencia de pulso, frecuencia de pulso, SQI | Se implementa y se valida. |
| Experimental | características derivadas, variabilidad aproximada | Solo modo investigación, marcado en UI. |
| Problemático | SpO2 desde cámara estándar | `RESEARCH`. Nunca visible como número clínico. |
| No defendible | hemorragia, adrenalina, gravedad de heridas | Prohibido. |

División clave: la extracción de señal 1D vive en `:android:ppg` (nativo,
CameraX); todo el DSP posterior es Kotlin puro en `core/signal`, testeable con
grabaciones sin ningún teléfono. Duración mínima de sesión utilizable: 15 s
(objetivo 20–30 s). `HeuristicFallback` (FFT + picos) siempre disponible: el
pipeline debe funcionar sin ML.

## 11. Backend (Python + FastAPI, hexagonal)

Servicios: `api` (REST/WS, auth por rol) · `alert_ingestor` (SGC/CAP/USGS →
evento interno) · `bundle_ingestor` (verificación de firmas, dedupe,
causalidad) · `localization` (factor graph, heatmaps) · `notifier` (FCM) ·
`analytics`. PostgreSQL+PostGIS con índices GIST en toda columna `geography`,
particionado de `bundles`/`peer_observations` por `incident_id`. Regla: todo
endpoint que devuelva PII escribe en `audit_log` **antes** de responder.

## 12. Web: landing + dashboard

Tres vistas con tres niveles de datos — ver ADR-0007 y `web/README.md`. Capas
deck.gl: `ScatterplotLayer` (nodos), `HeatmapLayer`/`ContourLayer`
(verosimilitud, con corte por piso cuando hay dato vertical — ADR-0009),
`ArcLayer` (grafo de encuentros), `TripsLayer` (recorrido de rescatistas),
`PolygonLayer` (zonas).

**Identidad por vista (ADR-0008):** `/mapa` nunca muestra nombre. `/familia`
puede mostrar el nombre real si el usuario lo autorizó en su
`EmergencyDataPolicy` y el vínculo está consentido — el backend le entrega solo
el `EncryptedIdentityProfile` cifrado para la clave de ese familiar. `/ops`
recibe, análogamente, solo lo que la política autorizó para la autoridad de
rescate — no necesariamente lo mismo que ve la familia.

## 13. Seguridad y modelo de amenazas

Ver `docs/security/THREAT-MODEL.md`.

## 14. Modos degradados

Ningún escenario (sin GNSS, sin Internet, sin Wi-Fi, solo Bluetooth, sin radios,
fabricante mata el servicio, batería crítica) es un único punto de fallo — cada
uno tiene un comportamiento definido. La arquitectura trata
`víctima→nube` y `víctima→relay→relay→rescatista→nube` como **el mismo objeto**,
con distinta latencia y metadatos.

## 15. Validación, métricas y simulación

Ver `docs/validation/VALIDATION.md`.
