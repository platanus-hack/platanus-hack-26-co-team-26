# Prueba de interconexión BLE entre dos teléfonos

Checklist de campo para cuando `android/transport` compile y esté cableado en
la app (Laura/Jorge). Corresponde a los niveles L2/L3 de
`docs/validation/PHONE-READINESS.md`. Necesitas: dos teléfonos Android
(API 26+), y opcionalmente una app externa tipo **nRF Connect** en un tercer
dispositivo para inspeccionar el advertising de forma independiente.

## 0. Antes de tocar dos teléfonos

- [ ] `./gradlew :core:compileDebugKotlinAndroid` en verde.
- [ ] `./gradlew :core:testDebugUnitTest` en verde (incluye `CryptoRoundTripTest` y `BundleGoldenVectorTest`).
- [ ] La app pide en runtime los permisos `BLUETOOTH_SCAN`, `BLUETOOTH_ADVERTISE`, `BLUETOOTH_CONNECT` — si `BleTransport.requirePermission()` lanza excepción, la app no los pidió todavía.

## 1. Advertising visible (un solo teléfono)

1. Instala el APK debug en el Teléfono A.
2. Dispara `startAdvertising()` (o el flujo de UI que lo invoque).
3. Con nRF Connect en un tercer dispositivo (o con el propio Teléfono B antes de correr la app), busca un anuncio BLE con el UUID de servicio `0000f5a5-0000-1000-8000-00805f9b34fb` (`BleGattProfile.SERVICE_UUID`).
4. **Qué verificar, no asumir:**
   - ¿Aparece el anuncio? Si no aparece, revisar `docs/validation/PHONE-READINESS.md` § presupuesto de 31 B — puede que el fabricante trunque el service data.
   - Tamaño real del payload de `service data` — debe ser 23 bytes exactos (`BleBeaconCodec.WIRE_SIZE`). Si el fabricante lo recorta, es un hallazgo real para la matriz de dispositivos.
   - Primeros 2 bytes = `0x5A 0x4D` (MAGIC).

## 2. Scan + decodificación (dos teléfonos, sin conectar)

1. Teléfono A: advertising activo (paso 1).
2. Teléfono B: dispara `observePeers()`.
3. **Qué verificar:**
   - ¿Llega un `PeerSighting` con el `PeerId` (MAC) del Teléfono A?
   - ¿El `Rssi` reportado es razonable (negativo, entre -30 y -90 dBm típico)?
   - ¿`BleBeaconCodec.decode()` no devuelve `null`? Si devuelve `null`, el AUTH (HMAC) no coincidió — revisar que ambos teléfonos usen la misma `sessionKey()`.

## 3. Conexión GATT + sincronización completa (el resultado real)

1. Con ambos teléfonos corriendo (A anunciando, B escaneando), en B invoca `connect(peer)` sobre el `PeerId` detectado.
2. Antes de conectar, guarda en A un `Bundle` de prueba en su `BundleStorePort` local (p. ej. un `EmergencyStatus` con `TRAPPED`).
3. **Qué verificar, en orden:**
   - `connect()` en B no lanza excepción y devuelve un `PeerLink`.
   - En A, `BleGattServer` recibe la conexión (`onConnectionStateChange` → `STATE_CONNECTED`).
   - Ambos lados habilitan notificaciones (CCCD) sin error.
   - El Bloom filter de B llega a A (`onCharacteristicWriteRequest` en `INVENTORY_CHARACTERISTIC_UUID`).
   - A responde con su propio Bloom filter + empuja el bundle de prueba por `BUNDLE_TRANSFER_CHARACTERISTIC_UUID`.
   - **El bundle de prueba aparece en el `BundleStorePort` de B.** Este es el criterio de aceptación real — compara el `bundle_id` recibido contra el que guardaste en A, deben coincidir byte a byte.
4. Repite invirtiendo los roles (B anuncia, A escanea y conecta) — el protocolo es simétrico, ambos casos deben funcionar igual.

## 4. Qué hacer con lo que encuentres

- Si algo falla, anota **en qué paso exacto** (1-4) y el mensaje de error/logcat completo — eso apunta directo al archivo responsable (`BleTransport`, `BleGattServer`, `BleGattClient`, `BleBeaconCodec`).
- Si todo funciona: has demostrado el núcleo del Slice 0 a nivel de transporte. Falta todavía repetirlo con tres teléfonos para el escenario A→B→C→R completo (`docs/roadmap/VERTICAL-SLICES.md`).
- Actualiza `docs/validation/PHONE-READINESS.md` marcando qué se verificó — ese documento existe justamente para no perder este historial.

**Dueño:** Helmut (con Laura para el lado de la app/UI que dispara estos flujos).
