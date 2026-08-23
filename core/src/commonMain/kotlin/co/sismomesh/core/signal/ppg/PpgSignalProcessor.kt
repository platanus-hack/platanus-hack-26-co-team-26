package co.sismomesh.core.signal.ppg

import kotlin.math.PI
import kotlin.math.abs
import kotlin.math.exp
import kotlin.math.max
import kotlin.math.sqrt

/** Reference processor. Freeze coefficients against Python golden fixtures before release. */
class PpgSignalProcessor {
    fun process(samples: List<FrameSample>, sampleRateHz: Int = 30): ProcessedPpg? {
        if (samples.size < sampleRateHz * 5) return null
        val sorted = samples.sortedBy { it.timestampNs }
        val duration = (sorted.last().timestampNs - sorted.first().timestampNs) / 1e9
        if (duration < 5.0) return null
        val n = (duration * sampleRateHz).toInt().coerceAtMost(sampleRateHz * 30)
        val red = interpolate(sorted, n, sampleRateHz) { it.red }
        val motion = interpolate(sorted, n, sampleRateHz) { it.motion }
        val detrended = movingAverageDetrend(red, sampleRateHz)
        val filtered = zeroPhaseLowCostFilter(detrended, sampleRateHz)
        val normalized = robustNormalize(filtered)
        val d1 = derivative(normalized)
        val d2 = derivative(d1)
        val peaks = detectPeaks(normalized, sampleRateHz)
        val ibis = peaks.zipWithNext().map { (a, b) -> (b - a) * 1000f / sampleRateHz }
        val medianIbi = median(ibis)
        val bpm = medianIbi?.takeIf { it > 0f }?.let { 60_000f / it }
        val rmssd = if (ibis.size >= 3) sqrt(ibis.zipWithNext().map { (a, b) ->
            val d = b - a; d * d
        }.average()).toFloat() else null
        val meanIbi = if (ibis.isNotEmpty()) ibis.average().toFloat() else null
        val irregularity = if (meanIbi != null && meanIbi > 0 && ibis.size >= 3) {
            standardDeviation(ibis) / meanIbi
        } else 1f
        val perfusion = standardDeviation(detrended.toList()) / max(1f, red.average().toFloat())
        return ProcessedPpg(sampleRateHz, normalized, d1, d2, motion, SignalFeatures(
            bpm, medianIbi, rmssd, irregularity, perfusion
        ))
    }

    private fun interpolate(s: List<FrameSample>, n: Int, fs: Int, get: (FrameSample) -> Float): FloatArray {
        val out = FloatArray(n)
        val t0 = s.first().timestampNs
        var j = 0
        for (i in 0 until n) {
            val target = t0 + (i * 1_000_000_000L / fs)
            while (j + 1 < s.size && s[j + 1].timestampNs < target) j++
            if (j + 1 >= s.size) out[i] = get(s.last()) else {
                val a = s[j]; val b = s[j + 1]
                val span = (b.timestampNs - a.timestampNs).coerceAtLeast(1)
                val w = (target - a.timestampNs).toFloat() / span
                out[i] = get(a) + w.coerceIn(0f, 1f) * (get(b) - get(a))
            }
        }
        return out
    }

    private fun movingAverageDetrend(x: FloatArray, fs: Int): FloatArray {
        val radius = fs.coerceAtLeast(3)
        val prefix = DoubleArray(x.size + 1)
        for (i in x.indices) prefix[i + 1] = prefix[i] + x[i]
        return FloatArray(x.size) { i ->
            val lo = (i - radius).coerceAtLeast(0)
            val hi = (i + radius + 1).coerceAtMost(x.size)
            x[i] - ((prefix[hi] - prefix[lo]) / (hi - lo)).toFloat()
        }
    }

    // Two forward/backward exponential stages: cheap baseline, not a clinical filter.
    // TODO(dueño=Alex/Laura, ver docs/ppg/ARCHITECTURE.md §5): sustituir por
    // Butterworth/SOS 0.5-4 Hz manteniendo equivalencia numérica con Python antes
    // de validación final.
    private fun zeroPhaseLowCostFilter(x: FloatArray, fs: Int): FloatArray {
        fun pass(input: FloatArray): FloatArray {
            val out = FloatArray(input.size)
            val alpha = (1.0 - exp(-2.0 * PI * 4.0 / fs)).toFloat().coerceIn(0.05f, 0.95f)
            for (i in input.indices) out[i] = if (i == 0) input[i] else out[i - 1] + alpha * (input[i] - out[i - 1])
            return out
        }
        val fwd = pass(x)
        return pass(fwd.reversedArray()).reversedArray()
    }

    private fun robustNormalize(x: FloatArray): FloatArray {
        val med = median(x.toList()) ?: 0f
        val mad = median(x.map { abs(it - med) })?.coerceAtLeast(1e-6f) ?: 1f
        return FloatArray(x.size) { ((x[it] - med) / (1.4826f * mad)).coerceIn(-8f, 8f) }
    }

    private fun derivative(x: FloatArray) = FloatArray(x.size) { i -> if (i == 0) 0f else x[i] - x[i - 1] }

    private fun detectPeaks(x: FloatArray, fs: Int): List<Int> {
        val candidates = mutableListOf<Int>()
        val minDistance = (fs * 60f / 220f).toInt().coerceAtLeast(3)
        for (i in 1 until x.lastIndex) if (x[i] > x[i - 1] && x[i] >= x[i + 1] && x[i] > 0.15f) {
            if (candidates.isEmpty() || i - candidates.last() >= minDistance) candidates += i
            else if (x[i] > x[candidates.last()]) candidates[candidates.lastIndex] = i
        }
        return candidates
    }

    private fun median(x: List<Float>): Float? {
        if (x.isEmpty()) return null
        val s = x.sorted(); val m = s.size / 2
        return if (s.size % 2 == 1) s[m] else (s[m - 1] + s[m]) / 2f
    }

    private fun standardDeviation(x: List<Float>): Float {
        if (x.size < 2) return 0f
        val mean = x.average()
        return sqrt(x.sumOf { val d = it - mean; d * d } / (x.size - 1)).toFloat()
    }
}
