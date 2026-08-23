package co.sismomesh.core.signal.ppg

/**
 * Fuses evidence without diagnosing, assigning clinical priority or inferring a cause.
 * Estimated ECG can contribute only when its independent release gate is enabled.
 */
class IfoFusionEngine(
    private val allowEstimatedEcgContribution: Boolean = false,
    private val minimumEcgQuality: Float = 0.80f,
) {
    fun evaluate(
        quality: SignalQuality,
        classification: Classification,
        estimatedEcg: EstimatedEcg,
    ): IfoResult {
        if (!quality.accepted) {
            val status = if (quality.score >= 50) IfoStatus.REPEAT_MEASUREMENT
            else IfoStatus.INSUFFICIENT_SIGNAL
            return IfoResult(
                status,
                PhysiologicalObservation.UNRELIABLE_MEASUREMENT,
                quality.reasons.map {
                    IfoEvidence(EvidenceSource.CAMERA_PPG, "QUALITY_${it.name}", null)
                },
                false,
            )
        }

        val ecgMayContribute = allowEstimatedEcgContribution &&
            estimatedEcg.status == EstimatedEcgStatus.AVAILABLE &&
            (estimatedEcg.reconstructionQuality ?: 0f) >= minimumEcgQuality

        val evidence = buildList {
            add(IfoEvidence(EvidenceSource.CAMERA_PPG, classification.observation.name, classification.confidence))
            if (ecgMayContribute) add(IfoEvidence(
                EvidenceSource.ESTIMATED_ECG,
                "ESTIMATED_ECG_RECONSTRUCTION_ACCEPTED",
                estimatedEcg.reconstructionQuality,
            ))
        }
        val marked = classification.observation != PhysiologicalObservation.STABLE_PATTERN
        return IfoResult(
            if (marked) IfoStatus.MARKED_PATTERN_OBSERVED else IfoStatus.OBSERVATION_AVAILABLE,
            classification.observation,
            evidence,
            ecgMayContribute,
        )
    }
}
