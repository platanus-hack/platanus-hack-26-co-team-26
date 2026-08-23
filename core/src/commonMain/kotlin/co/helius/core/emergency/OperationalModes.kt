package co.helius.core.emergency

import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow

/** Fuente de un incidente; la UI debe distinguir demo de datos operativos. */
enum class IncidentSource { REAL_ALERT, MANUAL_SOS, DEMO }

data class EmergencyIncident(
    val id: String,
    val source: IncidentSource,
    val detectedAtMs: Long,
    val summary: String,
)

enum class AssistanceConfirmation { CONFIRMED_BY_USER, UNCONFIRMED_NO_RESPONSE }

/**
 * Máquina canónica: Normal → apoyo o asistencia requerida. Las fases de alerta
 * y espera son transiciones temporales, no pantallas independientes.
 */
sealed interface HeliosOperationalMode {
    data object Normal : HeliosOperationalMode
    data class AlertDisplay(val incident: EmergencyIncident) : HeliosOperationalMode
    data class AwaitingResponse(
        val incident: EmergencyIncident,
        val askedAtMs: Long,
        val deadlineMs: Long,
    ) : HeliosOperationalMode
    data class EmergencySupport(val incident: EmergencyIncident) : HeliosOperationalMode
    data class AssistanceRequired(
        val incident: EmergencyIncident,
        val confirmation: AssistanceConfirmation,
    ) : HeliosOperationalMode
}

sealed interface EmergencyEvent {
    data class EarthquakeDetected(val incident: EmergencyIncident) : EmergencyEvent
    data class ManualSos(val incident: EmergencyIncident) : EmergencyEvent
    data class AlertElapsed(val atMs: Long) : EmergencyEvent
    data object UserSafe : EmergencyEvent
    data object UserNeedsHelp : EmergencyEvent
    data object ResponseTimeout : EmergencyEvent
    data object Resolve : EmergencyEvent
}

/** Reductor puro y determinista; no conoce Android, sensores ni navegación. */
class HeliosStateMachine(
    private val alertWindowMs: Long = 10_000L,
    private val responseWindowMs: Long = 30_000L,
) {
    fun reduce(mode: HeliosOperationalMode, event: EmergencyEvent): HeliosOperationalMode = when (event) {
        is EmergencyEvent.EarthquakeDetected -> if (mode is HeliosOperationalMode.Normal) {
            HeliosOperationalMode.AlertDisplay(event.incident)
        } else mode
        is EmergencyEvent.ManualSos -> HeliosOperationalMode.AssistanceRequired(
            event.incident,
            AssistanceConfirmation.CONFIRMED_BY_USER,
        )
        is EmergencyEvent.AlertElapsed -> when (mode) {
            is HeliosOperationalMode.AlertDisplay -> {
                val askedAt = mode.incident.detectedAtMs + alertWindowMs
                if (event.atMs >= askedAt) HeliosOperationalMode.AwaitingResponse(
                    mode.incident,
                    askedAt,
                    askedAt + responseWindowMs,
                ) else mode
            }
            else -> mode
        }
        EmergencyEvent.UserSafe -> when (mode) {
            is HeliosOperationalMode.AwaitingResponse -> HeliosOperationalMode.EmergencySupport(mode.incident)
            is HeliosOperationalMode.AssistanceRequired -> HeliosOperationalMode.EmergencySupport(mode.incident)
            else -> mode
        }
        EmergencyEvent.UserNeedsHelp -> when (mode) {
            is HeliosOperationalMode.AwaitingResponse -> confirmed(mode.incident)
            is HeliosOperationalMode.AssistanceRequired -> confirmed(mode.incident)
            is HeliosOperationalMode.EmergencySupport -> confirmed(mode.incident)
            else -> mode
        }
        EmergencyEvent.ResponseTimeout -> when (mode) {
            is HeliosOperationalMode.AwaitingResponse -> HeliosOperationalMode.AssistanceRequired(
                mode.incident,
                AssistanceConfirmation.UNCONFIRMED_NO_RESPONSE,
            )
            else -> mode
        }
        EmergencyEvent.Resolve -> if (mode is HeliosOperationalMode.Normal) mode else HeliosOperationalMode.Normal
    }

    private fun confirmed(incident: EmergencyIncident) = HeliosOperationalMode.AssistanceRequired(
        incident,
        AssistanceConfirmation.CONFIRMED_BY_USER,
    )
}

/** Fachada observable para el shell Android y futuros ViewModels. */
class EmergencyController(
    private val machine: HeliosStateMachine = HeliosStateMachine(),
    initialMode: HeliosOperationalMode = HeliosOperationalMode.Normal,
) {
    private val _mode = MutableStateFlow(initialMode)
    val mode: StateFlow<HeliosOperationalMode> = _mode.asStateFlow()

    fun dispatch(event: EmergencyEvent): HeliosOperationalMode {
        _mode.value = machine.reduce(_mode.value, event)
        return _mode.value
    }
}
