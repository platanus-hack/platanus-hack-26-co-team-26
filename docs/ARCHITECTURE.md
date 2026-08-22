# SismoMesh — Arquitectura inicial (Flutter / Android)

> Documento derivado de `docs/SismoMesh_Hackathon_Execution_Playbook_5_Devs-1.pdf`, adaptado a la
> decisión del equipo de construir la app en **Flutter, ejecutándose sólo en equipos Android**.
> Estado: propuesta para congelar en T0. Cambios al contrato de datos requieren bump de versión.

> [!IMPORTANT]
> **Este documento describe el sistema completo (horizonte 36 h).** Para el arranque real hay un
> corte de alcance vigente en **[`docs/CORE-5H.md`](./CORE-5H.md)**: núcleo entregable en 5 horas.
> Ese documento **revisa cinco ADR de aquí** (transporte, serialización, persistencia, estado,
> infraestructura) por presupuesto de tiempo. Ante conflicto, **manda `CORE-5H.md`** hasta que el
> núcleo esté verde y repetible.

---

## 0. Delta respecto al playbook

El playbook asume dos apps nativas (Kotlin + Swift) y dedica un dev completo (D2) a iOS/CoreBluetooth.
Al pasar a Flutter/Android-only cambian cinco cosas y **se conserva todo lo demás**.

| Tema | Playbook original | Esta arquitectura | Efecto |
|---|---|---|---|
| Clientes móviles | Android nativo + iOS nativo | **Una** app Flutter, un solo binario, tres roles en runtime | Se elimina la clase de riesgo "interop cross-platform", que era el riesgo Crítico #1 |
| Transporte P0 | BLE GATT (mínimo común denominador Android↔iOS) | **Nearby Connections** (P2P_CLUSTER) como P0; BLE GATT como fallback | Sin iOS ya no hay razón para pagar el costo de BLE GATT crudo en el camino crítico |
| D2 | Dueño de iOS/proximity | Dueño de **transporte + rol gateway/rescatista** | Se libera ~1 dev-día que va a integración y ensayos |
| Gate T+10 | "dos teléfonos intercambian bundle offline" | Se adelanta a **T+7**; T+10 pasa a ser A→B→C | El vertical slice llega antes, queda más margen para P1 |
| UWB / Wi-Fi Aware | P2 con entitlement iOS | UWB sigue P2 (`android.uwb`, sólo Pixel/Galaxy recientes); Wi-Fi Aware deja de ser feature: queda **oculto dentro de Nearby Connections** | Menos superficie, misma capacidad |

Lo que **no** cambia y sigue siendo ley: North Star `A → B → C → Cloud → Dashboard`, la
jerarquía P0/P1/P2, el lenguaje de seguridad no negociable (nunca `DEAD` por falta de movimiento,
nunca diagnóstico clínico desde PPG RGB, nunca RSSI→profundidad exacta), y la regla de que
**ninguna feature P1/P2 puede bloquear el flujo P0**.

---

## 1. Vista de sistema

```
┌─ VÍCTIMA (A) ────────┐   ┌─ RELAY (B) ──────────┐   ┌─ GATEWAY/RESCATISTA (C) ─┐
│ Flutter · Android    │   │ Flutter · Android    │   │ Flutter · Android        │
│ modo EMERGENCY       │   │ modo RELAY           │   │ modo GATEWAY             │
│ • trigger manual     │   │ • store-carry-fwd    │   │ • recolecta A+B          │
│ • PPG + motion       │   │ • dedupe + TTL       │   │ • GPS propio + RSSI      │
│ • firma Ed25519      │   │ • no lee evidencia   │   │ • cola de subida         │
│ • BundleStore local  │   │ • BundleStore local  │   │ • BundleStore local      │
└──────────┬───────────┘   └──────────┬───────────┘   └───────────┬──────────────┘
           │  Nearby Connections (P0)  │                          │
           └───────────────────────────┴──────────────────────────┘   ▲ offline
                     BLE GATT (fallback)                              │ ─────────
                     Acústico ggwave (P2, sólo ID/SOS)                 ▼ con red
                                                        ┌──────────────────────────┐
                                                        │ services/api  (FastAPI)  │
                                                        │ ingest idempotente       │
                                                        │ PostGIS + WS stream      │
                                                        └───────────┬──────────────┘
                                                        ┌───────────▼──────────────┐
                                                        │ apps/operations-web      │
                                                        │ mapa · timeline · grafo  │
                                                        └──────────────────────────┘
```

