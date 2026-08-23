package co.helius.core.application.ports

import kotlinx.coroutines.flow.Flow
import co.sismomesh.core.signal.PulseEstimate

/**
 * Frames y señal PPG cruda. Dueño: Laura + Jorge (app Android + captura AIB).
 * Adaptador real: `co.helius.android.ppg.CameraXPpgEngine` (android/ppg/src/main/kotlin/co/helius/android/ppg/PpgEngine.kt).
 * Adaptador fake: VideoReplayFake (pendiente).
 * TODO(dueño=Laura/Jorge): cablear CameraXPpgEngine detrás de este puerto —
 * ver android/ppg/README.md § Pendiente de integración.
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
