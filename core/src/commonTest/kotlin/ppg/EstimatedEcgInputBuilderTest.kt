package ppg

import co.helius.core.signal.ppg.EstimatedEcgInputBuilder
import co.helius.core.signal.ppg.ProcessedPpg
import co.helius.core.signal.ppg.SignalFeatures
import kotlin.test.Test
import kotlin.test.assertEquals

class EstimatedEcgInputBuilderTest {
    @Test fun standardInputHasFixedShapeAndBandwidthFlag() {
        val n = 450
        val ppg = ProcessedPpg(
            30,
            FloatArray(n) { it / 450f },
            FloatArray(n),
            FloatArray(n),
            FloatArray(n),
            SignalFeatures(70f, 850f, null, 0.03f, 0.05f),
        )
        val input = EstimatedEcgInputBuilder.fromStandardPpg(ppg)
        assertEquals(1800 * 5, input.size)
        for (i in 0 until 1800) assertEquals(0.25f, input[i * 5 + 4])
    }
}
