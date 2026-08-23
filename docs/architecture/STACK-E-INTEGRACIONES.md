# Stack tecnológico e integraciones

**Dueños:** Helmut (móvil, `:core`, protocolo, voz), Miguel (backend, web, CI).
**Verificado contra el árbol de código el 23 de agosto de 2026.**

[`OVERVIEW.md`](OVERVIEW.md) describe la arquitectura: qué capas hay y por qué. Los
[ADR](ADR/) registran las decisiones. Este documento cubre lo que falta entre ambos: **qué
tecnología concreta está instalada, en qué versión, quién la usa y qué integraciones
externas existen de verdad.**

## Cómo leer las tablas

Cada tecnología lleva un estado, y la distinción no es cosmética:

| Estado | Significa |
|---|---|
| **Cableado** | Declarado en un manifiesto de build *y* usado por código que compila. |
| **Declarado** | Está en el catálogo de versiones o en un ADR, pero ningún módulo lo consume todavía. |
| **Pendiente** | Decidido en documentación, sin línea de código ni dependencia. |

Un documento de stack que no separa esas tres cosas se convierte en una lista de deseos.
Las secciones 1 a 8 describen lo que hay; la sección 9 recoge lo declarado que aún no está
cableado, y la 10 las inconsistencias concretas que conviene resolver.

---

## 1. Vista general del monorepo

| Directorio | Lenguaje | Build | Workflow de CI |
|---|---|---|---|
| `core/` | Kotlin Multiplatform | Gradle (`:core`) | `android-ci.yml`, `arch-guard.yml` |
| `android/` | Kotlin + Jetpack Compose | Gradle (7 módulos) | `android-ci.yml`, `release.yml` |
| `protocol/` | Protocol Buffers + OpenAPI/AsyncAPI | `make proto` (scripts `bash`) | `protocol-ci.yml` |
| `services/` | Python 3.12 | `pip install -e` por servicio | `backend-ci.yml`, `arch-guard.yml` |
| `web/` | TypeScript + React | npm + Vite | `web-ci.yml` |
| `ml/` | Python (entrenamiento PPG) | — | — |
| `tools/voice_pack/` | Python (generador de audio) | `pip install -r` | — |
| `simulators/` | Kotlin (declarado en Gradle) | — | — |
| `infrastructure/` | Docker Compose | `make up` | — |

El nombre del proyecto Gradle es `helius` y el namespace de todos los módulos es
`co.helius`. La marca visible en UI y material de producto es **HELIOS**; según
[`PROJECT_CONTEXT.md`](../../PROJECT_CONTEXT.md) esa diferencia es deliberada y "la marca
visible HELIOS no justifica una migración masiva de namespaces". Ver §10 sobre el uso
mezclado en la documentación.

## 2. Plataforma móvil (Android)

Versiones exactas, todas desde [`gradle/libs.versions.toml`](../../gradle/libs.versions.toml):

| Componente | Versión | Estado |
|---|---|---|
| Kotlin | 2.1.0 | Cableado |
| Android Gradle Plugin | 8.7.0 | Cableado |
| Compose BOM | 2024.12.01 (plugin Compose 1.7.1) | Cableado |
| kotlinx-coroutines | 1.9.0 (`core`, `android`, `test`, `guava`) | Cableado |
| CameraX | 1.5.3 (`core`, `camera2`, `lifecycle`, `view`) | Cableado |
| AndroidX Lifecycle | 2.9.3 · Core KTX 1.16.0 · Activity Compose 1.10.0 | Cableado |
| protobuf-java / protobuf-kotlin | 4.35.1 | Cableado (solo `androidMain`) |
| SQLDelight (+ driver SQLCipher) | 2.0.2 | Declarado |
| LiteRT | 1.0.1 | Declarado |
| Koin | 4.0.0 | Declarado |
| ktlint-gradle · detekt · Konsist | 12.1.1 · 1.23.7 · 0.17.1 | Cableado (CI) |

