package co.helius.core.application.ports

import kotlinx.coroutines.flow.Flow

/**
 * Frames y señal PPG cruda. Dueño: Laura + Jorge (app Android + captura AIB).
 * Adaptador real: `co.helius.android.ppg.CameraXPpgEngine` (android/ppg/src/main/kotlin/co/helius/android/ppg/PpgEngine.kt).
 * Adaptador fake: VideoReplayFake (pendiente).
 * TODO(dueño=Laura/Jorge): cablear CameraXPpgEngine detrás de este puerto —
 * ver android/ppg/README.md § Pendiente de integración.
 */
interface PpgCaptureIPort {
    fun captureSession(durationS: Int): Flow<Any /* TODO: PpgFrame, ver core/signal/ppg/Models.kt::FrameSample */>
}

/**
 * Inferencia del modelo AIB (frecuencia de pulso + SQI, nunca "diagnóstico").
 * Dueño: Alex. Adaptador real de apoyo: `co.helius.core.signal.ppg.SafetyFirstClassifier`
 * (siempre disponible, sin ML) y `SignalModelRunner`/`ApprovedEstimatedEcgReconstructor`
 * (LiteRT, cuando exista modelo aprobado) — ver core/signal/ppg/. HeuristicFallback
 * obligatorio: el pipeline debe funcionar sin ML, ver docs/architecture/OVERVIEW.md § AIB.
 */
interface BiomarkerInferencePort {
    suspend fun infer(window: Any /* PpgWindow */): Any /* PulseEstimate con incertidumbre */
}
