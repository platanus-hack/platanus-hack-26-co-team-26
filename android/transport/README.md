# :android:transport

**Propósito:** BLE (advertising, scan, GATT), Wi-Fi Aware, Wi-Fi Direct, Nearby,
UWB oportunista. Implementa `TransportPort` de `:core`.

> [!WARNING]
> Este módulo nunca se compiló (entorno de desarrollo sin JDK/Android SDK) —
> ver `docs/validation/PHONE-READINESS.md` antes de asumir que algo de aquí
> funciona. Es implementación real, revisada con cuidado, con varios bugs
> reales ya encontrados y corregidos por inspección — pero no ejecutada ni una vez.

**Implementado (real, no stub):**

- `BleBeaconCodec.kt` — codifica/decodifica el beacon de 23 B
  (`protocol/beacon/BEACON_FORMAT.md`), con AUTH (HMAC-SHA256 truncado a 4 B
  vía `core/crypto/BeaconAuthenticator`) verificado contra la clave del incidente.
- `BleTransport.kt` (`TransportPort`) — advertising con `BluetoothLeAdvertiser`,
  scan con `BluetoothLeScanner` (decodifica beacons a `PeerSighting` con RSSI real).
- `BleGattProfile.kt` — esquema GATT: un servicio con dos características
  bidireccionales (inventario, transferencia de bundles), cada una con su CCCD.
- `BleChunking.kt` — framing para partir mensajes en escrituras/notificaciones
  del tamaño del MTU negociado (el MTU real nunca es tan grande como se
  quisiera — chunking es obligatorio, no opcional).
- `BleGattServer.kt` / `BleGattClient.kt` — **protocolo GATT completo y
  simétrico**: cada teléfono corre ambos roles a la vez (servidor para cuando
  lo conectan, cliente para cuando conecta él). Intercambian Bloom filters
  (chunked) y se empujan mutuamente los bundles que al otro le faltan —
  implementa de verdad el store-carry-forward de `EncounterStateMachine`
  sobre la red, no solo en memoria como el test de JVM. El cliente negocia
  MTU (`gatt.requestMtu(517)`, con fallback a 23 B) y el servidor soporta
  múltiples peers conectados a la vez (estado indexado por `device.address`,
  no en campos únicos) — ver `docs/validation/PHONE-READINESS.md`.
- `core/protocol/BundleWireCodec.kt` (en `:core`) — convierte entre el
  `Bundle` de dominio y las clases protobuf generadas; sin esto no había forma
  de mandar un bundle real por el aire. Cubre el payload `Status` completo
  (el que necesita el Slice 0); `Motion`/`Biomarker`/`Observation` lanzan
  `NotImplementedError` explícito hasta que tengan tipo de dominio real.

**Pendiente:**

- Wi-Fi Aware, Wi-Fi Direct, Nearby, UWB — sin empezar. Si se agrega un
  segundo transporte, considerar correr todos los adaptadores habilitados en
  paralelo (no fallback secuencial) para un SOS: la urgencia justifica el
  costo de batería de escanear/anunciar en varios a la vez en vez de esperar
  a que uno agote su timeout — idea tomada del prototipo Flutter descartado
  (`transport_router.dart`), no implementada porque hoy solo hay un transporte.
- Beacon acústico (tipo ggwave) como fallback terciario de solo ID/SOS — el
  prototipo Flutter descartado tenía uno (`acoustic_beacon.dart`), deliberadamente
  fuera de `TransportPort` porque solo mueve un string corto, no bundles
  completos. No hay equivalente en Kotlin; no es un hueco urgente, requeriría
  su propio ADR si el equipo lo quiere.
- UUID de servicio de desarrollo (`BleGattProfile.SERVICE_UUID`) — reservar uno oficial antes de release.
- Sin verificar en hardware real — correr contra la matriz de fabricantes (`docs/validation/VALIDATION.md`) antes de dar por bueno el comportamiento en background.

**Dueño:** Helmut.

**Etiqueta de madurez:** `ENGINEERING` (implementación real completa para el
flujo de estado/SOS, sin verificar en dispositivo — ver `docs/validation/PHONE-READINESS.md`).