**Niveles de API y JVM.** `compileSdk = 35`, `targetSdk = 35`, `minSdk = 26` en todos los
módulos. `sourceCompatibility`/`targetCompatibility` están fijados en `VERSION_21`, y
`:android:transport` y `:android:ppg` declaran además `jvmTarget = "21"`. No hay
`jvmToolchain(...)` en ningún módulo, así que la compilación usa el JDK del PATH — lo que
tiene una consecuencia en CI que se detalla en §10.

**Módulos y sus dependencias reales** (no las previstas):

| Módulo Gradle | Depende de | Para qué |
|---|---|---|
| `:android:app` | `:core` + los 6 módulos de abajo, Compose BOM, Material 3, `camera-view` | Shell de UI, `MainActivity`, `EmergencyForegroundService` |
| `:android:transport` | `:core`, `core-ktx`, `coroutines-android` | BLE GATT cliente y servidor (`BleGattClient`, `BleGattServer`) |
| `:android:sensing` | `:core`, `coroutines` | Acelerómetro y giroscopio (`MotionPort`) |
| `:android:ppg` | `:core`, CameraX completo, `coroutines-guava` | Captura de fotopletismografía por cámara + flash |
| `:android:inference` | `:core` | Hoy solo el módulo vacío; el adaptador LiteRT va aquí |
| `:android:storage` | `:core` | Hoy solo el módulo vacío; SQLDelight va aquí |
| `:android:power` | `:core` | Hoy solo el módulo vacío; política de batería |
| `:android:testing` | — | Utilidades de test compartidas |

Los tres módulos vacíos no son un descuido: existen para que la dependencia quede
declarada en `:android:app` desde el principio y el módulo se llene sin renegociar el
grafo. `:android:ppg` documenta en su propio `build.gradle.kts` por qué `libs.litert`
sigue comentado — hasta que exista un modelo aprobado y el adaptador en
`:android:inference`.

**Permisos y capacidades** ([`AndroidManifest.xml`](../../android/app/src/main/AndroidManifest.xml)).
Se piden `BLUETOOTH_SCAN`/`ADVERTISE`/`CONNECT`, `NEARBY_WIFI_DEVICES`, las tres
variantes de ubicación incluida `ACCESS_BACKGROUND_LOCATION`, `CAMERA`, tres
`FOREGROUND_SERVICE*`, `POST_NOTIFICATIONS` y `WAKE_LOCK`. El criterio de `uses-feature`
es consistente y vale explicarlo: **`bluetooth_le` es `required="false"` en la app y
`required="true"` en `:android:transport`**, y acelerómetro, giroscopio y flash también van
en `false`. La razón está escrita en `android/sensing/src/main/AndroidManifest.xml`: hay
equipos de gama baja sin giroscopio, y la ausencia de hardware debe degradar capacidades,
no bloquear la instalación. Wi-Fi Aware y UWB no se declaran: se detectan en tiempo de
ejecución con `PackageManager.hasSystemFeature`.

## 3. Núcleo compartido (`:core`, Kotlin Multiplatform)

Un solo target activo: `androidTarget()`. Los targets de iOS están escritos y comentados
en [`core/build.gradle.kts`](../../core/build.gradle.kts), no borrados, con referencia a la
Fase 2 (ADR-0003).

El reparto entre *source sets* obedece a una restricción técnica concreta:

- `commonMain` solo depende de `kotlinx-coroutines-core`. Ahí viven dominio, puertos, el
  motor DTN y el procesamiento de señal — todo testeable en JVM sin teléfono.
- `androidMain` es el único que depende de protobuf, porque **el runtime de
  `protobuf-java` es JVM-only, no multiplatform**. `gen_kotlin.sh` documenta la
  implicación: en Fase 2, la (de)serialización tendrá que quedar detrás de un puerto
  `expect`/`actual`, o iOS usará SwiftProtobuf.
- `androidUnitTest` corre en la JVM local, sin Robolectric, y cubre `core/crypto` y
  `core/protocol`.

La regla que `arch-guard` verifica: `:core:domain` no importa `android.*`, `androidx.*`,
`io.ktor.*` ni ningún SDK de plataforma.