**Un solo binario, tres roles.** El rol es estado de runtime (`NodeRole { victim, relay, gateway }`),
no un flavor de build. Cualquier teléfono puede cambiar de rol en el demo, y eso es parte del pitch:
la malla no depende de hardware dedicado. El gateway se distingue sólo por tener `GatewaySync` activo.

---

## 2. Decisiones de arquitectura (ADR compactos)

**ADR-01 · Flutter + Android-only.** Aceptado. Trade-off explícito: se pierde el claim
"cross-platform Android↔iOS" y se gana el gate T+10 con mucha más probabilidad. Se declara en el
pitch como decisión de alcance, no como limitación oculta.

**ADR-02 · Nearby Connections como transporte P0, BLE GATT como fallback.**
`nearby_connections` (Google Play Services, estrategia `P2P_CLUSTER`) negocia solo entre BLE,
Wi-Fi Direct y hotspot, entrega payloads de bytes arbitrarios con callbacks de progreso, y no exige
implementar un servidor GATT ni fragmentación manual. Costo: dependencia de Play Services (aceptable
en los teléfonos del demo) y **cero soporte iOS** (ya irrelevante).
El fallback BLE GATT vive detrás de la misma interfaz `TransportAdapter` y se implementa vía
`MethodChannel` a Kotlin (`BluetoothLeAdvertiser` + `BluetoothGattServer` + `BluetoothLeScanner`),
porque ningún plugin Flutter cubre bien el rol periférico con GATT server.
**Regla:** el fallback se construye recién después de que el camino P0 esté verde.

**ADR-03 · CBOR canónico para el wire, Ed25519 para integridad.** El bundle se serializa a CBOR
determinista (claves ordenadas), se hashea con SHA-256 y se firma con Ed25519 (`package:cryptography`).
La API HTTP habla JSON, pero **el hash y la firma se calculan siempre sobre los bytes CBOR**, nunca
sobre el JSON — así el mismo objeto lógico sobrevive intacto a BLE, Nearby y HTTP.

**ADR-04 · Drift (SQLite) para `BundleStore`.** Persistencia relacional con índices sobre
`(incident_id, priority, expires_at)` y el CBOR crudo como `BLOB`. Se elige sobre Isar/Hive porque
el gate de "reinicio de app conserva bundles reenviables" necesita consultas por rango y por estado
de reenvío, y porque el backend habla SQL: mismos conceptos, menos traducción mental.

**ADR-05 · Riverpod + freezed.** Estado con `flutter_riverpod` (+ `riverpod_generator`), modelos
inmutables con `freezed`. Los servicios de larga vida (transporte, store, DTN) son `Notifier`s
que exponen streams; la UI nunca toca el transporte directamente.

**ADR-06 · Foreground service obligatorio en modo emergencia.** `flutter_foreground_task` con
notificación persistente y `foregroundServiceType="connectedDevice|location"`. Sin esto Android
mata el descubrimiento a los pocos minutos con la pantalla apagada, y el demo se cae en vivo.

**ADR-07 · DSP en isolates.** PPG (stream de cámara ~30 fps) y detección de movimiento corren en
`Isolate`s dedicados. El hilo de UI no procesa señal: una caída de frames durante el demo se lee
como app rota.

**ADR-08 · Feature flags con default OFF.** Registro central en `packages/sismo_core/flags.dart`,
override desde una pantalla de debug. Todo lo que no sea P0 arranca apagado y se enciende sólo
después de probarse en hardware físico.

---

## 3. Estructura del monorepo

Adaptación directa del layout del playbook (`apps/`, `services/`, `protocol/`, `fixtures/`, `demo/`):

```
apps/
  mobile/                      # app Flutter única (Android)
    lib/
      main.dart
      app/                     # router, theme, bootstrap, DI
      features/
        incident/              # activación manual, modo emergencia, estado SAFE/HELP/TRAPPED
        mesh/                  # UI de peers, hops, inventario, debug de transporte
        vitals/                # captura PPG + motion, gating por SQI
        rescuer/               # modo gateway: cola, RF walk, mapa local
        voice/                 # pack de audio offline
        debug/                 # consola de bundles, flags, reset de demo
      core/                    # errores, logging, resultado, flags
    android/
      app/src/main/kotlin/...  # MethodChannel: BLE GATT fallback + hooks de foreground service
packages/
  sismo_protocol/              # ⚠ dueño: D3 — EmergencyBundle v1, CBOR, hash, firma, fixtures
  sismo_transport/             # TransportAdapter + impl Nearby + impl BLE + capability matrix
  sismo_store/                 # BundleStore (Drift) + motor DTN
  sismo_signals/               # PPG, motion, PeerObservation, localización v1
services/
  api/                         # FastAPI + PostGIS + WebSocket (sin cambios vs playbook)
apps/
  operations-web/              # Next.js (sin cambios vs playbook)
protocol/                      # esquema fuente de verdad + generador de fixtures
fixtures/                      # bundles de ejemplo, válidos / corruptos / duplicados / TTL vencido
demo/                          # incidente fijo, scripts de reset, capturas, video de respaldo
```

