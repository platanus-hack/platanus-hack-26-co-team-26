package motion

import co.helius.core.signal.motion.MotionFeatureExtractor
import co.helius.core.signal.motion.MotionSample
import kotlin.math.PI
import kotlin.math.sin
import kotlin.test.Test
import kotlin.test.assertEquals
import kotlin.test.assertNotNull
import kotlin.test.assertNull
import kotlin.test.assertTrue

class MotionFeatureExtractorTest {

    @Test fun sinMuestrasDevuelveFeaturesEnCero() {
        val f = MotionFeatureExtractor.extract(emptyList(), sampleRateHz = 50.0)
        assertEquals(0.0, f.rms)
        assertEquals(0.0, f.energy)
        assertEquals(0.0, f.zeroCrossingRate)
        assertNull(f.dominantFreqHz)
        assertNull(f.spectralEntropy)
    }

    @Test fun senalConstanteTieneZcrCeroYSinEspectro() {
        val samples = (0 until 20).map { MotionSample(it * 20L, 1.0) }
        val f = MotionFeatureExtractor.extract(samples, sampleRateHz = 50.0)
        assertEquals(1.0, f.rms, absoluteTolerance = 1e-9)
        assertEquals(0.0, f.zeroCrossingRate)
    }

    @Test fun senalSinusoidalDetectaLaFrecuenciaDominanteCercaDeLaReal() {
        val fs = 50.0
        val freqHz = 2.0
        val n = (fs * 6).toInt() // 6 s de ventana
        val samples = (0 until n).map { i ->
            val tS = i / fs
            MotionSample((tS * 1000).toLong(), sin(2 * PI * freqHz * tS))
        }
        val f = MotionFeatureExtractor.extract(samples, sampleRateHz = fs)
        val dominant = assertNotNull(f.dominantFreqHz)
        assertTrue(kotlin.math.abs(dominant - freqHz) <= 0.25, "esperado ~${freqHz}Hz, fue $dominant")
        val entropy = assertNotNull(f.spectralEntropy)
        assertTrue(entropy in 0.0..1.0)
        // tono puro -> energía concentrada en pocos bins -> entropía baja
        assertTrue(entropy < 0.7, "entropía esperada baja para un tono puro, fue $entropy")
    }

    @Test fun pocasMuestrasNoIntentaCalcularEspectro() {
        val samples = (0 until 3).map { MotionSample(it * 20L, it.toDouble()) }
        val f = MotionFeatureExtractor.extract(samples, sampleRateHz = 50.0)
        assertNull(f.dominantFreqHz)
        assertNull(f.spectralEntropy)
    }
}
