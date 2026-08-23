package co.helius.core.signal.motion

/**
 * Detecta ráfagas de picos separadas por pausas -- la huella de un patrón
 * deliberado tipo SOS ("3-3": tres golpes, pausa, tres golpes). Umbral
 * determinista sobre la señal cruda, sin ML.
 */
object MotionPatternDetector {

    /** Separación mínima entre dos picos para contarlos como golpes distintos. */
    private const val MIN_PEAK_GAP_MS = 250L

    /** Pausa mínima entre golpes para considerar que empieza una ráfaga nueva. */
    private const val BURST_GAP_MS = 600L

    /** "" si hay menos de dos golpes: no hay patrón que describir. */
    fun detect(samples: List<MotionSample>, threshold: Double): String {
        val peaks = findPeaks(samples, threshold)
        if (peaks.size < 2) return ""

        val bursts = mutableListOf(mutableListOf(peaks.first()))
        for (i in 1 until peaks.size) {
            val gap = peaks[i] - peaks[i - 1]
            if (gap >= BURST_GAP_MS) {
                bursts.add(mutableListOf(peaks[i]))
            } else {
                bursts.last().add(peaks[i])
            }
        }
        return bursts.joinToString("-") { it.size.toString() }
    }

    private fun findPeaks(samples: List<MotionSample>, threshold: Double): List<Long> {
        val peaks = mutableListOf<Long>()
        var lastPeakMs: Long? = null
        for (i in 1 until samples.size - 1) {
            val s = samples[i]
            if (s.magnitude < threshold) continue
            if (s.magnitude < samples[i - 1].magnitude || s.magnitude < samples[i + 1].magnitude) continue
            if (lastPeakMs != null && s.timestampMs - lastPeakMs!! < MIN_PEAK_GAP_MS) continue
            peaks.add(s.timestampMs)
            lastPeakMs = s.timestampMs
        }
        return peaks
    }
}
