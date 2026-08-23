package co.helius.core.application.ports

import kotlinx.coroutines.flow.Flow
import co.helius.core.signal.ppg.PulseEstimate

/**
 * Frames y señal PPG cruda. Dueño: Laura + Jorge (app Android + captura AIB).
 * Adaptador real: `co.helius.android.ppg.CameraPpgCaptureSource`
 * (android/ppg/src/main/kotlin/co/helius/android/ppg/CameraPpgCaptureSource.kt) —
 * implementación directa de este puerto (frame a frame, sin DSP). Para la
 * orquestación completa de sesión (estabilización, DSP, clasificación,
 * paquete de 28B) ver `CameraXPpgEngine` en el mismo directorio
 * (PpgEngine.kt) — no implementa este puerto, resuelve un contrato más rico
 * (`PpgSessionState`/`PpgResult`).
 * Adaptador fake: VideoReplayFake (pendiente).
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

/** Compatibility alias for older application use cases; one canonical capture port. */
typealias PpgCaptureIPort = PpgCapturePort

/**
 * Inferencia del modelo AIB (frecuencia de pulso + SQI, nunca "diagnóstico").
 * Dueño: Alex. Adaptador real de apoyo: `co.helius.core.signal.ppg.SafetyFirstClassifier`
 * (siempre disponible, sin ML) y `SignalModelRunner`/`ApprovedEstimatedEcgReconstructor`
 * (LiteRT, cuando exista modelo aprobado) — ver core/signal/ppg/. HeuristicFallback
 * obligatorio: el pipeline debe funcionar sin ML, ver docs/architecture/OVERVIEW.md § AIB.
 */
interface BiomarkerInferencePort {
    suspend fun infer(window: PpgWindow): PulseEstimate
}