**Por qué packages separados y no todo en `lib/`:** cada paquete tiene un dueño exclusivo y un
`pubspec.yaml` propio, así D3 puede publicar `sismo_protocol` con fixtures y D1/D2/D4 lo consumen
sin tocarse entre sí. Es la traducción literal de la regla del playbook: *ownership exclusivo,
interfaces compartidas*.

---

## 4. Capas y puertos

Regla de dependencia: `features → core/domain ← packages`. Ninguna feature importa una
implementación concreta de transporte o de base de datos, sólo su interfaz.

```dart
// packages/sismo_transport — dueño D2
abstract interface class TransportAdapter {
  TransportId get id;                                  // nearby | bleGatt | acoustic
  Future<TransportCapabilities> capabilities();        // qué soporta ESTE teléfono, medido en runtime
  Future<void> startAdvertising(NodePresence self);
  Future<void> startDiscovery();
  Stream<PeerEvent> get peers;                         // found / lost / connected / rssi
  Future<SendReceipt> send(PeerId to, List<int> cborBundle);
  Stream<InboundBundle> get inbound;                   // bytes + metadata de enlace (rssi, transport)
  Future<void> stop();
}

// packages/sismo_store — spec D3, uso D1/D2
abstract interface class BundleStore {
  Future<PutResult> put(EmergencyBundle b, {required BundleOrigin origin});
  Future<List<BundleId>> getMissing(InventoryDigest peerDigest);
  Future<InventoryDigest> inventoryDigest();           // Bloom filter + conteo, ver README C.5
  Future<void> markForwarded(BundleId id, PeerId to);
  Future<int> expire(DateTime now);                    // TTL
  Stream<EmergencyBundle> watchPending({int? maxPriority});
}

// packages/sismo_signals — dueño D4
abstract interface class SensorEngine {
  Future<MotionEvidence> captureMotion({Duration window});
  Stream<PpgFrame> capturePpg();                       // corre en isolate
  Future<BioSignalSummary?> getBioSummary();           // null si SQI insuficiente — nunca un valor inventado
}

// dueño D3 + integración móvil
abstract interface class GatewaySync {
  Future<UploadResult> uploadBatch(List<EmergencyBundle> batch, {required String idempotencyKey});
  RetryPolicy get retryPolicy;
  Stream<AckReceipt> get acks;
}
```

`TransportRouter` (D2) mantiene la lista de adapters ordenada por preferencia, consulta
`capabilities()` al arrancar y **oculta en la UI todo transporte no soportado**. Cumple el gate
del playbook: *unsupported != simulated success*.

---

## 5. `EmergencyBundle` v1 — contrato de datos

Congelado por D3 en T+4. Estructura de campos idéntica al playbook, expresada en Dart/freezed y
serializada a CBOR canónico.

| Grupo | Campos | Notas de implementación |
|---|---|---|
| Envelope | `version, incident_id, bundle_id, node_pseudonym, seq, created_at, ttl_s, priority` | `bundle_id = UUIDv7` (ordenable en el tiempo, útil para el timeline). `node_pseudonym` = base64url de los primeros 16 bytes de `SHA-256(pubkey)`, rotado por incidente |
| State | `status ∈ {SAFE, HELP, TRAPPED, UNCONFIRMED}`, `user_reported: bool` | **No existe `DEAD`** en el enum. Que no sea representable en el tipo es la mejor garantía |
| Location | `lat, lon, accuracy_m, source, measured_at` | `source ∈ {gnss, network, peerDerived, manual}`. `measured_at` separado de `created_at`: la ubicación puede ser vieja |
| Evidence | `motion: MotionEvidence?`, `ppg: BioSignalSummary?`, `peers: List<PeerObservation>` | Cada ítem lleva `provenance ∈ {MEASURED, DERIVED, ASSUMED, REFERENCE, IMPUTED}` + `confidence` + `sqi`, siguiendo la tabla de README §C.0 |
| Device | `battery_pct, capabilities, app_version` | Alimenta la política de energía del router: un nodo <15% deja de replicar bulk |
| Integrity | `payload_hash, signer_key_id, signer_pubkey_b64, signature` | SHA-256 + Ed25519 sobre los bytes canónicos. El bundle lleva su clave pública: es auto-verificable, sin registro de claves previo |
| Relay meta | `hop_count, received_from, transport, rssi, gateway_position` | **Envoltura mutable, fuera del payload firmado.** Un relay jamás reescribe la evidencia original |

