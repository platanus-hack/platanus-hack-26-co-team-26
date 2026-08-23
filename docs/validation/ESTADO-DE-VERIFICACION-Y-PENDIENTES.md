# Estado de verificación y pendientes — 23 de agosto de 2026

Este documento dice **qué se ejecutó de verdad y qué no**, para que nadie asuma que
algo funciona porque está escrito. Es el reporte de pendientes de la tanda de
arreglos de build, BLE y nivel de API.

**Dueño de este documento:** Helmut. **Ejecutor de la parte pendiente:** el equipo de
Laura (su PC tiene el hardware para correr emuladores y dispositivos reales).

---

## 1. Lo que quedó verificado por ejecución

Se montó el toolchain que faltaba (ver §3) y se corrió de verdad:

| Comprobación | Resultado | Detalle |
|---|---|---|
| `./gradlew clean build` (Kotlin, antes del merge con `develop` de Laura) | **PASA** | 62 tests, lint de los 8 módulos |
| `./gradlew :android:app:assembleDebug` | **PASA** | APK de 14 MB generado |
| `ruff check services/alert_ingestor` y `services/found_persons` | **PASA** | "All checks passed" |
| `pytest services/alert_ingestor` | **PASA** | 47 tests |
| `pytest services/found_persons` | **PASA** | 95 tests |
| `npm run lint` / `npm test` / `npm run build` en `web/` | **PASA** | 2 tests, build de 969 kB |

Bugs reales encontrados y corregidos por esa ejecución (ninguno era teórico —cada uno
rompía la compilación, un test o el runtime en dispositivo):

1. **`BundleWireCodec` no compilaba.** Dentro de `apply {}` el receptor es el *Builder*
   de protobuf, que declara campos con el mismo nombre que el dominio; `observerGeo`
   resolvía al del builder. Además de romper la compilación, los campos primitivos
   (`altitudeM`, `observedSkewMs`, `uwb*`) se serializaban como `0.0` en silencio.
   *Nota: Laura resolvió lo mismo en paralelo en el commit `2a69b5f` hoisteando locales;
   se conservó su versión y se descartó la duplicada.*
2. **`raw_chunk` perdía 6 bytes en el round-trip** (`BundleGoldenVectorTest`): el codec
   descartaba `tier` y `chunk_count`, así que un receptor no podía saber cuántos chunks
   esperar. *También resuelto por Laura en paralelo; se conservó su versión.*
3. **`AltitudeFusionTest` tenía dos tests contradictorios.** Uno esperaba piso `0` con
   incertidumbre de 3 m sobre pisos de 3 m; el otro esperaba `null` para el mismo caso.
   La regla de ADR-0009 (no reportar piso si la incertidumbre supera medio piso) dice
   que el segundo es el correcto; se corrigió el primero.
4. **X25519/XDH no existen antes de API 33** (`core/crypto/Identity.kt`). `minSdk` es 26,
   así que el handshake cifrado reventaba con `NoClassDefFoundError` en cualquier equipo
   con Android 12 o anterior. Ahora hay `X25519Handshake.isSupported()` (sondea el
   proveedor JCA, correcto también en la JVM de test) y un error accionable.
5. **Ubicación rota en Android 8–10.** `AndroidLocationSource` usaba
   `LocationManager#getCurrentLocation` (API 30) y `Context#mainExecutor` (API 28) sin
   guarda. Sustituidos por `LocationManagerCompat` y `ContextCompat`.
6. **PPG roto en Android 8.** `CameraPpgCaptureSource` usaba `Context#mainExecutor`
   (API 28) dos veces. Sustituido por `ContextCompat.getMainExecutor`.
7. **`:android:ppg:lintDebug` fallaba** por `UnsafeOptInUsageError`: el `@OptIn` de
   Kotlin no lo reconoce el lint de AGP. Se extrajo `lockAutoExposure()` con las dos
   anotaciones (`kotlin.OptIn` para el compilador, `androidx.annotation.OptIn` para lint).
8. **`gradlew` estaba commiteado sin bit de ejecución** (`100644`). Los cuatro workflows
   que invocan `./gradlew` fallaban con `Permission denied` antes de compilar nada.
9. **18 `MissingPermission` en `:android:transport`.** Resueltos declarando
   `@RequiresPermission` en la superficie real (no con `@SuppressLint`), más una guarda
   de permisos de verdad en `BlePermissions`.

## 2. Los arreglos de BLE, y por qué el descubrimiento no funcionaba