## 4. Contratos: Protocol Buffers como fuente única

[`protocol/proto/helius/v1/`](../../protocol/proto/helius/v1/) contiene 10 archivos
`.proto`: `common`, `identity`, `incident`, `observation`, `status`, `biomarker`,
`motion`, `bundle`, `found_person`, `inventory`. Junto a ellos hay contratos de API en
[OpenAPI](../../protocol/openapi/helius-api.yaml) y
[AsyncAPI](../../protocol/asyncapi/realtime.yaml), y especificaciones en prosa del formato
de baliza y del paquete PPG v1.

Generación de código, vía `make proto`:

| Destino | Script | Estado |
|---|---|---|
| Kotlin/Java → `core/src/androidMain/{java,kotlin}` | `gen_kotlin.sh` (`protoc --java_out --kotlin_out`, requiere protoc ≥ 26) | Cableado |
| Python → `services/shared/src/api/protocol` | `gen_python.sh` (`protoc --python_out`) | Cableado |
| TypeScript → `web/src/domain/protocol` | `gen_ts.sh` | Pendiente (el script solo imprime el `TODO`) |

La garantía de que el código generado no se desincroniza la da
[`protocol-ci.yml`](../../.github/workflows/protocol-ci.yml): regenera todo, hace
`git diff --exit-code` contra lo commiteado y falla si hay deriva. Además valida
round-trip contra **vectores dorados** versionados en
[`protocol/test-vectors/bundles/`](../../protocol/test-vectors/) — cinco pares `.bin`/`.json`
(`biomarker_pulse`, `motion_purposeful`, `observation_peer`, `raw_chunk`,
`status_trapped`) que se verifican desde Python y desde Kotlin. Es la pieza que impide que
un cambio de esquema rompa en silencio la interoperabilidad entre el teléfono y el backend.

## 5. Backend (Python)

Cuatro paquetes instalables, cada uno con su propio `pyproject.toml`. No es un servicio
monolítico partido en carpetas: `alert_ingestor` y `found_persons` son hexágonos
independientes con dependencias propias.

| Paquete | Python | Dependencias de runtime | Estado |
|---|---|---|---|
| `services/alert_ingestor` | ≥3.12 | `httpx≥0.27`, `websockets≥13` | Cableado, con tests |
| `services/found_persons` | ≥3.12 | `fastapi≥0.115`, `uvicorn[standard]≥0.32`, `pydantic≥2.9`, `cryptography≥43` | Cableado, con tests |
| `services/shared` | ≥3.12 | `fastapi`, `sqlalchemy≥2.0`, `geoalchemy2≥0.15`, `psycopg[binary]≥3.2`, `redis≥5.1`, `protobuf≥5.28`, `pysodium≥0.7`, `numpy≥2.1`, `scipy≥1.14`, `gtsam≥4.2` | No instalable hoy (§10) |
| `services/ppg_model_registry` | ≥3.11,<3.14 | `fastapi`, `uvicorn`, `pydantic` | Esqueleto |

`analytics`, `bundle_ingestor`, `localization` y `notifier` existen como directorios con
README pero sin manifiesto propio; su código previsto vive contra el kernel de
`services/shared`.

Dos decisiones de persistencia que conviene no confundir. El stack de
[`docker-compose.yml`](../../docker-compose.yml) levanta **PostgreSQL 16 + PostGIS 3.4**
para el backend geoespacial, pero `found_persons` **no lo usa**: guarda en SQLite en un
volumen propio (`FOUND_PERSONS_DB=/data/found_persons.db`). Eso es coherente con su diseño
—un servicio que debe poder correr aislado— y es también la razón técnica del pendiente de
inmutabilidad del `audit_log` que documenta [HABEAS-DATA.md](../privacy/HABEAS-DATA.md):
una tabla SQLite la puede editar un administrador.

La criptografía tampoco es una sola: `found_persons` usa `cryptography` (Ed25519, X25519,
ChaCha20-Poly1305) y `services/shared` declara `pysodium` para su `CryptoVerifierPort`.
Dos librerías para primitivas de la misma familia; funciona, pero es una divergencia
deliberada que alguien debería confirmar o unificar.

