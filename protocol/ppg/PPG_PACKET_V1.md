# PPG Packet v1 — resumen de 28 bytes

Formato compacto para el payload `biomarker` en el tier T0/T1 del bundle (ver
`protocol/docs/PROTOCOL.md` § Tiers y `protocol/proto/sismomesh/v1/biomarker.proto`).
Codificado/decodificado por `PpgPacketCodec` en
`core/src/commonMain/kotlin/co/sismomesh/core/signal/ppg/PpgPacketCodec.kt`.

Todos los enteros son little-endian. El transporte debe añadir cifrado/autenticación
(ver `docs/security/THREAT-MODEL.md`); el CRC aquí solo detecta corrupción accidental.

| Offset | Bytes | Campo |
|---:|---:|---|
| 0 | 2 | Magic `0x50 0x47` (`PG`) |
| 2 | 1 | Versión = 1 |
| 3 | 1 | Flags |
| 4 | 8 | Session ID aleatorio |
| 12 | 4 | Tiempo Unix en segundos, truncado |
| 16 | 1 | BPM redondeado; 255 = desconocido |
| 17 | 1 | SQI 0–100 |
| 18 | 1 | Código de observación (`PhysiologicalObservation.code`) |
| 19 | 1 | Confianza 0–100; 255 = desconocida |
| 20 | 2 | IBI mediano ms; 65535 = desconocido |
| 22 | 2 | RMSSD corto ms; 65535 = desconocido/no válido |
| 24 | 1 | Motivos de calidad bitmask bajo |
| 25 | 1 | Modelo/preprocesador major packed |
| 26 | 2 | CRC-16/CCITT-FALSE de bytes 0..25 |

**Flags:**

- bit 0: medición pasó gates de calidad.
- bit 1: clasificador IA aprobado participó.
- bit 2: baseline determinista participó.
- bit 3: hay movimiento elevado.
- bits 4–7 reservados y deben ser cero.

**No incluir ECG reconstruido en v1** — `estimated_ecg` usa un paquete versionado
independiente cuando se transmite (por defecto no se transmite, ver
`docs/ppg/PPG_TO_ECG.md`).

**Relación con `BiomarkerEvidence` (protobuf):** este formato de 28 B es la
codificación compacta para BLE (T0/T1); `BiomarkerEvidence` en
`biomarker.proto` es el mensaje más rico (T1/T2) para enlaces de mayor
*goodput*. Ambos deben mantenerse semánticamente equivalentes — cambios aquí
requieren ADR (ver `docs/architecture/ADR/0004-protobuf-wire-format.md`).

**Dueño:** Laura/Jorge (codec) + Helmut (integración en el transporte y en el protocolo).
