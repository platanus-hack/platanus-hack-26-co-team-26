package co.helius.core.signal.motion

import kotlin.math.PI
import kotlin.math.cos
import kotlin.math.ln
import kotlin.math.sin
import kotlin.math.sqrt

/**
 * DSP puro sobre una ventana de muestras de magnitud (acelerómetro o
 * giroscopio, ya reducidas a escalar). Sin dependencias de Android: corre
 * igual en JVM sobre grabaciones reproducidas, como `core/signal/ppg`.
 */
object MotionFeatureExtractor {

    /** Banda de interés para "sacudida deliberada" con la mano (Hz). */
    private const val MIN_HZ = 0.5
    private const val MAX_HZ = 6.0
    private const val HZ_STEP = 0.25
    private const val MIN_SAMPLES_FOR_SPECTRUM = 8

    fun extract(samples: List<MotionSample>, sampleRateHz: Double): AxisFeatures {
        if (samples.isEmpty()) return AxisFeatures(0.0, 0.0, 0.0, null, null)

        val mean = samples.sumOf { it.magnitude } / samples.size
        val energy = samples.sumOf { it.magnitude * it.magnitude }
        val rms = sqrt(energy / samples.size)

        var crossings = 0
        for (i in 1 until samples.size) {
            val prev = samples[i - 1].magnitude - mean
            val curr = samples[i].magnitude - mean
            if ((prev < 0 && curr >= 0) || (prev >= 0 && curr < 0)) crossings++
        }
        val durationS = (samples.last().timestampMs - samples.first().timestampMs) / 1000.0
        val zcr = if (durationS > 0) crossings / durationS else 0.0

        if (samples.size < MIN_SAMPLES_FOR_SPECTRUM || sampleRateHz <= 0) {
            return AxisFeatures(rms, energy, zcr, null, null)
        }
        val (dominantHz, entropy) = spectrum(samples, mean)
        return AxisFeatures(rms, energy, zcr, dominantHz, entropy)
    }

    /**
     * DFT ingenuo (O(muestras · bins)) limitado a las frecuencias plausibles
     * de una sacudida con la mano ([MIN_HZ], [MAX_HZ]). Las ventanas de este
     * proyecto son cortas (segundos, no minutos) y el número de bins es fijo
     * y pequeño (~23), así que esto es barato y evita traer una librería de
     * FFT completa sólo para un puñado de frecuencias.
     */
    private fun spectrum(samples: List<MotionSample>, mean: Double): Pair<Double?, Double?> {
        val n = samples.size
        val t0 = samples.first().timestampMs
        val bins = generateSequence(MIN_HZ) { it + HZ_STEP }.takeWhile { it <= MAX_HZ }.toList()
        if (bins.isEmpty()) return null to null

        val powers = DoubleArray(bins.size)
        for ((bi, hz) in bins.withIndex()) {
            var re = 0.0
            var im = 0.0
            for (s in samples) {
                val tS = (s.timestampMs - t0) / 1000.0
                val angle = 2.0 * PI * hz * tS
                val v = s.magnitude - mean
                re += v * cos(angle)
                im -= v * sin(angle)
            }
            powers[bi] = (re * re + im * im) / n
        }

        val totalPower = powers.sum()
        if (totalPower <= 1e-12) return null to null

        var maxPower = -1.0
        var maxIdx = 0
        for (i in powers.indices) {
            if (powers[i] > maxPower) {
                maxPower = powers[i]
                maxIdx = i
            }
        }
        val dominantHz = bins[maxIdx]

        // Entropía de Shannon normalizada de la distribución de potencia:
        // 0 = toda la energía en una frecuencia (patrón claro), 1 = repartida
        // por igual entre todos los bins (ruido/vibración ambiental).
        var entropy = 0.0
        for (p in powers) {
            val prob = p / totalPower
            if (prob > 1e-9) entropy -= prob * ln(prob)
        }
        val normalizedEntropy = entropy / ln(bins.size.toDouble())

        return dominantHz to normalizedEntropy
    }
}
