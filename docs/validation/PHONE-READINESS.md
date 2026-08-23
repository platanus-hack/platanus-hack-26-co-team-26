# Criterio de "listo para teléfono" (transporte, DTN, criptografía)

> [!WARNING]
> **Para quien monte el proyecto en Android Studio: este código nunca se
> compiló ni se ejecutó.** Se escribió en un entorno sin JDK completo (solo
> JRE, sin `javac`) y sin Android SDK — no hay forma de haber corrido
> `./gradlew` aquí. Todo lo de `core/dtn`, `core/crypto`, `android/transport`
> y el puente `core/protocol/BundleWireCodec.kt` está revisado línea por
> línea contra la documentación oficial de las APIs usadas, y con varios
> bugs reales ya encontrados y corregidos (tabla abajo) — pero **el primer
> trabajo de quien lo integre es correr L0 y L1 de esta tabla y arreglar lo
> que el compilador encuentre**, no asumir que ya está probado.

Este documento existe porque escribir código Kotlin correcto por inspección
**no es lo mismo** que saber que corre en un Android real. Aplica a
`core/dtn`, `core/crypto`, `android/transport` y cualquier módulo que toque
radios/hardware.

## Los 4 niveles, en orden — no se salta ninguno

| Nivel | Qué prueba | Herramienta |
|---|---|---|
| L0 — Compila | El código es sintácticamente válido y tipa correctamente | `./gradlew :core:compileDebugKotlinAndroid` |
| L1 — Lógica correcta en JVM | Las reglas de negocio (DTN, cripto, Bloom filter) hacen lo que dicen que hacen | `./gradlew :core:testDebugUnitTest` (sin ningún teléfono) |
| L2 — API de Android se comporta como se espera | Permisos, ciclo de vida de BLE/GATT, tamaños reales de advertising | `./gradlew :android:transport:connectedDebugAndroidTest` en emulador o dispositivo |
| L3 — Funciona entre dos teléfonos reales | El escenario completo (`docs/onboarding/FIRST-72-HOURS.md`: dos Android en modo avión intercambian un bundle T0 en <4 s) | Prueba de campo manual, `docs/validation/VALIDATION.md` |

**Ninguno de los 4 niveles se ha corrido todavía sobre el código de esta etapa.**
Este sandbox de desarrollo no tiene JDK completo (solo JRE, sin `javac`) ni
Android SDK/emulador — nada se compiló ni se ejecutó. Lo que sí se verificó
por ejecución real: los `.proto` con `protoc`, el codegen Python, y el HKDF a
mano contra el vector oficial RFC 5869. Todo el Kotlin (crypto, DTN,
transporte BLE) está escrito con cuidado pero es **L(-1): revisado por
inspección, no ejecutado**.

## Qué debe existir para pasar de "código" a "funcionalidad válida en el teléfono"

### Obligatorio antes de instalar en cualquier dispositivo (incluso de prueba)

- [ ] L0 y L1 en verde en CI (`android-ci.yml` ya está configurado para correrlo — nunca se ha ejecutado contra este código).
- [ ] `BleTransport` probado en `connectedAndroidTest` contra al menos un dispositivo real: advertising visible con un scanner externo (nRF Connect u otra app), tamaño del payload verificado byte a byte (no asumido).
- [ ] Manejo de permisos runtime: hoy `requirePermission()` lanza excepción si falta el permiso — la UI (`android/app`, Laura/Jorge) todavía no pide esos permisos en ningún flujo. Sin eso, `BleTransport` crashea en cuanto se usa.
- [ ] `core/crypto/Identity.kt` corriendo con Android Keystore, no con la clave en heap — hoy `Ed25519Identity.generate()` mantiene la clave privada en memoria del proceso, aceptable para el test de JVM, **no aceptable para producción** (una app maliciosa con el mismo UID o un dump de memoria la expondría).
- [ ] Verificar en la matriz de dispositivos (`docs/validation/VALIDATION.md`) que `Ed25519`/`XDH`/`ChaCha20-Poly1305` existen como proveedor JCA en cada fabricante objetivo, mínimo API 26. Si falta en alguno, sumar BouncyCastle — no lo asumas resuelto.

