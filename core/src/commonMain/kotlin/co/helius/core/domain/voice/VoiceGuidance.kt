package co.helius.core.domain.voice

import co.helius.core.application.ports.PowerMode

/**
 * Movilidad de una persona en modo TRAPPED. No viaja por el protocolo (no
 * necesita cruzar la malla) — es una entrada local: empieza en UNKNOWN y se
 * resuelve cuando la persona responde al guion [VoiceGuidanceCase.MOBILITY_CHECK]
 * (moviéndose o no) — no es una entrada manual en un formulario, es el
 * resultado de esa prueba. Dueño: Helmut.
 */
enum class TrappedMobility { MOBILE, IMMOBILE, UNKNOWN }

/**
 * Casos del catálogo de voz offline. `assetId` debe coincidir byte a byte
 * con `case_id` en tools/voice_pack/catalog.py y con el nombre de archivo en
 * assets/voice/<locale>/<assetId>.mp3 — ver docs/voice/VOICE-GUIDANCE.md.
 */
enum class VoiceGuidanceCase(val assetId: String) {
    RESCUER_INSTRUCTIONS("rescuer_instructions"),
    TRAPPED_CALM("trapped_calm"),
    TRAPPED_ACTIONABLE("trapped_actionable"),
    /** Movilidad todavía desconocida: pide un movimiento pequeño y prudente en
     * vez de quedarse en silencio. La respuesta (llega o no evidencia de
     * movimiento por [co.helius.core.application.ports.MotionPort]) es lo que
     * resuelve [TrappedMobility] de UNKNOWN a MOBILE/IMMOBILE. */
    MOBILITY_CHECK("mobility_check"),
    /** Guía para colocar el dedo sobre cámara+flash antes de una sesión PPG.
     * Disparador directo del flujo de captura (android/ppg), no de
     * [VoiceGuidanceSelector.select] — cualquier persona iniciando una
     * sesión lo necesita, sin importar su PowerMode. */
    PPG_FINGER_PLACEMENT("ppg_finger_placement"),
    /** Recordatorio corto y repetible del patrón de ráfagas "3-3" que
     * [co.helius.core.signal.motion.MotionPatternDetector] reconoce. Distinto
     * de TRAPPED_ACTIONABLE (que ya lo menciona una vez dentro de un guion
     * más largo) — este es para repetir cada tanto, ver
     * [VoiceGuidanceSelector.reminder]. */
    GYRO_SOS_PATTERN("gyro_sos_pattern"),
}

/**
 * Selección pura de qué guion de voz corresponde al estado actual del
 * teléfono. No decide *cuándo* reproducir (eso es política de UI/adaptador
 * Android, requiere pruebas en dispositivo) ni conoce nada de audio — solo
 * mapea (PowerMode, TrappedMobility) -> VoiceGuidanceCase?.
 */
object VoiceGuidanceSelector {
    /** Qué reproducir una vez, al entrar a un estado. */
    fun select(mode: PowerMode, trappedMobility: TrappedMobility = TrappedMobility.UNKNOWN): VoiceGuidanceCase? {
        return when (mode) {
            PowerMode.RESCUER -> VoiceGuidanceCase.RESCUER_INSTRUCTIONS
            PowerMode.TRAPPED -> when (trappedMobility) {
                TrappedMobility.IMMOBILE -> VoiceGuidanceCase.TRAPPED_CALM
                TrappedMobility.MOBILE -> VoiceGuidanceCase.TRAPPED_ACTIONABLE
                // Antes esto devolvía null ("nunca asumir movilidad"). Sigue sin
                // asumirla -- en vez de callar, pregunta: MOBILITY_CHECK es lo que
                // permite pasar de UNKNOWN a un valor real.
                TrappedMobility.UNKNOWN -> VoiceGuidanceCase.MOBILITY_CHECK
            }
            PowerMode.READY, PowerMode.ALERT -> null
        }
    }

    /**
     * Qué repetir periódicamente mientras se mantiene un estado (a diferencia
     * de [select], que es solo para la entrada). El intervalo de repetición
     * es decisión del llamador (Android, requiere pruebas en dispositivo) --
     * esta función solo dice *qué* guion, nunca *cada cuánto*.
     */
    fun reminder(mode: PowerMode, trappedMobility: TrappedMobility): VoiceGuidanceCase? {
        return if (mode == PowerMode.TRAPPED && trappedMobility == TrappedMobility.MOBILE) {
            VoiceGuidanceCase.GYRO_SOS_PATTERN
        } else null
    }
}