La separación *payload firmado* / *envoltura de relay mutable* es la pieza que hace que la firma
sobreviva N saltos: cada relay añade su capa sin invalidar la de A.

---

## 6. Motor DTN

Ciclo por contacto, sobre cualquier transporte:

```
descubrir peer → handshake (versión de protocolo + incident_id + inventoryDigest)
              → cada lado calcula getMissing(digest ajeno)
              → transferir faltantes por prioridad ascendente (SOS primero)
              → ACK por bundle_id → markForwarded
```

- **Dedupe:** `bundle_id` es PK. Un `put()` repetido devuelve `PutResult.duplicate` y suma
  evidencia de ruta (un `PeerObservation` más), no una fila nueva. Cubre el test *Duplicate bundle*.
- **Inventario:** Bloom filter con `k_opt ≈ (m/n)·ln2` (README §C.5). Como un falso positivo
  significa creer que el peer ya tiene un bundle que en realidad le falta, **P0 nunca depende sólo
  del Bloom**: siempre hay reconciliación por ACK.
- **Copy budget adaptativo** (mitigación estándar contra flooding, README §C.5):
  `priority 0 (SOS) → 6 réplicas` · `1 (evidencia) → 3` · `2 (bulk/waveform) → sólo hacia gateway`.
- **TTL:** `expire()` corre cada 60 s. Un bundle vencido se marca, no se borra, hasta después del
  demo — el borrado silencioso es indepurable en vivo.
- **Persistencia:** todo `put()` se escribe antes de cualquier ACK. Cubre el test
  *Restart persistence*.

---

## 7. Señales y límites de afirmación

`SensorEngine` devuelve `BioSignalSummary?` — **nullable a propósito**. Si el SQI no pasa el
umbral, el tipo devuelve `null` y la UI muestra *señal insuficiente / reintentar*, no un BPM.
No hay ruta de código que produzca un veredicto de salud, y no la hay tampoco para `DEAD`.

- **PPG:** stream de cámara → canal rojo promedio → detrend → banda 0.7–4 Hz → PSD Welch → HR,
  acompañado siempre de SQI y forma de onda. Todo en isolate, con fixtures deterministas de D4
  para poder desarrollar la UI sin cámara.
- **Movimiento:** `sensors_plus` → ventana → *purposeful motion* (patrón deliberado vs vibración de
  mesa). Fallback si el clasificador no convence: umbral determinista sobre señal cruda + flag.
- **Localización v1:** último fix + `PeerObservation[]` + GPS/RSSI del rescatista → **zona de
  confianza**, nunca metros exactos. La conversión RSSI→profundidad está prohibida por el playbook.
- **Voz:** pack de audio pregenerado con ElevenLabs, embebido en assets y validado en modo avión.

---

## 8. Seguridad (alineación con el track AI Security)

1. **Sin PII en el beacon.** El anuncio lleva `node_pseudonym` + `incident_id` + capacidades. Nada más.
2. **Integridad verificable extremo a extremo.** Firma Ed25519 en A, verificada en B, en C y en el
   backend. Byte volteado → rechazo + log. Cubre el test *Corruption*.
3. **Claude nunca es el oráculo de integridad ni el plano de control.** Es enriquecimiento online
   detrás de feature flag; si falla, el core no se entera. Su salida se marca `IMPUTED` y **nunca**
   se presenta como RAW recuperado.
4. **Secretos sólo desde entorno/CI.** Cero API keys en el APK o en el historial de git — un APK
   es un ZIP, cualquiera lo abre.
5. **Superficie de confianza declarada:** en esta v1 cualquier nodo puede *inyectar* bundles
   firmados con su propia clave (no hay PKI). Lo que se garantiza es **no repudio del emisor e
   integridad en tránsito**, no autenticidad de identidad real. Decirlo en el pitch es más fuerte
   que dejar que un juez lo pregunte.

