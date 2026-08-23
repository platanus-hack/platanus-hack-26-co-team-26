package co.helius.core.signal.motion

import kotlin.math.min

/**
 * Clasificador determinista, sin ML -- equivalente de `SafetyFirstClassifier`
 * (core/signal/ppg) para el dominio de movimiento. Ningún resultado afirma
 * nada sobre la persona más allá de "hubo/no hubo un patrón de movimiento
 * consistente con una señal deliberada" -- ver
 * docs/architecture/ADR/0006-no-clinical-claims.md.
 */
interface ActivityEvidenceClassifier {
    fun classify(window: MotionWindow): MotionClassification
}

/**
 * Umbral determinista sobre RMS + giro coordinado + entropía espectral:
 *
 * - RMS de aceleración bajo [stillRmsThreshold] -> `NO_RECENT_EVIDENCE`,
 *   confianza 0. Nunca se usa para inferir lo contrario (ausencia de
 *   movimiento no es evidencia de nada sobre la persona).
 * - RMS de aceleración y de giro ambos por encima de sus umbrales, Y energía
 *   concentrada en pocas frecuencias (entropía espectral baja: la huella de
 *   una mano sacudiendo el teléfono, no de una superficie vibrando) ->
 *   `PURPOSEFUL_MOTION`, con el patrón de ráfagas de [MotionPatternDetector].
 * - Cualquier otro movimiento -> `MOTION_DETECTED`, confianza acotada baja
 *   a propósito: nunca se sobre-afirma intención sin evidencia suficiente.
 */
class DeterministicActivityClassifier(
    private val stillRmsThreshold: Double = 0.5,
    private val shakeRmsThreshold: Double = 3.0,
    private val shakeGyroThreshold: Double = 2.0,
    private val maxSpectralEntropyForPattern: Double = 0.75,
) : ActivityEvidenceClassifier {

    override fun classify(window: MotionWindow): MotionClassification {
        val accel = window.accel
        val gyro = window.gyro
        val lastMotionTsMs = window.accelSamples.lastOrNull()?.timestampMs

        if (accel.rms < stillRmsThreshold) {
            return MotionClassification(
                purposefulMotionConfidence = 0.0,
                pattern = "",
                lastMotionTsMs = lastMotionTsMs,
                activityState = ActivityState.NO_RECENT_EVIDENCE,
            )
        }

        val looksDeliberate = accel.rms >= shakeRmsThreshold &&
            gyro.rms >= shakeGyroThreshold &&
            (accel.spectralEntropy == null || accel.spectralEntropy <= maxSpectralEntropyForPattern)

        if (looksDeliberate) {
            val peakThreshold = stillRmsThreshold + (shakeRmsThreshold - stillRmsThreshold) / 2
            val pattern = MotionPatternDetector.detect(window.accelSamples, peakThreshold)
            val confidence = min(1.0, accel.rms / (shakeRmsThreshold * 2))
            return MotionClassification(
                purposefulMotionConfidence = confidence,
                pattern = pattern,
                lastMotionTsMs = lastMotionTsMs,
                activityState = ActivityState.PURPOSEFUL_MOTION,
            )
        }

        val confidence = min(0.4, accel.rms / (shakeRmsThreshold * 2))
        return MotionClassification(
            purposefulMotionConfidence = confidence,
            pattern = "",
            lastMotionTsMs = lastMotionTsMs,
            activityState = ActivityState.MOTION_DETECTED,
        )
    }
}
