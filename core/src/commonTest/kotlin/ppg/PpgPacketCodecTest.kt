package ppg

import co.helius.core.signal.ppg.Classification
import co.helius.core.signal.ppg.PhysiologicalObservation
import co.helius.core.signal.ppg.PpgPacketCodec
import co.helius.core.signal.ppg.SignalFeatures
import co.helius.core.signal.ppg.SignalQuality
import kotlin.test.Test
import kotlin.test.assertEquals

class PpgPacketCodecTest {
    @Test fun packetHasExpectedHeaderAndLength() {
        val quality = SignalQuality(88, true, emptySet())
        val features = SignalFeatures(72f, 833f, 31f, 0.04f, 0.05f)
        val classification = Classification(PhysiologicalObservation.STABLE_PATTERN, null, false)
        val packet = PpgPacketCodec.encode(7L, 10L, quality, features, classification)
        assertEquals(28, packet.size)
        assertEquals(0x50, packet[0].toInt() and 0xff)
        assertEquals(0x47, packet[1].toInt() and 0xff)
        assertEquals(1, packet[2].toInt() and 0xff)
    }
}
