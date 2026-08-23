package co.helius.core.signal.ppg

import kotlin.math.abs

class SignalQualityEvaluator {
    fun evaluate(raw: List<FrameSample>, processed: ProcessedPpg?, config: PpgConfig): SignalQuality {
        val reasons = linkedSetOf<QualityReason>()
        if (raw.size < config.targetSampleRateHz * (config.acquisitionSeconds - 2)) {
            reasons += QualityReason.INSUFFICIENT_DURATION
        }
        if (raw.isEmpty()) return SignalQuality(0, false, reasons + QualityReason.NO_FINGER)

        val meanRed = raw.map { it.red }.average()
        val saturation = raw.map { it.saturatedFraction }.average()
        val motion = raw.map { abs(it.motion) }.average()
        if (meanRed < 80.0) reasons += QualityReason.NO_FINGER
        if (saturation > 0.35) reasons += QualityReason.SATURATED
        if (motion > 1.25) reasons += QualityReason.MOTION

        val gaps = raw.zipWithNext().count { (a, b) ->
            (b.timestampNs - a.timestampNs) > 100_000_000L
        }
        if (gaps > 2) reasons += QualityReason.FRAME_GAPS
        if (processed == null || processed.features.perfusionProxy < 0.015f) {
            reasons += QualityReason.LOW_PULSATILITY
        }

        var score = 100
        for (reason in reasons) score -= when (reason) {
            QualityReason.NO_FINGER -> 70
            QualityReason.INSUFFICIENT_DURATION -> 45
            QualityReason.LOW_PULSATILITY -> 40
            QualityReason.MOTION -> 25
            QualityReason.FRAME_GAPS -> 20
            QualityReason.SATURATED -> 20
            else -> 25
        }
        score = score.coerceIn(0, 100)
        return SignalQuality(score, score >= config.minQuality && reasons.none {
            it == QualityReason.NO_FINGER || it == QualityReason.INSUFFICIENT_DURATION
        }, reasons)
    }
}