**Variables de entorno que cambian el comportamiento de seguridad.** `found_persons`
arranca en modo desarrollo si faltan `FOUND_PERSONS_MASTER_KEY` y
`FOUND_PERSONS_SIGNING_SEED`: los tokens de búsqueda serían predecibles y la clave de firma
cambiaría en cada reinicio, invalidando toda cápsula ya emitida. El `docker-compose.yml` lo
dice en un comentario junto a los valores por defecto; no es un descuido, pero sí un
requisito de despliegue que no debe perderse.

## 6. Web (dashboard y landing)

| Dependencia | Versión | Estado |
|---|---|---|
| React + React DOM | ^18.3.1 | Cableado |
| React Router DOM | ^6.28.0 | Cableado |
| TanStack React Query | ^5.62.0 | Cableado |
| MapLibre GL | ^4.7.1 | Cableado |
| TypeScript · Vite · Vitest | ^5.7.2 · ^6.0.3 · ^2.1.8 | Cableado |
| ESLint + typescript-eslint | ^9.16.0 · ^8.18.0 | Cableado |
| deck.gl | — | Declarado en ADR-0005, **no instalado** |

El código fuente actual es deliberadamente pequeño: `App.tsx`, `MapCanvas.tsx`,
`DevicePanel.tsx`, `icons.tsx`, un dominio `geo.ts` con su test, y
`simulation/fixtures.ts`. No consume el protocolo generado, porque ese generador todavía no
existe (§4). `web-ci.yml` corre sobre Node 22 con `npm install && lint && test && build`.

## 7. Integraciones externas

Las cuatro que existen hoy, con su endpoint real:

| Integración | Endpoint / identificador | Protocolo | Estado |
|---|---|---|---|
| **EMSC** (European-Mediterranean Seismological Centre) | `wss://www.seismicportal.eu/standing_order/websocket` | WebSocket, *standing order* en tiempo real | Cableado (`adapters/sources/emsc.py`) |
| **USGS** | `https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary` | HTTP, GeoJSON por *polling* (`ALERT_INGESTOR_POLL_INTERVAL_S`, 15 s por defecto) | Cableado (`adapters/sources/usgs.py`) |
| **SGC** (Servicio Geológico Colombiano) | Sin endpoint fijado a propósito | HTTP | Incompleto por decisión explícita |
| **ElevenLabs** | `https://api.elevenlabs.io/v1/text-to-speech/{voice_id}`, modelo `eleven_multilingual_v2`, voz Daniela (`tOyBjc1xwZQ2wFR7GLaO`) | HTTP, **solo en desarrollo** | Cableado (`tools/voice_pack/`) |

Tres notas que importan más que la tabla.

El adaptador del **SGC** está incompleto de forma razonada, no abandonado. Su docstring
explica que el SGC no publica una API REST pública estable y documentada, solo un visor web
y un RSS cuya URL cambia, y que escribir un parser sobre una URL adivinada habría
significado entregar código que aparenta funcionar sin poder verificarlo. Lo que sí está
resuelto es todo lo demás: el adaptador cumple `AlertSourcePort`, comparte la abstracción
`HttpClient` con USGS, y `parse_sgc_payload()` está aislado como función pura inyectable
para que sea lo único que haya que escribir cuando se confirme el esquema. `FakeSgcSource`
permite ejercitar dedupe cruzado y activación como si ya estuviera integrado. Es la forma
correcta de dejar pendiente una integración de la que se depende para el caso colombiano.

**ElevenLabs no es una dependencia de ejecución.** La app nunca llama a esa API: el
paquete de audio se genera una vez en desarrollo desde
[`tools/voice_pack/catalog.py`](../../tools/voice_pack/catalog.py) —única fuente de verdad
de los guiones— y viaja embebido. `manifest.json` guarda el sha256 de cada archivo para que
la app valide integridad antes de confiar en el paquete. La API key va por
`ELEVENLABS_API_KEY` y no se commitea. El razonamiento completo está en
[`VOICE-GUIDANCE.md`](../voice/VOICE-GUIDANCE.md).