### Obligatorio antes de una demo con usuarios reales (Slice 0)

- [ ] Transferencia real de bundles sobre la conexión GATT — hoy `connect()` solo entrega el `PeerLink`; no hay servicio/característica GATT que mueva bytes. Sin esto, `EncounterStateMachine.exchange()` (que sí funciona) nunca se dispara con datos reales.
- [ ] UUID de servicio BLE propio registrado (no el de desarrollo que hay ahora).
- [ ] Corrida del escenario A→B→C→R con tres teléfonos físicos, no solo el test en JVM.
- [ ] Medición de batería del ciclo READY/ALERT (`docs/architecture/OVERVIEW.md` § 6) — sin medir, no se sabe si el foreground service sobrevive las horas que promete el spec.

### Nunca debe pasar a producción así esté "verde" en tests

- Cualquier vocabulario clínico prohibido (linter de CI ya lo bloquea, pero revisar igual — ver `docs/glossary.md`).
- Un bundle marcado `VERIFIED` sin haber pasado por `BundleSigner.verify()` real — hoy nada llama a `verify()` en el flujo real todavía, así que ningún bundle debería tratarse como verificado en producción hasta que `bundle_ingestor`/`EncounterStateMachine` lo invoquen.
- Cifrado con la clave por defecto de ejemplo (`ByteArray(32){it.toByte()}` que aparece en los tests) — es intencionalmente insegura, solo para el test.

## Errores reales encontrados y corregidos en esta revisión

| Error | Dónde | Severidad | Corregido |
|---|---|---|---|
| `AdvertiseData` con `addServiceUuid()` **y** `addServiceData()` duplicando el UUID — excede el presupuesto de 31 B de legacy advertising y el beacon (23 B) no cabría | `BleTransport.startAdvertising` | Alta — el advertising fallaría o se truncaría en hardware real | ✅ |
| `onConnectionStateChange`/`onServicesDiscovered` resolvían éxito sin revisar `status` — una conexión GATT fallida podía reportarse como `PeerLink` válido | `BleTransport.connect` | Alta — corrompería el estado de la app (cree que hay enlace cuando no) | ✅ |
| `KeyAgreement.getInstance("X25519")` — nombre de algoritmo no documentado de forma consistente para `KeyAgreement` en JCA; `"XDH"` es el nombre correcto desde JDK 11 | `core/crypto/Identity.kt` | Media — podría lanzar `NoSuchAlgorithmException` en tiempo de ejecución | ✅ |
| Precondición de `PayloadCipher.decrypt` aceptaba payloads sin espacio para el tag Poly1305 (`> 12` en vez de `>= 28`) | `core/crypto/Identity.kt` | Baja — el `Cipher` igual habría fallado, pero con un error menos claro | ✅ |
| `EncounterStateMachine.State` sugiere una máquina de estados completa que no existe — riesgo de que alguien la dé por implementada | `core/dtn/EncounterStateMachine.kt` | Baja (documentación engañosa, no bug de ejecución) | ✅ (comentario explícito) |
| **`SERVICE_UUID` divergía entre el anuncio BLE (`BleTransport`) y el servicio GATT real (`BleGattProfile`)** — un cliente encontraría el beacon por scan pero jamás encontraría el servicio al conectarse, todo el intercambio fallaría en silencio | `BleTransport` / `BleGattProfile` | **Alta** — el sistema completo no funcionaría entre dos teléfonos aunque cada parte compilara bien | ✅ (unificado a una sola constante, `BleTransport.SERVICE_UUID = ParcelUuid(BleGattProfile.SERVICE_UUID)`) |
| `BleGattProfile.SERVICE_UUID` no seguía el patrón exacto de Base UUID de Bluetooth SIG (grupo 2 era `0001`, no `0000`) — Android no lo habría comprimido a 16 bits en el advertising, repitiendo el bug de presupuesto de 31 B ya corregido antes | `BleGattProfile.kt` | Alta | ✅ |
| `onCharacteristicChanged` implementado con la sobrecarga de 3 argumentos (`byte[] value`), que es **API 33+**; con `minSdk 26` ese callback nunca se dispara en versiones anteriores y la recepción de notificaciones (bundles/inventario entrantes) se cuelga en silencio sin ningún error | `BleGattClient.kt` | **Alta** — falla exactamente en el rango de API que el proyecto dice soportar (26 en adelante) | ✅ (cambiado a la sobrecarga de 2 argumentos, compatible con todo el rango) |
| Notificaciones GATT (`notifyCharacteristicChanged`) enviadas en bucle sin esperar `onNotificationSent` entre una y la siguiente — la pila BLE típicamente descarta notificaciones en vuelo que se pisan | `BleGattServer.kt` | Media — pérdida silenciosa de chunks en hardware real, aunque "funcionaría" en cualquier prueba que no sea BLE real | ✅ (pacing con `CompletableDeferred` esperando confirmación por chunk) |

