package emergency

import co.helius.core.emergency.AssistanceConfirmation
import co.helius.core.emergency.EmergencyEvent
import co.helius.core.emergency.EmergencyIncident
import co.helius.core.emergency.HeliosOperationalMode
import co.helius.core.emergency.HeliosStateMachine
import co.helius.core.emergency.IncidentSource
import kotlin.test.Test
import kotlin.test.assertEquals
import kotlin.test.assertIs

class OperationalModeTest {
    private val machine = HeliosStateMachine(alertWindowMs = 10, responseWindowMs = 30)
    private val incident = EmergencyIncident("i-1", IncidentSource.DEMO, 100, "Evento simulado")

    @Test
    fun demoAlertMovesToQuestionAfterAlertWindow() {
        val alert = machine.reduce(HeliosOperationalMode.Normal, EmergencyEvent.EarthquakeDetected(incident))
        val question = machine.reduce(alert, EmergencyEvent.AlertElapsed(110))
        val awaiting = assertIs<HeliosOperationalMode.AwaitingResponse>(question)
        assertEquals(140, awaiting.deadlineMs)
    }

    @Test
    fun safeAnswerEntersSupportWithoutCallingUserResponder() {
        val awaiting = HeliosOperationalMode.AwaitingResponse(incident, 110, 140)
        assertIs<HeliosOperationalMode.EmergencySupport>(machine.reduce(awaiting, EmergencyEvent.UserSafe))
    }

    @Test
    fun timeoutIsUnconfirmedAndNeedsExplicitConfirmation() {
        val awaiting = HeliosOperationalMode.AwaitingResponse(incident, 110, 140)
        val noResponse = machine.reduce(awaiting, EmergencyEvent.ResponseTimeout)
        val assistance = assertIs<HeliosOperationalMode.AssistanceRequired>(noResponse)
        assertEquals(AssistanceConfirmation.UNCONFIRMED_NO_RESPONSE, assistance.confirmation)
    }

    @Test
    fun manualSosWorksFromNormalMode() {
        val assistance = machine.reduce(HeliosOperationalMode.Normal, EmergencyEvent.ManualSos(incident))
        assertIs<HeliosOperationalMode.AssistanceRequired>(assistance)
    }
}
