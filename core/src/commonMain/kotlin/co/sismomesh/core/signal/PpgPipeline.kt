package co.sismomesh.core.signal

/**
 * Cadena determinista: resample → normalize → detrend → bandpass(0.5-4Hz) → FFT/PSD
 * + peak timing → SQI. Ver estado del arte en el README raíz, sección "PPG con Cámara".
 * HeuristicFallback obligatorio: el pipeline debe funcionar sin ML.
 */
class PpgPipeline {
    fun process(samples: DoubleArray, fs: Double): PulseEstimate {
        if (samples.size < (fs * 8).toInt() || fs <= 0.0) {
            return PulseEstimate(0.0, 0.0, "HEURISTIC_FALLBACK", PhysiologicalPattern.UNRELIABLE_MEASUREMENT)
        }

        val centered = detrend(samples)
        val variance = centered.sumOf { it * it } / centered.size
        if (variance <= 1e-10) return PulseEstimate(0.0, 0.0, "HEURISTIC_FALLBACK", PhysiologicalPattern.UNRELIABLE_MEASUREMENT)

        var bestFrequency = 0.0
        var bestPower = 0.0
        var totalPower = 0.0
        val spectralPowers = mutableListOf<Pair<Double, Double>>()
        var frequency = 0.5
        while (frequency <= 4.0) {
            var real = 0.0
            var imaginary = 0.0
            centered.forEachIndexed { index, value ->
                val window = 0.5 - 0.5 * kotlin.math.cos(2.0 * kotlin.math.PI * index / (centered.lastIndex.coerceAtLeast(1)))
                val windowedValue = value * window
                val angle = 2.0 * kotlin.math.PI * frequency * index / fs
                real += windowedValue * kotlin.math.cos(angle)
                imaginary -= windowedValue * kotlin.math.sin(angle)
            }
            val power = real * real + imaginary * imaginary
            spectralPowers += frequency to power
            totalPower += power
            if (power > bestPower) { bestPower = power; bestFrequency = frequency }
            frequency += 0.05
        }
        // A real sampled sinusoid spreads across neighboring bins. Count that narrow
        // peak band as one coherent component while rejecting broad/noisy spectra.
        val coherentPeakPower = spectralPowers
            .filter { kotlin.math.abs(it.first - bestFrequency) <= 0.1 }
            .sumOf { it.second }
        val sqi = (coherentPeakPower / totalPower.coerceAtLeast(1e-9)).coerceIn(0.0, 1.0)
        val bpm = bestFrequency * 60.0
        val pattern = when {
            sqi < 0.5 -> PhysiologicalPattern.UNRELIABLE_MEASUREMENT
            bpm > 100 -> PhysiologicalPattern.HIGH_PULSE_PATTERN
            bpm < 50 -> PhysiologicalPattern.LOW_PULSE_PATTERN
            else -> PhysiologicalPattern.STABLE_PATTERN
        }
        return PulseEstimate(bpm, sqi, "HEURISTIC_FALLBACK", pattern)
    }