## Qué se completó en esta pasada (transferencia real de bundles)

- `core/protocol/BundleWireCodec.kt` — puente entre el modelo de dominio
  (`core/domain/model/Bundle`) y las clases protobuf generadas. Antes de esto,
  **no existía ninguna forma de convertir un `Bundle` a bytes reales** — cubre
  el payload `Status` completo (el que necesita el Slice 0); `Motion`/
  `Biomarker`/`Observation` lanzan `NotImplementedError` explícito (no
  fallan en silencio) hasta que Alex/Helmut definan esos tipos de dominio.
- `BleGattProfile.kt`, `BleChunking.kt`, `BleGattServer.kt`, `BleGattClient.kt`
  — protocolo GATT completo y simétrico: cada teléfono corre servidor Y
  cliente a la vez, intercambian Bloom filters (chunked) y se empujan
  mutuamente los bundles que al otro le faltan, vía `notify`/`write` con
  reensamblado de chunks.

## Qué sigue sin cubrir

- `gatt.requestMtu()` nunca se llama — el cliente siempre asume el MTU mínimo
  (23 B), lo cual es *correcto pero lento* (más chunks de los necesarios). No
  es un bug, es una optimización pendiente.
- Un solo peer conectado a la vez por `BleGattServer` (el reensamblador no
  distingue por dispositivo) — con más de una conexión GATT simultánea al
  mismo teléfono, los chunks de distintos peers se mezclarían.
- Nada de esto se ha probado contra la matriz de fabricantes
  (`docs/validation/VALIDATION.md`) — ni siquiera contra un único par de
  teléfonos reales.

## Veredicto actual

**No está listo para instalarse en un teléfono real todavía.** El protocolo
GATT de extremo a extremo (Bloom filter + bundles en ambos sentidos) ya está
escrito y con varios bugs reales de compatibilidad (algunos de API level,
otros de presupuesto de advertising) ya encontrados y corregidos por
inspección — pero **ninguno de los 4 niveles L0-L3 se ha ejecutado nunca**.
El siguiente paso obligatorio, sin excepción, es que alguien con Android
Studio corra:

```bash
./gradlew :core:compileDebugKotlinAndroid   # L0
./gradlew :core:testDebugUnitTest            # L1
./gradlew :android:transport:connectedDebugAndroidTest   # L2, con emulador o dispositivo
```

y reporte lo que falle — recién ahí este documento puede actualizarse a
"parcialmente verificado". Avisar al resto del equipo (Laura/Jorge, Alex,
Miguel) apenas L0 esté en verde, porque varias piezas (UI que pide permisos,
`BiomarkerEvidence`/`MotionEvidence` reales, wiring de DI) dependen de que
esto compile primero.
