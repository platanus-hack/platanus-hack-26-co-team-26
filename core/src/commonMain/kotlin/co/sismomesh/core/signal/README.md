# core/signal

**Propósito:** DSP puro (Kotlin, sin Android) para PPG y evidencia de movimiento.
Testeable con grabaciones reproducidas, sin ningún teléfono.

## `signal/ppg/` — pipeline PPG completo (integrado, no stub)

Código real integrado desde el blueprint de Laura (`docs/ppg/`, ver
`docs/ppg/README.md` para el origen): `Models.kt` (vocabulario compartido con
`android/ppg`), `PpgSignalProcessor.kt` (remuestreo/detrend/filtro/derivadas/picos),
`SignalQualityEvaluator.kt` (SQI y gates), `PhysiologicalClassifier.kt`
(`SafetyFirstClassifier`, baseline determinista), `IfoFusionEngine.kt` (combina
evidencia sin diagnosticar), `EstimatedEcgReconstructor.kt` +
`SignalModelRunner.kt` (reconstrucción `estimated_ecg`, detrás de gate de
aprobación independiente — ver `docs/ppg/PPG_TO_ECG.md`), `PpgPacketCodec.kt`
(payload binario de 28 B, especificación en `protocol/ppg/PPG_PACKET_V1.md`).

> **Nota de portabilidad (fase 2):** `PpgPacketCodec.kt` y `SignalModelRunner.kt`
> usan `java.nio`/`java.security`, válido mientras `iosMain` esté desactivado
> (ver `core/src/iosMain/README.md`). Migrar a multiplataforma antes de activar
> el target iOS.

## `signal/` (raíz) — evidencia de movimiento del proyecto

Features de acelerómetro para el motor de evidencia de actividad (RMS, energía,
ZCR, entropía espectral, patrón intencional) — distinto del `MotionSampler`
interno de `android/ppg` (que solo gatea calidad de señal PPG). Ver
`docs/architecture/OVERVIEW.md` § 9.

**Puertos relacionados:** `BiomarkerInferencePort`, `MotionPort` (implementaciones
de apoyo — el puerto en sí vive en `core/application/ports`).

**Dueño:** Alex (DSP de movimiento, modelo AIB) + Laura/Jorge (integración PPG con
`:android:ppg`, captura y app).

**Etiqueta de madurez:** `ENGINEERING` (frecuencia de pulso, SQI, empaquetado) /
`EXPERIMENTAL` (PRV, respiración, perfusión, `estimated_ecg`) — ver
`docs/architecture/OVERVIEW.md` § AIB y el estado del arte de PPG en el
`README.md` raíz.