---

## 9. Feature flags

| Flag | Default | P | Gate para encender |
|---|---|---|---|
| `transport.nearby` | **ON** | P0 | es el camino crítico |
| `transport.bleGatt` | OFF | P0-fallback | probado en 2 teléfonos físicos |
| `transport.acoustic` | OFF | P2 | sólo si P0 está congelado |
| `signals.ppg` | OFF | P1 | SQI validado en ≥2 modelos de teléfono |
| `signals.motion` | OFF | P1 | separa sacudida deliberada de vibración |
| `localization.zone` | OFF | P1 | muestra zona, jamás metros |
| `voice.cachedPack` | OFF | P1 | audio suena en modo avión |
| `ai.claudeAnalysis` | OFF | P2 | apagable sin tocar el core |
| `ranging.uwb` | OFF | P2 | `android.uwb` disponible **y** callback real |

---

## 10. Reparto del equipo (5 devs, sin iOS)

| Dev | Ownership | Primeras 4 h | Entregable núcleo |
|---|---|---|---|
| **D1 — Tech Lead / App** | Freeze de arquitectura, shell Flutter, modo emergencia, roles, batería/ubicación, release train | Scaffold `apps/mobile`, DI, router, `EmergencyMode`, feature flags, foreground service | APK firmado, activación de incidente, UX de emergencia |
| **D2 — Transporte / Mesh** | `TransportAdapter`, Nearby Connections, fallback BLE GATT nativo, matriz de capacidades, rol gateway | Permisos Android, POC Nearby de 2 teléfonos enviando bytes | Bundle cruzando A↔B offline, con RSSI y transporte logueados |
| **D3 — Protocolo / DTN / Backend** | `sismo_protocol` v1, CBOR, cripto, `BundleStore`+DTN, FastAPI, PostGIS, WS, ingest idempotente | Congelar esquema, generar fixtures, esqueleto de backend | Bundle v1 congelado, A→B→C→Cloud, dedupe/TTL/firmas |
| **D4 — Señales / IA** | PPG, motion, `PeerObservation`, localización v1, pack de voz, adaptadores Claude | Librerías deterministas con fixtures, definir `BioSignalSummary` | Evidencia con provenance + SQI, sin afirmaciones clínicas |
| **D5 — Web / Ops / DevOps** | Dashboard Next.js, mapa/timeline/grafo, stream en vivo, CI, telemetría de demo | Dashboard contra mocks generados del esquema | URL desplegada, render en vivo, botón de reset del demo |

RACI, regla de escalamiento (15 min bloqueado → pregunta, 20 → pairing, 45 → cut) y cadencia de
sync cada ~4 h: **igual que el playbook**, sin cambios.

---

## 11. Timeboxes ajustados

| Ventana | Gate | Si falla |
|---|---|---|
| T0–T4 | Protocolo v1 congelado; app compila; dashboard contra mocks | D3 congela el esquema; cero trabajo de UI hasta resolverlo |
| **T4–T7** | **Dos teléfonos intercambian bundle en modo avión (Nearby)** | Enciende `transport.bleGatt` y detén todo lo demás |
| T7–T12 | A→B→C con reinicio de app; upload al gateway | Pairing D1/D2/D3 hasta verde; todo P1 en pausa |
| T12–T16 | Vertical slice completo hasta dashboard | Congela P0; opcionales sólo detrás de flags |
| T16–T22 | Seguridad, reintentos, idempotencia; arranca P1 | — |
| T22–T28 | ≥1 valor de sensor + observación de localización con provenance | Baja la inferencia avanzada; deja evidencia cruda |
| T28–T32 | P0 repetido 5 veces sin editar la DB a mano | Cut #2 |
| T32–T35 | 3 ensayos limpios consecutivos | Sin features nuevas: sólo bugs, copy y media |
| T35–T36 | Freeze, tag, backups | — |

---

## 12. Arranque concreto (primeros 90 minutos)

```bash
# 1. toolchain — no está instalado en esta máquina
#    (instalar Flutter estable + Android SDK + habilitar depuración USB en los teléfonos)
flutter create --org us.platanus.sismomesh --platforms=android apps/mobile
flutter create --template=package packages/sismo_protocol
flutter create --template=package packages/sismo_transport
flutter create --template=package packages/sismo_store
flutter create --template=package packages/sismo_signals
```

Dependencias base de `apps/mobile/pubspec.yaml`:

