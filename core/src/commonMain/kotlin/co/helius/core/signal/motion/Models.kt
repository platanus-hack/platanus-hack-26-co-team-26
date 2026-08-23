package co.helius.core.signal.motion

/**
 * Vocabulario del motor de evidencia de actividad/movimiento intencional
 * (RMS, energía, ZCR, entropía espectral, patrón intencional — ver
 * `core/signal/README.md` § "evidencia de movimiento del proyecto" y
 * `docs/architecture/OVERVIEW.md` § 9). DSP puro, sin Android: testeable en
 * JVM sobre grabaciones reproducidas, igual que `core/signal/ppg`.
 *
 * Distinto del `MotionSampler` de `android/ppg` (que sólo gatea calidad de
 * señal PPG dentro de una sesión de captura) — esto alimenta la evidencia de
 * actividad de la malla DTN (`MotionPort`, `EvaluateActivityEvidence`).
 */

/** Una muestra ya reducida a magnitud escalar de un eje/sensor. */
data class MotionSample(val timestampMs: Long, val magnitude: Double)

/** Features resumidas de un sensor (acelerómetro o giroscopio) sobre una ventana. */
data class AxisFeatures(
    val rms: Double,
    val energy: Double,
    val zeroCrossingRate: Double,
    /** null si la ventana no tiene muestras suficientes para un DFT confiable. */
    val dominantFreqHz: Double?,
    /** Baja entropía = energía concentrada en pocas frecuencias (huella de una
     * sacudida deliberada); alta entropía = energía repartida (vibración/ruido). */
    val spectralEntropy: Double?,
)

/**
 * Ventana ya resumida (RMS/energía/ZCR/espectro) más las muestras crudas de
 * acelerómetro, que el detector de patrón necesita para agrupar picos en
 * ráfagas. Este tipo vive sólo dentro de `core/signal/motion` y
 * `EvaluateActivityEvidence` -- nunca se serializa ni cruza el puerto de
 * transporte: lo que sale al wire es [MotionClassification], ya resumido.
 */
data class MotionWindow(
    val startedAtMs: Long,
    val endedAtMs: Long,
    val sampleRateHz: Double,
    val accel: AxisFeatures,
    val gyro: AxisFeatures,
    val accelSamples: List<MotionSample>,
)

/**
 * Estados de wire — deben calzar 1:1 con `activity_state` en
 * `protocol/proto/helius/v1/motion.proto`. `PULSE_SIGNAL_DETECTED` y
 * `RESPONSIVE` pertenecen a otras fuentes de evidencia (PPG, interacción de
 * pantalla); este clasificador nunca los emite.
 */
enum class ActivityState { UNKNOWN, NO_RECENT_EVIDENCE, MOTION_DETECTED, PURPOSEFUL_MOTION }

/**
 * Salida del clasificador de movimiento — mapea 1:1 a `MotionEvidence`
 * (motion.proto): purposeful_motion_confidence, pattern, last_motion_ts,
 * activity_state. Nunca "caída detectada", "convulsión" ni ningún término
 * clínico — ver docs/architecture/ADR/0006-no-clinical-claims.md.
 */
data class MotionClassification(
    val purposefulMotionConfidence: Double,
    /** p.ej. "3-3" (ráfagas de 3 picos separadas por una pausa, patrón tipo
     * SOS). Vacío si no hay un patrón de ráfagas reconocible. */
    val pattern: String,
    val lastMotionTsMs: Long?,
    val activityState: ActivityState,
)
