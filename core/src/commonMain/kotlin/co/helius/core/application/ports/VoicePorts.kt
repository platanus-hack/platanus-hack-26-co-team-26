package co.helius.core.application.ports

import co.helius.core.domain.voice.VoiceGuidanceCase

/**
 * Reproduce un guion de voz ya embebido en la app (assets/voice/, generado
 * offline por tools/voice_pack/ — ver docs/voice/VOICE-GUIDANCE.md). Nunca
 * llama a una API en tiempo real: el `VoiceGuidanceCase` ya trae el
 * `assetId` del archivo local a reproducir, este puerto solo lo reproduce.
 *
 * Dueño: Helmut (selección, `VoiceGuidanceSelector`). Adaptadores: quien
 * implemente la reproducción en Android (MediaPlayer/ExoPlayer, Laura/Jorge
 * — requiere pruebas en dispositivo, ver docs/validation/PHONE-READINESS.md,
 * no implementado en esta capa), MemoryFake para tests.
 */
interface VoiceGuidancePlaybackPort {
    suspend fun play(case: VoiceGuidanceCase)
    suspend fun stop()
    fun isPlaying(): Boolean
}
