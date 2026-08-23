package co.sismomesh.core.application.ports

import kotlinx.coroutines.flow.Flow

/**
 * Frames y señal PPG cruda. Dueño: Laura + Jorge (app Android + captura AIB).
 * Adaptadores: CameraXAdapter, VideoReplayFake.
 */
interface PpgCaptureIPort {
    fun captureSession(durationS: Int): Flow<Any /* TODO: PpgFrame, ver core/signal */>
}

/**
 * Inferencia del modelo AIB (frecuencia de pulso + SQI, nunca "diagnóstico").
 * Dueño: Alex. Adaptadores: LiteRtAdapter, HeuristicFallback (obligatorio: el pipeline
 * debe funcionar sin ML, ver docs/architecture/OVERVIEW.md § AIB).
 */
interface BiomarkerInferencePort {
    suspend fun infer(window: Any /* PpgWindow */): Any /* PulseEstimate con incertidumbre */
}
