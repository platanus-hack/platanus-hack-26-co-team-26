package co.sismomesh.core.application.ports

import kotlinx.coroutines.flow.Flow
import co.sismomesh.core.signal.PulseEstimate

/**
 * Frames y señal PPG cruda. Dueño: Laura + Jorge (app Android + captura AIB).
 * Adaptadores: CameraXAdapter, VideoReplayFake.
 */
data class PpgFrame(
    val timestampEpochMillis: Long,
    val red: Double,
    val green: Double,
    val blue: Double,
    val opticalContactScore: Double,
)

data class PpgWindow(val frames: List<PpgFrame>, val sampleRateHz: Double)

interface PpgCapturePort {
    fun captureSession(durationS: Int): Flow<PpgFrame>
}

/**
 * Inferencia del modelo AIB (frecuencia de pulso + SQI, nunca "diagnóstico").
 * Dueño: Alex. Adaptadores: LiteRtAdapter, HeuristicFallback (obligatorio: el pipeline
 * debe funcionar sin ML, ver docs/architecture/OVERVIEW.md § AIB).
 */
interface BiomarkerInferencePort {
    suspend fun infer(window: PpgWindow): PulseEstimate
}