```yaml
dependencies:
  flutter_riverpod: ^2.5.0
  riverpod_annotation: ^2.3.0
  freezed_annotation: ^2.4.0
  json_annotation: ^4.9.0
  go_router: ^14.0.0
  nearby_connections: ^4.1.0        # transporte P0
  flutter_blue_plus: ^1.32.0        # fallback: rol central
  drift: ^2.18.0
  sqlite3_flutter_libs: ^0.5.0
  cbor: ^6.2.0
  cryptography: ^2.7.0              # Ed25519 + SHA-256
  flutter_foreground_task: ^6.5.0
  sensors_plus: ^5.0.0
  camera: ^0.11.0
  geolocator: ^12.0.0
  battery_plus: ^6.0.0
  connectivity_plus: ^6.0.0
  device_info_plus: ^10.1.0
  permission_handler: ^11.3.0
  just_audio: ^0.9.38
  dio: ^5.4.0
  uuid: ^4.4.0
dev_dependencies:
  build_runner: ^2.4.0
  freezed: ^2.5.0
  json_serializable: ^6.8.0
  riverpod_generator: ^2.4.0
  drift_dev: ^2.18.0
```

> Las versiones son un punto de partida; fijarlas con `flutter pub get` y **commitear
> `pubspec.lock`**. En un hackathon, una resolución de dependencias que cambia sola a las 3 a.m.
> cuesta más que cualquier bug.

`AndroidManifest.xml` — permisos mínimos para que Nearby Connections funcione en Android 12–14:

```xml
<uses-permission android:name="android.permission.BLUETOOTH_SCAN"      android:usesPermissionFlags="neverForLocation" tools:targetApi="s"/>
<uses-permission android:name="android.permission.BLUETOOTH_ADVERTISE" tools:targetApi="s"/>
<uses-permission android:name="android.permission.BLUETOOTH_CONNECT"   tools:targetApi="s"/>
<uses-permission android:name="android.permission.NEARBY_WIFI_DEVICES" android:usesPermissionFlags="neverForLocation" tools:targetApi="tiramisu"/>
<uses-permission android:name="android.permission.ACCESS_FINE_LOCATION"/>
<uses-permission android:name="android.permission.ACCESS_WIFI_STATE"/>
<uses-permission android:name="android.permission.CHANGE_WIFI_STATE"/>
<uses-permission android:name="android.permission.CAMERA"/>
<uses-permission android:name="android.permission.FOREGROUND_SERVICE"/>
<uses-permission android:name="android.permission.FOREGROUND_SERVICE_CONNECTED_DEVICE"/>
<uses-permission android:name="android.permission.FOREGROUND_SERVICE_LOCATION"/>
<uses-permission android:name="android.permission.POST_NOTIFICATIONS"/>
<uses-permission android:name="android.permission.WAKE_LOCK"/>
```

`minSdkVersion 26`, `targetSdkVersion 34`. Los permisos se piden **todos juntos en el onboarding**,
antes del demo — no en medio del flujo de emergencia.

---

## 13. Riesgos nuevos introducidos por Flutter/Android

| Riesgo | P | Impacto | Disparador | Mitigación |
|---|---|---|---|---|
| Nearby Connections exige Play Services | Media | Alto | Teléfono sin GMS / Play Services viejo | Verificar GMS en los 3 teléfonos **en T0**; fallback BLE GATT |
| Permisos runtime bloquean discovery en silencio | **Alta** | Alto | No aparece ningún peer y no hay error | Pantalla de preflight que verifica y muestra cada permiso antes de armar el incidente |
| OEM mata el proceso en background (Xiaomi/Oppo/Samsung) | **Alta** | Alto | Deja de descubrir con pantalla apagada | Foreground service + excluir de optimización de batería + demo con pantalla encendida |
| Jank de UI por procesar cámara en el hilo principal | Media | Medio | Frames caídos durante PPG | Isolates desde el día 1 (ADR-07) |
| Plugin nativo (BLE GATT) consume tiempo de senior | Media | Medio | Fallback tarda > 4 h | Fallback recién después de P0 verde; si no, se corta |
| Deriva de versiones de plugins | Media | Medio | Build roto en otra máquina | `pubspec.lock` commiteado + una versión de Flutter fija para todo el equipo |

---

## 14. La pregunta de siempre

> **"¿Esto hace más confiable la historia de rescate de extremo a extremo antes del próximo gate?"**

Si la respuesta es no, va detrás de un flag apagado o se corta. Cortar es una feature.