Diagnóstico de lo que reportó Laura ("no sincroniza, no pasa nada, y una vez que marca
error siempre marca error"). Los tres primeros son bugs de código ya corregidos:

1. **El filtro de escaneo no podía coincidir con el anuncio, nunca.** El anuncio pone el
   beacon en *service data* (AD type 0x16) y a propósito no incluye una lista de service
   UUID, por presupuesto de 31 bytes. Pero el scan filtraba con
   `ScanFilter.setServiceUuid(...)`, que compara contra `ScanRecord.getServiceUuids()` —
   vacío cuando solo hay service data. Resultado: escaneo activo, cero resultados, y
   **ningún error**. Corregido a `setServiceData(SERVICE_UUID, ByteArray(0), ByteArray(0))`.
2. **Un fallo de escaneo era permanente.** `onScanFailed` hacía `close(excepción)` sobre
   un `callbackFlow`, y un flow cerrado no se reabre: el primer error dejaba el
   descubrimiento muerto hasta reiniciar el proceso. Ahora hay reintento con backoff, y
   el caso `SCAN_FAILED_SCANNING_TOO_FREQUENTLY` (el sistema limita a **5 `startScan` por
   cada 30 s**) espera la ventana completa.
3. **Los fallos del radio eran invisibles.** `onStartFailure` del advertising era un
   `TODO` vacío: un teléfono que no anunciaba se veía idéntico a uno que sí. Ahora hay
   `BleRadioEvent` con códigos traducidos a castellano.
4. **`BlePermissions` nuevo** — cubre lo que ningún permiso arregla y que en campo es la
   causa más común de "escanea y no encuentra nada":
   - Los permisos `BLUETOOTH_SCAN`/`ADVERTISE`/`CONNECT` son de *runtime* desde Android
     12 y **la app nunca los pedía** (solo pedía ubicación y cámara).
   - `BLUETOOTH_SCAN` se declara sin `neverForLocation`, así que exige el **interruptor
     de Ubicación del sistema encendido**; apagado, el escaneo devuelve cero resultados
     sin llamar a `onScanFailed`.
   - **Rol periférico**: `FEATURE_BLUETOOTH_LE` solo garantiza escanear.
     `isMultipleAdvertisementSupported` dice si el equipo puede anunciarse. Es la
     hipótesis principal para la **Redmi Pad SE**: si no anuncia, ve a otros pero es
     invisible, y el descubrimiento se ve asimétrico y errático.

> [!IMPORTANT]
> **Lo que la app NO puede hacer, y hay que rediseñar en la UI.** Encender Wi-Fi
> (`setWifiEnabled` es no-op desde Android 10), datos móviles (requiere privilegios de
> operador) o Bluetooth (`BluetoothAdapter.enable()` sin efecto desde Android 13) es
> imposible para una app de terceros. La única vía es detectar qué está apagado y
> llevar al usuario a los paneles del sistema. Y para la malla teléfono-a-teléfono,
> **Wi-Fi y datos no hacen falta**: BLE funciona en modo avión con el Bluetooth
> encendido, que es la tesis del proyecto.

## 3. Cómo reproducir el build (esto no estaba documentado y sin él nada compila)

Ningún entorno del equipo podía construir el proyecto. Hacen falta dos cosas que no
estaban escritas en ninguna parte:

```bash
# 1. JDK 21. Ni 17 (CI) ni 26 (máquina moderna) sirven:
#    - los módulos declaran sourceCompatibility 21, así que 17 no compila;
#    - el wrapper es Gradle 8.9, que no soporta JDK 26 y aborta al levantar el daemon.
export JAVA_HOME=/ruta/a/jdk-21
export PATH="$JAVA_HOME/bin:$PATH"

# 2. Android SDK con platform 35 y build-tools 35.0.0
export ANDROID_HOME="$HOME/Android/Sdk"
echo "sdk.dir=$ANDROID_HOME" > local.properties   # local.properties está en .gitignore

./gradlew clean build :android:app:assembleDebug
```

**Pendiente estructural (no lo arreglé para no mezclarlo con los arreglos
funcionales):** fijar la versión en un solo lugar en vez de tres — `jvmToolchain(21)`
en los módulos, subir el wrapper a un Gradle que soporte JDK 21+ como runtime, y
alinear `setup-java` a 21 en `android-ci.yml`, `arch-guard.yml`, `protocol-ci.yml` y
`release.yml`.

## 4. PENDIENTE — no verificado, para ejecutar en el PC de Laura

### 4.1 Build sobre el merge más reciente (prioridad 1)

El build verde de §1 se corrió **antes** de integrar el commit `2a69b5f` de Laura, que
trae 1904 líneas nuevas sin compilar nunca: `MobileShell.kt` (+934),
`NearbyConnectionsTransport.kt` (+318), `OperationalModes.kt` (+111),
`HeliosDesignSystem.kt` (+153), `LocalAccountRepository.kt` y recursos de launcher.
**No se pudo ejecutar el build sobre ese merge por falta de tiempo.**

```bash
./gradlew clean build :android:app:assembleDebug
```

Si falla, los sospechosos por orden de probabilidad son
`NearbyConnectionsTransport.kt` (dependencia nueva `play-services-nearby`, y Nearby
Connections exige sus propios permisos en el manifest) y `MobileShell.kt`.

### 4.2 Prueba de BLE en hardware (prioridad 1)

Nada del transporte se ha ejecutado en radio. Antes de tocar código, **el diagnóstico
de dos minutos**: instalar **nRF Connect** en un equipo y escanear mientras otro tiene
HELIUS abierto. Debe aparecer un anuncio bajo el UUID
`0000f5a5-0000-1000-8000-00805f9b34fb`. Si no aparece, el problema es de advertising,
no de escaneo. nRF Connect también reporta si el equipo soporta el rol periférico —
**ese es el dato que falta de la Redmi Pad SE**.

Después:

```bash
./gradlew :android:transport:connectedDebugAndroidTest   # requiere 2 dispositivos
```

Y en cada equipo, a mano, porque ningún permiso de Android lo cubre y MIUI/HyperOS mata
el proceso sin ello:
- **Autostart**: Ajustes → Apps → Permisos → Autoarranque.
- **Batería sin restricciones**: Ahorro de batería → Sin restricciones.
- **Ubicación del sistema encendida**, y el interruptor de "Búsqueda de dispositivos
  Bluetooth" dentro de Ajustes → Ubicación.

**Dato que falta:** el modelo exacto del "Redmi 2022" y la versión de Android de los
tres equipos. El soporte de anuncio BLE varía por chipset, y si alguno está en Android
12 o anterior el handshake X25519 no puede funcionar (§1.4).

### 4.3 Pantallas que son maniquíes, no funcionalidad

Verificado por lectura del código en `MobileShell.kt` **antes** del commit de Laura: de
13 rutas, 5 eran `PlaceholderScreen` (texto estático, cero lógica), incluidas las tres
que más se notan:

| Ruta | Estado en el código anterior |
|---|---|
| `MAP` | Placeholder. **No existe ninguna librería de mapas en Android** — MapLibre solo está en `web/package.json` (JavaScript), pese a que el texto del placeholder dice "Base MapLibre lista" y ADR-0005 la declara. Es la causa de "el mapa no se despliega". |
| `EMERGENCY` | Placeholder — y el botón rojo "NECESITO AYUDA" de la pantalla principal navega ahí. |
| `NEARBY` | Placeholder. `BleTransport` **no se instanciaba en ninguna parte del repo**. |
| `TRUSTED_CONTACTS` | Placeholder |
| `PERMISSIONS` | Placeholder |

`MOTION`, `PPG` y `DIAGNOSTICS` sí eran reales.

**Pendiente:** revisar cuáles de estas cinco resolvió el commit `2a69b5f` (+934 líneas
en `MobileShell.kt`) y cuáles siguen siendo maniquíes. Para el mapa hay que decidir
entre integrar el SDK de MapLibre para Android con un proveedor de teselas, o
implementar la vista de radar local sin red que el propio placeholder menciona — la
segunda es coherente con un sistema que debe funcionar en modo avión.

**`EmergencyForegroundService.onStartCommand` era un `TODO(...)`**, es decir que
arrancar el servicio **crasheaba** con `NotImplementedError`. Verificar si sigue así.

### 4.4 Plugins declarados con `apply false` (post-commit)

`build.gradle.kts` declara ktlint, detekt y konsist con `apply false`, y **ningún módulo
los aplica**. Consecuencia verificada: `./gradlew ktlintCheck` responde
`Task 'ktlintCheck' not found`. Por tanto:

- `android-ci.yml` corre `./gradlew ktlintCheck detekt` → falla por tarea inexistente.
- `arch-guard.yml` corre `./gradlew konsistCheck` → igual.
- `make lint` y `make arch-check` → igual.

Se dejó **sin aplicar a propósito**: aplicarlos ahora habría mezclado un reformateo
masivo con los arreglos funcionales de este commit. Trabajo post-commit:

```kotlin
// en cada módulo, o en un bloque subprojects del root
apply(plugin = "org.jlleitschuh.gradle.ktlint")
apply(plugin = "io.gitlab.arturbosch.detekt")
```

```bash
./gradlew ktlintFormat   # el formateo es mecánico y seguro
./gradlew ktlintCheck detekt konsistCheck   # medir lo que quede y arreglarlo aparte
```

### 4.5 La guarda de vocabulario clínico está rota y bloquea todo PR

Verificado ejecutando el comando exacto de `arch-guard.yml` y el del hook
`no-clinical-vocab`: **ambos devuelven exit 1**. La lista de excepciones espera `nunca`
o `prohibid`, pero el código niega con "no es un diagnóstico". Las seis líneas que
dispara son usos correctos. Ampliar la excepción a `no es`, `no constituye`, `no
implica`, y dejar el hook y el paso de CI con la misma lista.

### 4.6 Otros pendientes ya documentados

`services/shared` no se instala (`gtsam` fija `numpy<2` contra `numpy>=2.1`), la
detección de deriva del protocolo no cubre TypeScript porque `gen_ts.sh` es un `TODO`,
y `tools/voice_pack/README.md` dice "3 guiones" cuando `catalog.py` tiene seis. Detalle
completo en [`docs/architecture/STACK-E-INTEGRACIONES.md`](../architecture/STACK-E-INTEGRACIONES.md) §10.

## 5. Inventario de ramas (para consolidar en `main`)

| Rama | vs `develop` | Qué es | Recomendación |
|---|---|---|---|
| `origin/develop` | — | El monorepo real, 501 archivos | Rama de trabajo |
| `origin/main` | +25 / −27 | **El prototipo Flutter descartado** (`apps/mobile/**`, 31 archivos Dart) + `services/api/`, `fixtures/`, `demo/`, y la metadata del hackathon | Ver abajo |
| `origin/fix/mobile-ui-cleanup` | +1 / −0 | `fix(mobile): navegación, rotación y limpieza de UI en el shell Android`, solo toca `MobileShell.kt` (+85/−26) | Revisar contra el `2a69b5f` de Laura (tocan el mismo archivo) y mergear si no choca |
| `origin/feat/offline-earthquake-detection` | +0 / −12 | Ya está **enteramente contenida** en `develop` | Se puede borrar sin perder nada |
| `origin/backup/pre-reset-main` | +12 / −28 | Respaldo del proyecto anterior de AI Security (PRs #1–#8) | Conservar como respaldo histórico, no mergear |

**Sobre el merge a `main`.** `main` es la **rama por defecto** (`origin/HEAD → main`), o
sea lo que ve un juez al abrir el repo, y hoy muestra el prototipo Dart. El merge en
seco (`git merge-tree`) da **6 conflictos, todos en archivos de raíz y ninguno en
código**: `.gitignore`, `Makefile`, `README.md`, `platanus-hack-project.jsonc`,
`project-description.md`, y `project-logo.png` (borrado en `main`, modificado en
`develop`).

Criterio acordado: **de `main` lo que importa conservar es la documentación**, y se
complementa con la de `develop`; integrar sin romper ni borrar lo que no deba borrarse.
Traducido a acciones concretas:

- **Conservar de `main`:** `docs/API.md`, `docs/ARCHITECTURE.md`, `docs/CORE-5H.md` y el
  PDF del playbook. Conviene moverlos a `docs/legacy/` con una nota de que describen el
  prototipo Dart y no la arquitectura vigente (`docs/architecture/OVERVIEW.md` + los 10
  ADR), para que nadie los lea como actuales.
- **Tomar de `main`:** el `deploy-url` ya resuelto
  (`https://helius-landing-pearl.vercel.app/`) y la decisión de marca (`Helius`).
- **Resolver a favor de `develop`:** `README.md`, `Makefile`, `.gitignore`.
- **Decidir un solo logo:** `main` tiene `project-logo.jpg` (1254×1254) y `develop`
  `project-logo.png` (1000×1000, 74 KB). El `platanus-hack-project.jsonc` pide
  "1000x1000 png, max 500kb", que cumple el PNG y no el JPG. Además el README de `main`
  tiene la línea 3 apuntando a `.png` y la 5 a `.jpg`.
- **`apps/mobile/**` (Dart):** su valor ya fue extraído al Kotlin en el commit
  `7122a60` (MTU negotiation, servidor GATT multi-peer, `sdnnMs`/`pnn50`). No borrarlo
  sin decisión del equipo; si se conserva, dejarlo bajo una ruta explícita de prototipo
  para que no se confunda con código vivo y para que no entre a `backend-ci.yml`, que
  dispara con `paths: services/**` y lintearía `services/api/`.
