package co.sismomesh.core.signal

import kotlin.math.PI
import kotlin.math.sin
import kotlin.test.Test
import kotlin.test.assertEquals
import kotlin.test.assertTrue

class PpgPipelineTest {
    @Test
    fun `detects a stable pulse pattern from a clean synthetic waveform`() {
        val fs = 30.0
        val samples = DoubleArray(30 * 12) { index ->
            0.5 + 0.1 * sin(2 * PI * 1.2 * index / fs)
        }

        val result = PpgPipeline().process(samples, fs)

        assertEquals(72.0, result.bpm, absoluteTolerance = 3.0)
        assertTrue(result.sqi >= 0.8)
        assertEquals("HEURISTIC_FALLBACK", result.method)
        assertEquals(PhysiologicalPattern.STABLE_PATTERN, result.pattern)
    }

    @Test
    fun `rejects too-short or noisy capture safely`() {
        val result = PpgPipeline().process(DoubleArray(20) { if (it % 2 == 0) 1.0 else -1.0 }, 30.0)

        assertEquals(0.0, result.bpm)
        assertTrue(result.sqi < 0.5)
        assertEquals(PhysiologicalPattern.UNRELIABLE_MEASUREMENT, result.pattern)
    }

    @Test
    fun `requests a second verification for a suspicious low reading`() {
        val fs = 30.0
        val low = DoubleArray(30 * 12) { index ->
            0.5 + 0.1 * sin(2 * PI * 0.7 * index / fs)
        }

        val assessment = PpgPipeline().assess(low, fs)

        assertEquals(VerificationStatus.SECOND_VERIFICATION_REQUIRED, assessment.status)
        assertTrue(assessment.message.contains("repite"))
    }

    @Test
    fun `marks repeated anomalous readings as observational only`() {
        val fs = 30.0
        val low = DoubleArray(30 * 12) { index ->
            0.5 + 0.1 * sin(2 * PI * 0.7 * index / fs)
        }

        val assessment = PpgPipeline().assess(low, fs, low)

        assertEquals(VerificationStatus.REPEATED_ANOMALY, assessment.status)
        assertTrue(assessment.message.contains("no es un diagnóstico"))
    }

    @Test
    fun `does not confirm when repeated captures disagree`() {
        val fs = 30.0
        val low = DoubleArray(30 * 12) { index -> 0.5 + 0.1 * sin(2 * PI * 0.7 * index / fs) }
        val normal = DoubleArray(30 * 12) { index -> 0.5 + 0.1 * sin(2 * PI * 1.2 * index / fs) }

        val assessment = PpgPipeline().assess(low, fs, normal)

        assertEquals(VerificationStatus.INCONCLUSIVE_RECHECK, assessment.status)
    }
}
