# Vectores dorados

5 bundles dorados (uno por tipo de payload) en `bundles/*.json` (legible) +
`bundles/*.bin` (protobuf binario), generados de forma determinista por
`generate_golden_vectors.py` (requiere `protoc` y el paquete `protobuf` de
Python — corre `python3 generate_golden_vectors.py` desde `protocol/test-vectors/`
tras `make proto`).

| Vector | Payload | Prioridad |
|---|---|---|
| `status_trapped` | `EmergencyStatus` (TRAPPED) | P1_LOCATION |
| `motion_purposeful` | `MotionEvidence` (patrón "3-3") | P1_LOCATION |
| `biomarker_pulse` | `BiomarkerEvidence` (pulso + SQI) | P2_STATUS |
| `observation_peer` | `PeerObservation` (RSSI entre dos nodos) | P3_NETWORK_OBS |
| `raw_chunk` | `RawSensorChunk` (T2) | P4_RAW_SENSOR |

**Pendiente:** `signature` es un placeholder de 64 ceros — se regenerará con una
firma Ed25519 real cuando `core/crypto/Identity.kt` esté implementado. No usar
estos vectores para probar verificación de firma todavía, solo serialización.

**Regla:** un bundle serializado en Kotlin debe coincidir byte a byte con
`bundles/*.bin` (`protocol-ci.yml`). Sin excepciones — es la prueba que elimina
la clase de bug más cara del proyecto ("mi lado del contrato funciona en mi máquina").

Falta `beacons/*.hex` (ejemplo de beacon BLE de 26 B, formato en
`protocol/beacon/BEACON_FORMAT.md`) y `signatures/*.json` — quedan pendientes
hasta tener `core/crypto` real.

**Dueño:** Helmut.