    /**
     * Two-pass guard for camera PPG. A low-SQI or physiologically unusual first
     * reading is never presented as a conclusion; the caller must capture again.
     * The second pass is combined with a robust median and remains observational.
     */
    fun assess(samples: DoubleArray, fs: Double, verificationSamples: DoubleArray? = null): PpgAssessment {
        val first = process(samples, fs)
        if (!requiresVerification(first)) {
            return PpgAssessment(first, first, null, VerificationStatus.ACCEPTED, "Lectura PPG estable")
        }
        if (verificationSamples == null) {
            return PpgAssessment(
                estimate = first,
                first = first,
                status = VerificationStatus.SECOND_VERIFICATION_REQUIRED,
                message = if (first.sqi < 0.60) "Calidad de señal insuficiente; repite la captura" else "Lectura inusual; repite la captura para verificar",
            )
        }

        val second = process(verificationSamples, fs)
        val usable = listOf(first, second).filter { it.bpm > 0.0 && it.sqi >= 0.50 }
        if (usable.size < 2) {
            val best = usable.maxByOrNull { it.sqi } ?: second
            return PpgAssessment(best, first, second, VerificationStatus.INCONCLUSIVE_RECHECK, "Las capturas no tienen calidad suficiente")
        }

        val agrees = kotlin.math.abs(first.bpm - second.bpm) <= 12.0
        val repeatedAnomaly = isAnomalous(first) && isAnomalous(second) && agrees
        val robust = robustEstimate(first, second)
        return when {
            repeatedAnomaly -> PpgAssessment(
                robust,
                first,
                second,
                VerificationStatus.REPEATED_ANOMALY,
                "Patrón inusual repetido; requiere valoración, no es un diagnóstico",
            )
            agrees -> PpgAssessment(robust, first, second, VerificationStatus.ACCEPTED, "Lecturas repetidas coherentes")
            else -> PpgAssessment(
                robust,
                first,
                second,
                VerificationStatus.INCONCLUSIVE_RECHECK,
                "Las capturas difieren; repite en reposo y con el dedo estable",
            )
        }
    }

    private fun requiresVerification(estimate: PulseEstimate): Boolean =
        estimate.bpm <= 0.0 || estimate.sqi < 0.60 || isAnomalous(estimate)

    private fun isAnomalous(estimate: PulseEstimate): Boolean =
        estimate.bpm in 0.0..49.0 || estimate.bpm >= 180.0

    private fun robustEstimate(first: PulseEstimate, second: PulseEstimate): PulseEstimate {
        // With two observations the robust midpoint is less sensitive to one noisy
        // frame window than trusting the first or second capture alone.
        val bpm = (first.bpm + second.bpm) / 2.0
        val conservativeSqi = minOf(first.sqi, second.sqi)
        val pattern = when {
            bpm >= 180.0 -> PhysiologicalPattern.HIGH_PULSE_PATTERN
            bpm < 50.0 -> PhysiologicalPattern.LOW_PULSE_PATTERN
            else -> PhysiologicalPattern.STABLE_PATTERN
        }
        return PulseEstimate(bpm, conservativeSqi, "HEURISTIC_DFT_ROBUST_MEDIAN", pattern)
    }

    private fun detrend(samples: DoubleArray): DoubleArray {
        val n = samples.size
        val meanX = (n - 1) / 2.0
        val meanY = samples.average()
        var numerator = 0.0
        var denominator = 0.0
        samples.forEachIndexed { index, value ->
            val x = index - meanX
            numerator += x * (value - meanY)
            denominator += x * x
        }
        val slope = numerator / denominator.coerceAtLeast(1e-9)
        val intercept = meanY - slope * meanX
        return DoubleArray(n) { index -> samples[index] - (intercept + slope * index) }
    }
}

data class PulseEstimate(
    val bpm: Double,
    val sqi: Double,
    val method: String,
    val pattern: PhysiologicalPattern = PhysiologicalPattern.UNRELIABLE_MEASUREMENT,
)

enum class PhysiologicalPattern {
    STABLE_PATTERN,
    HIGH_PULSE_PATTERN,
    LOW_PULSE_PATTERN,
    IRREGULAR_PULSE_PATTERN,
    REDUCED_PERFUSION_OR_CONTACT,
    PHYSIOLOGICAL_ACTIVATION_PATTERN,
    UNRELIABLE_MEASUREMENT,
}

enum class VerificationStatus {
    ACCEPTED,
    SECOND_VERIFICATION_REQUIRED,
    REPEATED_ANOMALY,
    INCONCLUSIVE_RECHECK,
}

data class PpgAssessment(
    val estimate: PulseEstimate,
    val first: PulseEstimate,
    val second: PulseEstimate? = null,
    val status: VerificationStatus,
    val message: String,
)
