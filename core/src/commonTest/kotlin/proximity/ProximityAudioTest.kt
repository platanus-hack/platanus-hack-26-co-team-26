package proximity

import co.helius.core.domain.proximity.ProximityAlert
import co.helius.core.domain.proximity.ProximityAlertReducer
import co.helius.core.domain.proximity.ProximityAudioMapper
import co.helius.core.domain.vo.PeerId
import kotlin.test.Test
import kotlin.test.assertEquals
import kotlin.test.assertFalse
import kotlin.test.assertTrue

class ProximityAudioMapperTest {

    @Test
    fun beepsFasterAsSignalGetsStronger() {
        val far = ProximityAudioMapper.beepIntervalMs(-90)
        val mid = ProximityAudioMapper.beepIntervalMs(-70)
        val near = ProximityAudioMapper.beepIntervalMs(-45)

        assertTrue(far > mid, "far=$far debería ser más lento que mid=$mid")
        assertTrue(mid > near, "mid=$mid debería ser más lento que near=$near")
    }

    @Test
    fun neverExceedsHumanPerceivableBounds() {
        assertEquals(1_500L, ProximityAudioMapper.beepIntervalMs(-150)) // mucho más lejos que el rango
        assertEquals(120L, ProximityAudioMapper.beepIntervalMs(-10))    // mucho más cerca que el rango
    }

    @Test
    fun operativeRangeThreshold() {
        assertTrue(ProximityAudioMapper.isOperativeRange(-40))
        assertFalse(ProximityAudioMapper.isOperativeRange(-80))
    }
}

class ProximityAlertReducerTest {

    @Test
    fun firstSightingOfAPeerChimesOnceThenJustBeeps() {
        val reducer = ProximityAlertReducer()
        val peer = PeerId("aa:bb:cc")

        val first = reducer.onSighting(peer, -60)
        assertEquals(listOf(ProximityAlert.NewPeerChime, ProximityAlert.Beep(ProximityAudioMapper.beepIntervalMs(-60))), first)

        val second = reducer.onSighting(peer, -50)
        assertEquals(listOf(ProximityAlert.Beep(ProximityAudioMapper.beepIntervalMs(-50))), second)
    }

    @Test
    fun differentPeersEachGetTheirOwnChime() {
        val reducer = ProximityAlertReducer()
        val a = reducer.onSighting(PeerId("a"), -60)
        val b = reducer.onSighting(PeerId("b"), -60)

        assertTrue(a.contains(ProximityAlert.NewPeerChime))
        assertTrue(b.contains(ProximityAlert.NewPeerChime))
    }

    @Test
    fun resetForgetsPreviouslyChimedPeers() {
        val reducer = ProximityAlertReducer()
        val peer = PeerId("aa:bb:cc")
        reducer.onSighting(peer, -60)

        reducer.reset()

        val afterReset = reducer.onSighting(peer, -60)
        assertTrue(afterReset.contains(ProximityAlert.NewPeerChime))
    }
}