**Despliegue.** No hay ninguno publicado. El `README.md` documenta la restricción real:
Vercel, Render y Netlify solo pueden conectarse a repositorios propios, no al repo de la
organización, de modo que desplegar exige espejar a un repo personal con un `origin` de
doble push. `platanus-hack-project.jsonc` tiene `deploy-url` pendiente por eso.
`release.yml` construye el `bundleRelease` del APK pero la subida a Play Store es un
`TODO`: no hay fastlane ni credenciales de Play Developer API.

## 8. Infraestructura local y guardas automáticas

`make up` levanta ocho contenedores desde [`docker-compose.yml`](../../docker-compose.yml):

| Servicio | Imagen | Puerto |
|---|---|---|
| `postgres` | `postgis/postgis:16-3.4` | 5432 |
| `redis` | `redis:7-alpine` | 6379 |
| `minio` | `minio/minio:latest` | 9000, 9001 |
| `api` | build de `services/shared`, `uvicorn --reload` | 8000 |
| `alert_ingestor` | build propio, `restart: unless-stopped` | — |
| `found_persons` | build propio, `uvicorn` | 8010 |
| `jaeger` | `jaegertracing/all-in-one:latest` | 16686 |
| `grafana` | `grafana/grafana:latest` | 3001 |

Las guardas que corren solas, y qué impide cada una:

| Herramienta | Alcance | Qué bloquea |
|---|---|---|
| ktlint + detekt | Kotlin | Estilo y *code smells* |
| Konsist (`konsistCheck`) | `:core` | Que el dominio importe `android.*`, `androidx.*`, `io.ktor.*` |
| ruff | `services/` | Estilo y errores Python (línea de 100) |
| import-linter | `services/` | **9 contratos** de capas hexagonales |
| pre-commit | repo | Whitespace, YAML, archivos >2000 KB, vocabulario clínico |
| `no-clinical-vocab` | `core/ android/ services/ web/` | `triage`, `diagnóstico`, `signos vitales`, `oximetría` en código |

Los 9 contratos de [`.importlinter`](../../.importlinter) merecen mención porque codifican
la arquitectura en vez de confiar en la revisión humana: el dominio de `found_persons` no
puede importar `fastapi`, `pydantic`, `sqlite3` ni `cryptography`; el de `alert_ingestor`
no puede importar `httpx`, `websockets` ni siquiera `asyncio`; y el contrato 9 obliga a que
la política de divulgación sea el único camino de salida, prohibiendo que `mapping` y
`codec` importen los routers HTTP. El archivo documenta además que
`include_external_packages = True` es obligatorio para que esos contratos se evalúen —sin
él import-linter aborta antes de verificar nada—, y que era un error del esqueleto original.

Los seis workflows: `android-ci` (test, lint, `assembleDebug`), `backend-ci` (ruff,
import-linter, pytest), `web-ci` (lint, test, build), `protocol-ci` (regeneración y
detección de deriva), `arch-guard` (Konsist + import-linter + vocabulario) y `release`
(bundle de APK en ramas `release/*`).

## 9. Declarado y todavía no cableado

Nada de esto está roto; es trabajo identificado y no empezado. Se lista aquí para que
nadie lea la tabla de tecnologías del `OVERVIEW.md` y asuma que ya funciona.

