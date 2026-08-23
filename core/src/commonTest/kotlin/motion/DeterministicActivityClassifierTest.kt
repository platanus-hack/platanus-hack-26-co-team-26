package motion

import co.helius.core.signal.motion.ActivityState
import co.helius.core.signal.motion.AxisFeatures
import co.helius.core.signal.motion.DeterministicActivityClassifier
import co.helius.core.signal.motion.MotionSample
import co.helius.core.signal.motion.MotionWindow
import kotlin.test.Test
import kotlin.test.assertEquals
import kotlin.test.assertTrue

class DeterministicActivityClassifierTest {

    private val classifier = DeterministicActivityClassifier(
        stillRmsThreshold = 0.5,
        shakeRmsThreshold = 3.0,
        shakeGyroThreshold = 2.0,
        maxSpectralEntropyForPattern = 0.75,
    )

    private fun axis(rms: Double, entropy: Double? = null) =
        AxisFeatures(rms = rms, energy = rms * rms, zeroCrossingRate = 0.0, dominantFreqHz = null, spectralEntropy = entropy)

    private fun window(
        accel: AxisFeatures,
        gyro: AxisFeatures,
        accelSamples: List<MotionSample> = emptyList(),
    ) = MotionWindow(
        startedAtMs = 0, endedAtMs = 10_000, sampleRateHz = 50.0,
        accel = accel, gyro = gyro, accelSamples = accelSamples,
    )

    @Test fun rmsBajoEsQuieto() {
        val r = classifier.classify(window(axis(0.1), axis(0.05)))
        assertEquals(ActivityState.NO_RECENT_EVIDENCE, r.activityState)
        assertEquals(0.0, r.purposefulMotionConfidence)
        assertEquals("", r.pattern)
    }

    @Test fun rmsFuerteMasGiroCoordinadoMasEntropiaBajaEsMovimientoDeliberado() {
        val r = classifier.classify(window(axis(5.0, entropy = 0.3), axis(4.0)))
        assertEquals(ActivityState.PURPOSEFUL_MOTION, r.activityState)
        assertTrue(r.purposefulMotionConfidence > 0.0)
        assertTrue(r.purposefulMotionConfidence <= 1.0)
    }

    @Test fun rmsFuerteSinGiroCoordinadoNuncaEsDeliberado() {
        val r = classifier.classify(window(axis(5.0, entropy = 0.2), axis(0.1)))
        assertEquals(ActivityState.MOTION_DETECTED, r.activityState)
        assertTrue(r.purposefulMotionConfidence <= 0.4)
        assertEquals("", r.pattern)
    }

    @Test fun entropiaAltaDescartaPatronDeliberadoAunqueRmsYGiroAlcancen() {
        // rms y giro por encima del umbral, pero energía repartida (ruido/vibración
        // ambiental, no la huella de una sacudida con la mano): nunca se marca
        // como intencional sin la firma espectral que lo respalde.
        val r = classifier.classify(window(axis(5.0, entropy = 0.95), axis(4.0)))
        assertEquals(ActivityState.MOTION_DETECTED, r.activityState)
    }

    @Test fun confianzaSiempreEnRangoValido() {
        for (rms in listOf(0.0, 0.3, 0.6, 1.0, 3.0, 5.0, 10.0)) {
            val r = classifier.classify(window(axis(rms, entropy = 0.2), axis(rms)))
            assertTrue(r.purposefulMotionConfidence in 0.0..1.0, "rms=$rms -> ${r.purposefulMotionConfidence}")
        }
    }

    @Test fun patronDeRafagasSePropagaDesdeLasMuestrasCrudas() {
        fun peak(atMs: Long) = listOf(
            MotionSample(atMs - 20, 0.1), MotionSample(atMs, 5.0), MotionSample(atMs + 20, 0.1),
        )
        val burst1 = peak(1000) + peak(1300) + peak(1600)
        val burst2 = peak(2500) + peak(2800) + peak(3100)
        val r = classifier.classify(window(axis(5.0, entropy = 0.2), axis(4.0), accelSamples = burst1 + burst2))
        assertEquals(ActivityState.PURPOSEFUL_MOTION, r.activityState)
        assertEquals("3-3", r.pattern)
    }
}
