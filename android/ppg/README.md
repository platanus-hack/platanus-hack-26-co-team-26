# :android:ppg

**Propósito:** captura PPG de contacto con CameraX (cámara trasera + flash), sin
grabar foto ni video — los cuadros se procesan en memoria y se liberan de
inmediato. Implementación real integrada desde el blueprint de Laura (ver
`docs/ppg/README.md` para el origen del código y `docs/ppg/KOTLIN_INTEGRATION_BLUEPRINT.md`
para el plano de integración completo).

**Componentes:**

- `RgbFrameAnalyzer.kt` — extrae RGB/saturación/cobertura de un `ImageProxy`
  YUV_420_888 sin construir `Bitmap`, muestreando la ROI cada `pixelStep` píxeles.
- `MotionSampler.kt` — proxy de movimiento del acelerómetro (30–50 Hz) que gatea
  la calidad de la sesión PPG. **No confundir** con el motor de evidencia de
  actividad del proyecto (`core/signal` raíz, dueño Alex) — este sampler es local
  a la sesión de captura PPG, no alimenta el `MotionEvidence` de la malla DTN.
- `PpgEngine.kt` — `CameraXPpgEngine`: máquina de estados
  `Idle→Preparing→Stabilizing→Acquiring→Processing→Completed/Failed/Cancelled`,
  gestiona ciclo de vida de cámara/torch, delega el DSP a `core/signal/ppg`
  (`PpgSignalProcessor`, `SignalQualityEvaluator`, clasificador, `PpgPacketCodec`).

**Pendiente de integración (dueño=Laura/Jorge):** cablear `CameraXPpgEngine`
detrás de `PpgCaptureIPort` (`core/application/ports/SensingPorts.kt`) y de
`RunBiomarkerSession` (`core/application/usecase/UseCases.kt`) para que su
resultado (`PpgPacketCodec.encode(...)`, 28 B) viaje como payload `biomarker`
del bundle DTN — ver `protocol/ppg/PPG_PACKET_V1.md` y
`protocol/proto/helius/v1/biomarker.proto`.

**Dueño:** Laura + Jorge.

**Etiqueta de madurez:** `ENGINEERING` (captura, DSP, empaquetado) — ver la tabla
de madurez completa por elemento en `docs/architecture/OVERVIEW.md` § 10 (AIB).

Ver `docs/team/DIVISION-DE-TRABAJO.md` y
`core/src/commonMain/kotlin/co/helius/core/application/ports/` para el
contrato exacto de puertos.