| Tecnología | Dónde está declarada | Qué falta |
|---|---|---|
| SQLDelight + SQLCipher | Catálogo de versiones; `OVERVIEW.md` §2; mencionada en `DataPorts.kt` | Dependencia y esquema en `:android:storage`; hoy la persistencia real es `InMemoryBundleStore` |
| LiteRT | Catálogo; comentada en `android/ppg/build.gradle.kts` | Un modelo aprobado y el adaptador en `:android:inference` (ver `SignalModelRunner.kt`) |
| Koin (o Hilt) | Catálogo; `HELIUSApp.kt` con `TODO` | La decisión misma: el comentario deja abierto Koin vs Hilt |
| deck.gl | ADR-0005; `OVERVIEW.md` §2 | Instalarlo; hoy el mapa es MapLibre GL a secas |
| OpenTelemetry, Loki, Tempo | `OVERVIEW.md` §2 | Cero código; el compose trae Jaeger y Grafana, sin colector ni Loki ni Tempo |
| Codegen TypeScript | `gen_ts.sh`, `Makefile` | El comando `protoc --ts_proto_out` |
| `simulators/mesh-sim`, `fake-devices` | `settings.gradle.kts` | No tienen `build.gradle.kts`; `make sim` es un `echo` |
| iOS | ADR-0003, `core/build.gradle.kts` | En standby explícito hasta Fase 2 |
| Objetivos de `make` | `bootstrap`, `test`, `lint` | `npm install`/`npm test`/`npm run lint` en `web/` y el venv del resto de `services/` siguen como `TODO(dueño=Miguel)` |

## 10. Inconsistencias detectadas al escribir este documento

Cinco cosas que aparecieron al comparar los manifiestos entre sí. Ninguna es una opinión
de estilo; todas tienen un efecto verificable, y la quinta se reprodujo ejecutándola.

**1. Ningún entorno puede construir el proyecto hoy: el wrapper de Gradle no es
ejecutable, y las versiones de JDK no cuadran por ninguno de los dos lados.** Son tres
problemas encadenados, y los tres se verificaron ejecutando o inspeccionando el índice de
git, no razonando.

*Primero, `gradlew` está commiteado sin bit de ejecución.* `git ls-files -s` lo reporta
como modo `100644`, mientras todos los demás scripts del repo (`scripts/*.sh`,
`protocol/codegen/*.sh`) están correctamente en `100755`. Los cuatro workflows que invocan
`./gradlew` —`android-ci`, `arch-guard`, `protocol-ci` y `release`— fallan en su primer
paso con `Permission denied`, antes de compilar una sola línea. Es el bloqueo más barato de
arreglar y el que más rinde: `git update-index --chmod=+x gradlew`.

*Segundo, el JDK de CI no alcanza para el `sourceCompatibility` declarado.* Todos los
módulos Android fijan `sourceCompatibility`/`targetCompatibility` en `VERSION_21`, y
`:android:transport` y `:android:ppg` declaran además `jvmTarget = "21"`. Ningún módulo
declara `jvmToolchain(...)`, así que Gradle usa el JDK del entorno, y los cuatro workflows
instalan **Temurin 17**. Un JDK 17 no puede compilar con release 21: incluso con el bit de
ejecución corregido, la compilación falla.

*Tercero, el wrapper tampoco tolera un JDK moderno.* El wrapper fija **Gradle 8.9**, que no
soporta JDK 26. Ejecutando `sh gradlew :core:testDebugUnitTest` en este entorno, Gradle
aborta con `What went wrong: 26.0.1` tras levantar el daemon. Es decir: **CI tiene un JDK
demasiado viejo para el `sourceCompatibility` del proyecto, y una máquina de desarrollo
actual tiene un JDK demasiado nuevo para el wrapper.** No hay hoy una combinación que
construya.

La salida coherente es fijar la versión en un solo lugar en vez de tres: declarar
`jvmToolchain(21)` en los módulos —así Gradle descarga el JDK correcto y deja de depender
del entorno—, subir el wrapper a una versión de Gradle que soporte JDK 21+ como *runtime*,
y alinear `setup-java` a 21 en los cuatro workflows. Mientras eso no exista, **ningún test
de Kotlin del repo se está ejecutando**, ni en CI ni en local, y eso incluye los vectores
dorados del protocolo del lado Kotlin (§4).

