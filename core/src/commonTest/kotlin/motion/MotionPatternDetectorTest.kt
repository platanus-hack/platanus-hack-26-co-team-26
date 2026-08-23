package motion

import co.helius.core.signal.motion.MotionPatternDetector
import co.helius.core.signal.motion.MotionSample
import kotlin.test.Test
import kotlin.test.assertEquals

class MotionPatternDetectorTest {

    private fun peakSample(atMs: Long) = listOf(
        MotionSample(atMs - 20, 0.5),
        MotionSample(atMs, 5.0),
        MotionSample(atMs + 20, 0.5),
    )

    @Test fun menosDeDosPicosNoTienePatron() {
        val samples = peakSample(1000)
        assertEquals("", MotionPatternDetector.detect(samples, threshold = 2.0))
    }

    @Test fun tresGolpesSeguidosSonUnaSolaRafaga() {
        val samples = peakSample(1000) + peakSample(1300) + peakSample(1600)
        assertEquals("3", MotionPatternDetector.detect(samples, threshold = 2.0))
    }

    @Test fun patronSosTresPausaTres() {
        // tres golpes cada 300ms, pausa de 900ms (> BURST_GAP_MS), tres golpes más
        val burst1 = peakSample(1000) + peakSample(1300) + peakSample(1600)
        val burst2 = peakSample(2500) + peakSample(2800) + peakSample(3100)
        assertEquals("3-3", MotionPatternDetector.detect(burst1 + burst2, threshold = 2.0))
    }

    @Test fun picosDemasiadoJuntosSeCuentanUnaSolaVez() {
        // separación de 50ms, por debajo de MIN_PEAK_GAP_MS (250ms)
        val samples = peakSample(1000) + peakSample(1050) + peakSample(1100)
        assertEquals("", MotionPatternDetector.detect(samples, threshold = 2.0))
    }

    @Test fun sinPicosPorEncimaDelUmbralNoHayPatron() {
        val samples = listOf(
            MotionSample(0, 0.1), MotionSample(20, 0.1), MotionSample(40, 0.1),
        )
        assertEquals("", MotionPatternDetector.detect(samples, threshold = 2.0))
    }
}
