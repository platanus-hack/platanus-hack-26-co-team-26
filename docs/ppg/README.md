# Módulo PPG de contacto — Evaluación Fisiológica Orientativa (EFO / AIB)

Diseñado y desarrollado por Laura (con Jorge en la integración de app). Integra
adquisición PPG por cámara trasera + flash en Kotlin, con entrenamiento y
validación en Python. Produce observaciones de señal (frecuencia de pulso, SQI,
patrón fisiológico) y una reconstrucción `estimated_ecg` opcional — no asigna
prioridad clínica, diagnóstico ni conducta médica. En el resto del proyecto este
resultado se integra como el módulo **AIB** (Análisis e Interpretación de
Biomarcadores); el nombre de referencia original del indicador en estos
documentos es **IFO** (Indicador Fisiológico Orientativo) — ver `docs/glossary.md`.

## Dónde vive el código en este monorepo

Los documentos de esta carpeta (`ARCHITECTURE.md`, `INTEGRATION.md`,
`KOTLIN_INTEGRATION_BLUEPRINT.md`, `PPG_TO_ECG.md`, `VALIDATION.md`,
`TEST_AND_RELEASE_MATRIX.md`, `APP_INTEGRATION_EXAMPLE.md`,
`DEVELOPER_CHECKLIST.md`) se conservan tal como los entregó Laura — son la
referencia de diseño. El código ya está integrado en la estructura hexagonal del
proyecto; cuando estos documentos mencionen una ruta, el mapeo real es:

| Ruta en la entrega original de Laura | Ruta real en el monorepo |
|---|---|
| `android/ppg-core/.../com/sismomesh/ppg/RgbFrameAnalyzer.kt`, `MotionSampler.kt` | `android/ppg/src/main/kotlin/co/helius/android/ppg/` |
| `android/ppg-core/.../com/sismomesh/ppg/PpgEngine.kt` (`CameraXPpgEngine`) | `android/ppg/src/main/kotlin/co/helius/android/ppg/PpgEngine.kt` |
| `android/ppg-core/.../com/sismomesh/ppg/{Models,PpgSignalProcessor,SignalQualityEvaluator,PhysiologicalClassifier,EstimatedEcgReconstructor,IfoFusionEngine,PpgPacketCodec,SignalModelRunner}.kt` | `core/src/commonMain/kotlin/co/helius/core/signal/ppg/` (Kotlin puro, testeable en JVM sin Android — ver ADR-0003) |
| `android/ppg-core/src/test/**` | `core/src/commonTest/kotlin/ppg/` (adaptados de JUnit4 a `kotlin.test` para portabilidad multiplataforma) |
| `protocol/PPG_PACKET_V1.md` | `protocol/ppg/PPG_PACKET_V1.md` |
| `training/` (Python) | `ml/ppg/training/` (paquete `src/` intacto, mismos imports) |
| `backend/` (registro de modelos FastAPI) | `services/ppg_model_registry/` |

El nombre del proyecto era "SismoMesh" al momento de esta entrega; el paquete
Kotlin `com.sismomesh.ppg` (nombre original de Laura) se dividió en dos,
siguiendo la
regla hexagonal del proyecto (`docs/architecture/ADR/0001-hexagonal.md`,
`0003-kmp-core-ios-standby.md`): lo que no depende de `android.*`/CameraX vive en
`core/signal/ppg` (paquete `co.helius.core.signal.ppg`); lo que sí depende de
CameraX/sensores vive en `android/ppg` (paquete `co.helius.android.ppg`).

## Decisión de producto

Este módulo no graba fotografías ni videos. `CameraX ImageAnalysis` entrega
cuadros en memoria; de cada cuadro se extraen estadísticas RGB de una región de
interés y el cuadro se libera inmediatamente.

El resultado primario es una PPG óptica medida. La reconstrucción PPG→ECG es un
componente del proyecto, pero su salida se identifica siempre como
`estimated_ecg` y permanece separada de un ECG medido — solo podrá aportar al
indicador combinado después de superar validación externa prospectiva (ver
`PPG_TO_ECG.md`).

## Qué entrega el módulo

- PPG cruda y filtrada, únicamente en memoria durante la sesión.
- Frecuencia de pulso y regularidad básica.
- Índice de calidad de señal (SQI) y motivos de rechazo.
- Observación fisiológica orientativa, no diagnóstica.
- Reconstrucción PPG→ECG mediante modelo teacher–student, salida explícitamente estimada.
- Paquete binario compacto de 28 B para comunicación entre dispositivos (`protocol/ppg/PPG_PACKET_V1.md`).

## Límites obligatorios

Las únicas salidas autorizadas son observaciones de señal (`PhysiologicalObservation`
en `core/signal/ppg/Models.kt`): `STABLE_PATTERN`, `HIGH_PULSE_PATTERN`,
`LOW_PULSE_PATTERN`, `IRREGULAR_PULSE_PATTERN`, `REDUCED_PERFUSION_OR_CONTACT`,
`PHYSIOLOGICAL_ACTIVATION_PATTERN`, `UNRELIABLE_MEASUREMENT`. Nunca `herido`,
`shock`, `ansiedad`, prioridad clínica o un diagnóstico cardíaco como conclusión
obtenida solamente de la PPG — ver `docs/glossary.md`.

## Presupuesto de recursos objetivo

| Recurso | Objetivo |
|---|---:|
| Resolución de análisis | 640×480 YUV; ROI muestreada |
| FPS objetivo | 30 Hz usando timestamps reales |
| Ventana rápida | 15 s útiles + estabilización |
| Muestras de señal | 450 por canal |
| Parámetros Tiny-TCN | <100.000 |
| Modelo INT8 | <500 KB esperado |
| Pico adicional de RAM del pipeline | <12 MB, sin video |
| Inferencia CPU | <25 ms en dispositivo Android medio de referencia |
| Resumen binario | 28 bytes, sin waveform |

Los objetivos de latencia y memoria deben medirse en los teléfonos reales de la
matriz de fabricantes (`docs/validation/VALIDATION.md`); no son garantías antes
del *benchmarking*.

## Fuentes base

- CameraX ImageAnalysis: https://developer.android.com/media/camera/camerax/analyze
- CameraX architecture: https://developer.android.com/media/camera/camerax/architecture
- LiteRT Android: https://ai.google.dev/edge/litert/android
- Cuantización INT8: https://ai.google.dev/edge/litert/performance/post_training_integer_quant
- BIDMC PPG/ECG: https://physionet.org/content/bidmc/
- MIMIC-III Waveform Matched: https://physionet.org/content/mimic3wdb-matched/

## Estado de entrega

La estructura, contratos y baseline son implementables. No se incluye un modelo
clínicamente validado ni pesos ficticios: entrenar, calibrar y aprobar pesos
requiere datos simultáneos de cámara-PPG y referencia ECG/pulsioxímetro
obtenidos con protocolo ético y población objetivo.

**Dueño:** Laura (captura e integración en app) + Jorge (integración de app) +
Alex (modelo, revisor del DSP). Ver `docs/team/DIVISION-DE-TRABAJO.md`.