**2. `services/shared` no se instala.** Lo documenta el propio comentario de
`backend-ci.yml`: `gtsam` fija `numpy<2` y el kernel pide `numpy>=2.1`. Por eso el workflow
tolera el fallo con `|| pip install -e services/shared` e instala `alert_ingestor` y
`found_persons` por separado. La consecuencia práctica es que el servicio `api` del
`docker-compose` —que construye desde `services/shared`— no puede levantar hoy. La salida
razonable es aislar `gtsam` en `services/localization` con su propio manifiesto y sacarlo
del kernel, que es justo el TODO que el `pyproject.toml` de `shared` ya anticipa.

**3. La verificación de deriva del protocolo cubre menos de lo que parece.**
`protocol-ci.yml` hace `git diff --exit-code` sobre cuatro rutas, y una de ellas
(`web/src/domain/protocol`) no existe porque `gen_ts.sh` no genera nada. Ese tramo del
chequeo pasa siempre, sin comprobar nada. No es un falso positivo peligroso —el lado
Kotlin y Python sí se verifican de verdad, con vectores dorados— pero conviene saberlo
para no confiar en una cobertura que no está. Vale además revisar que
`protobuf-java 4.35.1` (Kotlin) y `protobuf>=5.28` (Python) sean series compatibles en el
cable: los números mayores de los runtimes de protobuf no se corresponden entre lenguajes,
así que la comprobación real es que los vectores dorados sigan pasando en ambos lados.

**4. `tools/voice_pack/README.md` quedó desactualizado tras la última tanda de guiones.**
Afirma que el catálogo son "3 guiones" y lista tres archivos de salida; `catalog.py` tiene
hoy **seis** `case_id`: `rescuer_instructions`, `trapped_calm`, `trapped_actionable`,
`mobility_check`, `ppg_finger_placement` y `gyro_sos_pattern`. También dice que el `.mp3`
generado no está commiteado, y eso sigue siendo cierto —de `assets/voice/` solo están
versionados `README.md` y `manifest.json`, mientras los seis `.mp3` viven únicamente en
disco—, pero la frase se lee como si la decisión estuviera pendiente cuando ya se tomó.

**5. La guarda de vocabulario clínico falla hoy, y bloquea cualquier PR.** Esto se
verificó ejecutando el comando exacto de `arch-guard.yml` y el del hook
`no-clinical-vocab` de `.pre-commit-config.yaml`: **ambos devuelven código de salida 1**.
La causa es la lista de excepciones. El comando busca `triage|diagnóstico|signos vitales`
y descarta las coincidencias que contengan `NUNCA`, `nunca` o `prohibid`, pero el código
del proyecto no niega el término con esas palabras — lo niega con "no es":

```
core/.../ppg/PpgPipeline.kt:90   "Patrón inusual repetido; requiere valoración, no es un diagnóstico"
core/.../ppg/Models.kt:59        * o diagnóstico cardíaco a este enum.
android/.../MobileShell.kt:321   "Estimación observacional de una señal; no es un diagnóstico clínico."
web/.../DevicePanel.tsx:18       "No prueban vida ni constituyen un diagnóstico clínico."
```

Son seis líneas en total y **todas son usos correctos**: dicen exactamente lo que el
glosario exige decir. El defecto está en la guarda, no en el código. Es además el peor tipo
de guarda rota, porque falla sobre texto que cumple la regla: el equipo aprende a ignorarla
o a desactivarla, y con eso se pierde la protección real. La corrección es ampliar la
excepción a las formas de negación que el proyecto sí usa (`no es`, `no constituye`, `no
implica`) en vez de exigir el vocabulario del filtro, y dejar el hook y el paso de CI con
la misma lista para que no divergan.

**Nota sobre la marca.** La documentación usa las dos formas: `HELIUS` aparece en 10
archivos (incluido el título de `OVERVIEW.md`) y `HELIOS` en 4 (`README.md`, `DESIGN.md`,
`PROJECT_CONTEXT.md` y `docs/mobile/branch-integration.md`), además de la UI y el
`android:label`. `PROJECT_CONTEXT.md` fija la regla —HELIOS es la marca visible, `co.helius`
el namespace técnico— así que no es un error, pero la prosa debería seguir esa regla de
forma consistente en vez de alternar.
