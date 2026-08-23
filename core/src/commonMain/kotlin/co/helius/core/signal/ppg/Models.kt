package co.helius.core.signal.ppg

/**
 * Vocabulario compartido del módulo PPG entre `core/signal/ppg` (DSP puro, Kotlin,
 * testeable en JVM sin teléfono) y `android/ppg` (captura con CameraX). Integrado
 * desde el blueprint de Laura — ver docs/ppg/README.md para el origen y el mapeo
 * de rutas. Nombre de referencia original del indicador: IFO (Indicador
 * Fisiológico Orientativo); en el resto del proyecto el módulo se llama AIB
 * (Análisis e Interpretación de Biomarcadores) — ver docs/glossary.md.
 */

data class PpgConfig(
    val stabilizationMs: Long = 1_500,
    val acquisitionSeconds: Int = 15,
    val sessionTimeoutSeconds: Int = 25,
    val targetSampleRateHz: Int = 30,
    val minQuality: Int = 70,
    val roiFraction: Float = 0.42f,
    val pixelStep: Int = 2,
)

data class FrameSample(
    val timestampNs: Long,
    val red: Float,
    val green: Float,
    val blue: Float,
    val lumaStd: Float,
    val saturatedFraction: Float,
    val motion: Float,
)

enum class QualityReason {
    NO_FINGER, SATURATED, LOW_PULSATILITY, MOTION, FRAME_GAPS,
    INSUFFICIENT_DURATION, TOO_MUCH_PRESSURE, THERMAL_LIMIT, INTERNAL_ERROR
}

enum class PpgErrorCode {
    CAMERA_PERMISSION_DENIED,
    BACK_CAMERA_UNAVAILABLE,
    TORCH_UNAVAILABLE,
    CAMERA_BIND_FAILED,
    SESSION_TIMEOUT,
    THERMAL_LIMIT,
    MODEL_UNAVAILABLE,
    MODEL_HASH_MISMATCH,
    MODEL_INFERENCE_FAILED,
    INTERNAL_PROCESSING_ERROR,
}

class PpgEngineException(
    val errorCode: PpgErrorCode,
    message: String,
    cause: Throwable? = null,
) : RuntimeException(message, cause)

/**
 * Salidas permitidas — ver README raíz § Restricciones no negociables y
 * docs/glossary.md. Prohibido agregar HERIDO, SHOCK, ANSIEDAD, prioridad clínica
 * o diagnóstico cardíaco a este enum.
 */
enum class PhysiologicalObservation(val code: Int) {
    STABLE_PATTERN(0), HIGH_PULSE_PATTERN(1), LOW_PULSE_PATTERN(2),
    IRREGULAR_PULSE_PATTERN(3), REDUCED_PERFUSION_OR_CONTACT(4),
    PHYSIOLOGICAL_ACTIVATION_PATTERN(5), UNRELIABLE_MEASUREMENT(255)
}

data class SignalQuality(
    val score: Int,
    val accepted: Boolean,
    val reasons: Set<QualityReason>,
)

data class SignalFeatures(
    val pulseBpm: Float?,
    val medianIbiMs: Float?,
    val shortRmssdMs: Float?,
    val irregularity: Float,
    val perfusionProxy: Float,
)

data class ProcessedPpg(
    val sampleRateHz: Int,
    val normalized: FloatArray,
    val d1: FloatArray,
    val d2: FloatArray,
    val motion: FloatArray,
    val features: SignalFeatures,
)

data class Classification(
    val observation: PhysiologicalObservation,
    val confidence: Float?,
    val approvedAiUsed: Boolean,
)

enum class IfoStatus {
    OBSERVATION_AVAILABLE,
    MARKED_PATTERN_OBSERVED,
    REPEAT_MEASUREMENT,
    INSUFFICIENT_SIGNAL,
}

enum class EvidenceSource { CAMERA_PPG, MOTION_SENSOR, ESTIMATED_ECG }

data class IfoEvidence(
    val source: EvidenceSource,
    val code: String,
    val confidence: Float?,
)

data class IfoResult(
    val status: IfoStatus,
    val observation: PhysiologicalObservation,
    val evidence: List<IfoEvidence>,
    val estimatedEcgContributed: Boolean,
)

data class ComponentVersions(
    val module: String = "1.0.0",
    val preprocessor: String = "ppg-pre-v1",
    val model: String? = null,
    val estimatedEcgModel: String? = null,
)

enum class EstimatedEcgStatus { AVAILABLE, UNAVAILABLE, QUALITY_REJECTED, HIGH_UNCERTAINTY }

/** `estimated_ecg` — nunca se confunde con un ECG medido. Ver docs/ppg/PPG_TO_ECG.md. */
data class EstimatedEcg(
    val status: EstimatedEcgStatus,
    val samples: FloatArray? = null,
    val sampleRateHz: Int = 120,
    val reconstructionQuality: Float? = null,
    val meanUncertainty: Float? = null,
    val modelVersion: String? = null,
)

data class PpgResult(
    val sessionId: Long,
    val quality: SignalQuality,
    val features: SignalFeatures?,
    val classification: Classification,
    val estimatedEcg: EstimatedEcg,
    val ifo: IfoResult,
    val packet: ByteArray,
    val versions: ComponentVersions,
)

sealed interface PpgSessionState {
    data object Idle : PpgSessionState
    data object Preparing : PpgSessionState
    data object Stabilizing : PpgSessionState
    data object Acquiring : PpgSessionState
    data object Processing : PpgSessionState
    data class Completed(val result: PpgResult) : PpgSessionState
    data class QualityRejected(val quality: SignalQuality) : PpgSessionState
    data class Failed(
        val message: String,
        val code: PpgErrorCode = PpgErrorCode.INTERNAL_PROCESSING_ERROR,
    ) : PpgSessionState
    data object Cancelled : PpgSessionState
}

data class PpgProgress(
    val fraction: Float = 0f,
    val liveQualityHint: QualityReason? = null,
)
