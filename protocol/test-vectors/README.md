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

**Pendiente:** `signature` es un placeholder de 64 ceros. `core/crypto/Identity.kt`
ya tiene una implementación Ed25519 real, pero firmar con una clave generada al
vuelo rompería la reproducibilidad de estos vectores (deben dar el mismo byte a
byte cada vez); regenerarlos con firma real requiere fijar una clave de prueba
determinista primero. No usar estos vectores para probar verificación de firma
todavía, solo serialización.

**Regla:** un bundle serializado en Kotlin debe coincidir byte a byte con
`bundles/*.bin` (`protocol-ci.yml`). Sin excepciones — es la prueba que elimina
la clase de bug más cara del proyecto ("mi lado del contrato funciona en mi máquina").

**Verificación real:**

- Python: `python3 protocol/test-vectors/verify_python_roundtrip.py` — corre en
  este mismo entorno, sin Gradle. Ya verificado: los 5 vectores pasan.
- Kotlin: `core/src/androidUnitTest/kotlin/co/helius/core/protocol/BundleGoldenVectorTest.kt`
  — cubre `status_trapped`, `observation_peer`, `raw_chunk` (los tres tipos de
  payload que `BundleWireCodec` ya soporta). `motion_purposeful` y
  `biomarker_pulse` quedan fuera hasta que Alex defina `MotionEvidence`/
  `BiomarkerEvidence` reales. **No ejecutado todavía** — requiere Gradle real,
  ver `docs/validation/PHONE-READINESS.md`.

Falta `beacons/*.hex` (ejemplo de beacon BLE de 26 B, formato en
`protocol/beacon/BEACON_FORMAT.md`) y `signatures/*.json` — quedan pendientes
hasta fijar la clave de prueba determinista mencionada arriba.

**Dueño:** Helmut.
