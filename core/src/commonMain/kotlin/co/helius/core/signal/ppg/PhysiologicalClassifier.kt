package co.helius.core.signal.ppg

interface PhysiologicalClassifier {
    fun classify(signal: ProcessedPpg, quality: SignalQuality): Classification
}

/** Safe, auditable fallback — el equivalente de `HeuristicFallback` (ver docs/architecture/OVERVIEW.md §10). Thresholds are product defaults, not clinical diagnoses. */
class SafetyFirstClassifier : PhysiologicalClassifier {
    override fun classify(signal: ProcessedPpg, quality: SignalQuality): Classification {
        if (!quality.accepted) return Classification(
            PhysiologicalObservation.UNRELIABLE_MEASUREMENT, null, false
        )
        val f = signal.features
        val bpm = f.pulseBpm ?: return Classification(
            PhysiologicalObservation.UNRELIABLE_MEASUREMENT, null, false
        )
        val observation = when {
            f.perfusionProxy < 0.02f -> PhysiologicalObservation.REDUCED_PERFUSION_OR_CONTACT
            f.irregularity > 0.20f -> PhysiologicalObservation.IRREGULAR_PULSE_PATTERN
            bpm > 110f -> PhysiologicalObservation.HIGH_PULSE_PATTERN
            bpm < 50f -> PhysiologicalObservation.LOW_PULSE_PATTERN
            bpm > 95f && f.irregularity < 0.15f -> PhysiologicalObservation.PHYSIOLOGICAL_ACTIVATION_PATTERN
            else -> PhysiologicalObservation.STABLE_PATTERN
        }
        return Classification(observation, null, false)
    }
}
