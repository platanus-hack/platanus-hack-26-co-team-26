package voice

import co.helius.core.application.ports.PowerMode
import co.helius.core.domain.voice.TrappedMobility
import co.helius.core.domain.voice.VoiceGuidanceCase
import co.helius.core.domain.voice.VoiceGuidanceSelector
import kotlin.test.Test
import kotlin.test.assertEquals
import kotlin.test.assertNull

class VoiceGuidanceSelectorTest {

    @Test
    fun rescuerModeSelectsInstructions() {
        assertEquals(
            VoiceGuidanceCase.RESCUER_INSTRUCTIONS,
            VoiceGuidanceSelector.select(PowerMode.RESCUER),
        )
    }

    @Test
    fun trappedImmobileSelectsCalmScript() {
        assertEquals(
            VoiceGuidanceCase.TRAPPED_CALM,
            VoiceGuidanceSelector.select(PowerMode.TRAPPED, TrappedMobility.IMMOBILE),
        )
    }

    @Test
    fun trappedMobileSelectsActionableScript() {
        assertEquals(
            VoiceGuidanceCase.TRAPPED_ACTIONABLE,
            VoiceGuidanceSelector.select(PowerMode.TRAPPED, TrappedMobility.MOBILE),
        )
    }

    @Test
    fun trappedWithUnknownMobilityNeverGuesses() {
        assertNull(VoiceGuidanceSelector.select(PowerMode.TRAPPED, TrappedMobility.UNKNOWN))
        assertNull(VoiceGuidanceSelector.select(PowerMode.TRAPPED))
    }

    @Test
    fun readyAndAlertHaveNoScriptInV1() {
        assertNull(VoiceGuidanceSelector.select(PowerMode.READY))
        assertNull(VoiceGuidanceSelector.select(PowerMode.ALERT))
    }

    @Test
    fun everyCaseAssetIdMatchesVoicePackCatalogNaming() {
        val expected = setOf("rescuer_instructions", "trapped_calm", "trapped_actionable")
        val actual = VoiceGuidanceCase.entries.map { it.assetId }.toSet()
        assertEquals(expected, actual)
    }
}
