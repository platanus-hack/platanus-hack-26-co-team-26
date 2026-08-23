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
  sobre la red, no solo en memoria como el test de JVM.
- `core/protocol/BundleWireCodec.kt` (en `:core`) — convierte entre el
  `Bundle` de dominio y las clases protobuf generadas; sin esto no había forma
  de mandar un bundle real por el aire. Cubre el payload `Status` completo
  (el que necesita el Slice 0); `Motion`/`Biomarker`/`Observation` lanzan
  `NotImplementedError` explícito hasta que tengan tipo de dominio real.

**Pendiente:**

- `gatt.requestMtu()` — hoy siempre se asume el MTU mínimo (23 B); funciona pero es más lento de lo necesario.
- Múltiples conexiones GATT simultáneas al mismo servidor (hoy solo soporta una a la vez, ver `BleGattServer`).
- Wi-Fi Aware, Wi-Fi Direct, Nearby, UWB — sin empezar.
- UUID de servicio de desarrollo (`BleGattProfile.SERVICE_UUID`) — reservar uno oficial antes de release.
- Sin verificar en hardware real — correr contra la matriz de fabricantes (`docs/validation/VALIDATION.md`) antes de dar por bueno el comportamiento en background.

**Dueño:** Helmut.

**Etiqueta de madurez:** `ENGINEERING` (implementación real completa para el
flujo de estado/SOS, sin verificar en dispositivo — ver `docs/validation/PHONE-READINESS.md`).
