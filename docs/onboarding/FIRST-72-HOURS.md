# Primeras 72 horas del equipo

Objetivo: demostrar el **Slice 0** (el corazón) en video antes de la hora 72 —
ver `docs/roadmap/VERTICAL-SLICES.md`. No se empieza por PPG, ni por ML, ni por
UI bonita.

> [!IMPORTANT]
> `core/dtn`, `core/crypto`, `android/transport` y `core/protocol/BundleWireCodec.kt`
> ya tienen implementación real (no `TODO`), pero **nunca se compilaron** — se
> escribieron sin JDK/Android SDK disponible. La tarea de la hora 0–4 de
> "monorepo generado, `./gradlew build` verde" no es un formalismo: es
> literalmente la primera vez que este código pasa por un compilador. Léanse
> `docs/validation/PHONE-READINESS.md` antes de tocar `android/transport` —
> ahí está la lista de bugs ya encontrados por revisión manual y los que
> probablemente aparezcan recién al compilar/correr en dispositivo.

| Hora | Quién | Entregable |
|---|---|---|
| 0–4 | Todos | Monorepo generado, `./gradlew build` verde, `make up` funciona. |
| 0–8 | Helmut | `.proto` congelados v0.1 + vectores dorados + codegen Kotlin/Python. |
| 4–24 | Helmut | BLE advertising + scan entre dos Android, RSSI registrado, beacon de 26 bytes. |
| 4–24 | Laura + Jorge | App corriendo, UI de emergencia en Compose, DI y fakes cableados. |
| 4–24 | Alex | Protocolo de grabación de dataset + primeras 20 sesiones + DSP base en `core/signal`. |
| 4–24 | Miguel | Dashboard React con datos falsos vía WebSocket + `mesh_sim` v0. |
| 24–48 | Helmut | Bundle firmado A→B en modo avión, verificado en backend (Miguel). |
| 24–48 | Helmut | Escenario DTN A→B→C→R pasando en JVM con `LoopbackFake`. |
| 48–72 | Todos | **Slice 0 completo demostrado en vídeo.** |

**Documento vivo.** Cualquier cambio a las restricciones no negociables (§1.3 del
`README.md` raíz), a la pureza de `commonMain`, al protocolo, o a los niveles de
exposición de datos del dashboard (§13.1) requiere un ADR aprobado.
