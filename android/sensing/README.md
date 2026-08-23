# :android:sensing

**Propósito:** SensorManager, buffers, ventanas de acelerómetro/giroscopio. Implementa MotionPort de :core.

**Dueño:** Alex.

**Etiqueta de madurez:** `ENGINEERING` (propuesta funcional en revisión -- ver nota abajo).

## Contenido

- `SensorManagerMotionAdapter.kt` — implementación de referencia de `MotionPort`:
  `TYPE_LINEAR_ACCELERATION` + `TYPE_GYROSCOPE`, ventana deslizante resumida
  cada 2s (RMS/ZCR/espectro vía `core/signal/motion/MotionFeatureExtractor`).
  No pide permiso runtime.
- El DSP/clasificación (RMS, energía, ZCR, entropía espectral, detección de
  patrón tipo "3-3", clasificador determinista sin ML) vive en
  `core/src/commonMain/kotlin/co/helius/core/signal/motion/` -- testeable
  en JVM sin teléfono, ver `core/src/commonTest/kotlin/motion/`.
- `EvaluateActivityEvidence` (core/application/usecase/UseCases.kt) ya
  consume `MotionPort` end-to-end.

> **Nota:** esto es una propuesta de implementación completa, en una rama
> separada (`feat/motion-alert-evidence`) para comparar con lo que Alex ya
> tenga en curso -- no asume que reemplaza su trabajo. Pendiente: cablear
> `SensorManagerMotionAdapter` en la DI de `android/app` (fuera de este
> alcance, carpeta de Laura/Jorge) y, si aplica, mapear
> `MotionClassification` al `MotionEvidence` generado de
> `protocol/proto/helius/v1/motion.proto` en `BundlePayload.Motion`
> (`core/domain/model/Bundle.kt`) -- no tocado aquí porque depende del
> codegen de protobuf, que no se pudo verificar en este entorno.

Ver `docs/team/DIVISION-DE-TRABAJO.md` y `core/src/commonMain/kotlin/co/helius/core/application/ports/` para el contrato exacto de puertos.
