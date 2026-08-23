package ppg

import co.helius.core.signal.ppg.Classification
import co.helius.core.signal.ppg.EstimatedEcg
import co.helius.core.signal.ppg.EstimatedEcgStatus
import co.helius.core.signal.ppg.IfoFusionEngine
import co.helius.core.signal.ppg.IfoStatus
import co.helius.core.signal.ppg.PhysiologicalObservation
import co.helius.core.signal.ppg.QualityReason
import co.helius.core.signal.ppg.SignalQuality
import kotlin.test.Test
import kotlin.test.assertEquals
import kotlin.test.assertFalse

class IfoFusionEngineTest {
    @Test fun badSignalCanNeverProduceAvailableObservation() {
        val ifo = IfoFusionEngine(true).evaluate(
            SignalQuality(20, false, setOf(QualityReason.NO_FINGER)),
            Classification(PhysiologicalObservation.HIGH_PULSE_PATTERN, 0.99f, true),
            EstimatedEcg(EstimatedEcgStatus.AVAILABLE, FloatArray(1800), reconstructionQuality = 0.99f),
        )
        assertEquals(IfoStatus.INSUFFICIENT_SIGNAL, ifo.status)
        assertEquals(PhysiologicalObservation.UNRELIABLE_MEASUREMENT, ifo.observation)
        assertFalse(ifo.estimatedEcgContributed)
    }

    @Test fun estimatedEcgIsDisabledByDefault() {
        val ifo = IfoFusionEngine().evaluate(
            SignalQuality(90, true, emptySet()),
            Classification(PhysiologicalObservation.STABLE_PATTERN, 0.8f, true),
            EstimatedEcg(EstimatedEcgStatus.AVAILABLE, FloatArray(1800), reconstructionQuality = 0.99f),
        )
        assertFalse(ifo.estimatedEcgContributed)
    }
}
