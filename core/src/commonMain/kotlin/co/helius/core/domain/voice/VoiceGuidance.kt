package co.helius.core.domain.voice

import co.helius.core.application.ports.PowerMode

/**
 * Movilidad de una persona en modo TRAPPED. No viaja por el protocolo (no
 * necesita cruzar la malla) — es una entrada local, hoy manual (la persona o
 * quien la asiste la fija en la UI). Dueño: Helmut.
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
}

/**
 * Selección pura de qué guion de voz corresponde al estado actual del
 * teléfono. No decide *cuándo* reproducir (eso es política de UI/adaptador
 * Android, requiere pruebas en dispositivo) ni conoce nada de audio — solo
 * mapea (PowerMode, TrappedMobility) -> VoiceGuidanceCase?.
 *
 * `null` es una respuesta válida: no todo estado tiene guion (READY/ALERT en
 * v1) y TrappedMobility.UNKNOWN nunca asume MOBILE por defecto — asumir mal
 * la movilidad de alguien atrapado es peor que no reproducir nada.
 */
object VoiceGuidanceSelector {
    fun select(mode: PowerMode, trappedMobility: TrappedMobility = TrappedMobility.UNKNOWN): VoiceGuidanceCase? {
        return when (mode) {
            PowerMode.RESCUER -> VoiceGuidanceCase.RESCUER_INSTRUCTIONS
            PowerMode.TRAPPED -> when (trappedMobility) {
                TrappedMobility.IMMOBILE -> VoiceGuidanceCase.TRAPPED_CALM
                TrappedMobility.MOBILE -> VoiceGuidanceCase.TRAPPED_ACTIONABLE
                TrappedMobility.UNKNOWN -> null
            }
            PowerMode.READY, PowerMode.ALERT -> null
        }
    }
}
