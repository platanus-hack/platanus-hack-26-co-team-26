package co.helius.core.signal.ppg

interface EstimatedEcgReconstructor {
    fun reconstruct(ppg: ProcessedPpg): EstimatedEcg
}

/** Safe default until an approved, hash-verified LiteRT model is bundled. */
class UnavailableEstimatedEcgReconstructor : EstimatedEcgReconstructor {
    override fun reconstruct(ppg: ProcessedPpg) = EstimatedEcg(EstimatedEcgStatus.UNAVAILABLE)
}

/** Builds the fixed 120 Hz input. Interpolation does not claim additional bandwidth. */
object EstimatedEcgInputBuilder {
    const val TARGET_HZ = 120
    const val TARGET_SAMPLES = 1800
    const val CHANNELS = 5

    fun fromStandardPpg(ppg: ProcessedPpg): FloatArray {
        val out = FloatArray(TARGET_SAMPLES * CHANNELS)
        for (i in 0 until TARGET_SAMPLES) {
            val position = i.toFloat() * ppg.sampleRateHz / TARGET_HZ
            val base = position.toInt().coerceIn(0, ppg.normalized.lastIndex)
            val next = (base + 1).coerceAtMost(ppg.normalized.lastIndex)
            val w = position - base
            fun lerp(x: FloatArray) = x[base] + w * (x[next] - x[base])
            val offset = i * CHANNELS
            out[offset] = lerp(ppg.normalized)
            out[offset + 1] = lerp(ppg.d1)
            out[offset + 2] = lerp(ppg.d2)
            out[offset + 3] = lerp(ppg.motion)
            out[offset + 4] = 0.25f // low temporal-bandwidth standard camera mode
        }
        return out
    }
}
