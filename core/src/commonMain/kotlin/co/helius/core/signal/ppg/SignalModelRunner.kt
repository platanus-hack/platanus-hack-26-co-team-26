package co.helius.core.signal.ppg

import java.security.MessageDigest
import kotlin.math.exp

/** Runtime-neutral port. La capa de infraestructura (`android/inference`) lo implementa con LiteRT. */
interface SignalModelRunner : AutoCloseable {
    fun run(input: FloatArray): EstimatedEcgModelOutputs
}

data class EstimatedEcgModelOutputs(
    val mean: FloatArray,
    val logVariance: FloatArray,
    val quality: Float,
)

data class ModelArtifactManifest(
    val version: String,
    val status: String,
    val sha256: String,
    val preprocessor: String,
    val inputShape: List<Int>,
)

/** Rechaza modelos cuyo hash no coincida — ver services/ppg_model_registry/ y docs/security/THREAT-MODEL.md. */
object ModelArtifactVerifier {
    fun verify(bytes: ByteArray, manifest: ModelArtifactManifest, expectedPreprocessor: String) {
        require(manifest.status == "approved") { "Model is not approved" }
        require(manifest.preprocessor == expectedPreprocessor) { "Preprocessor mismatch" }
        require(manifest.inputShape == listOf(1, 1800, 5)) { "Input shape mismatch" }
        val actual = MessageDigest.getInstance("SHA-256")
            .digest(bytes)
            .joinToString("") { "%02x".format(it) }
        require(actual.equals(manifest.sha256, ignoreCase = true)) { "Model hash mismatch" }
    }
}

class ApprovedEstimatedEcgReconstructor(
    private val runner: SignalModelRunner,
    private val modelVersion: String,
    private val minimumQuality: Float = 0.80f,
    private val maximumMeanUncertainty: Float = 1.50f,
) : EstimatedEcgReconstructor, AutoCloseable {
    override fun reconstruct(ppg: ProcessedPpg): EstimatedEcg {
        val input = EstimatedEcgInputBuilder.fromStandardPpg(ppg)
        val output = runner.run(input)
        require(output.mean.size == EstimatedEcgInputBuilder.TARGET_SAMPLES)
        require(output.logVariance.size == EstimatedEcgInputBuilder.TARGET_SAMPLES)
        val uncertainty = output.logVariance
            .map { exp(0.5f * it) }
            .average()
            .toFloat()
        val status = when {
            output.quality < minimumQuality -> EstimatedEcgStatus.HIGH_UNCERTAINTY
            uncertainty > maximumMeanUncertainty -> EstimatedEcgStatus.HIGH_UNCERTAINTY
            else -> EstimatedEcgStatus.AVAILABLE
        }
        return EstimatedEcg(
            status = status,
            samples = output.mean.takeIf { status == EstimatedEcgStatus.AVAILABLE },
            reconstructionQuality = output.quality,
            meanUncertainty = uncertainty,
            modelVersion = modelVersion,
        )
    }

    override fun close() = runner.close()
}
