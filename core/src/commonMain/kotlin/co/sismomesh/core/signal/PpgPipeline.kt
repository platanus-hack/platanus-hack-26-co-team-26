package co.sismomesh.core.signal

/**
 * Cadena determinista: resample → normalize → detrend → bandpass(0.5-4Hz) → FFT/PSD
 * + peak timing → SQI. Ver estado del arte en el README raíz, sección "PPG con Cámara".
 * HeuristicFallback obligatorio: el pipeline debe funcionar sin ML.
 */
class PpgPipeline {
    fun process(samples: DoubleArray, fs: Double): PulseEstimate = TODO("dueño=Alex")
}

data class PulseEstimate(val bpm: Double, val sqi: Double, val method: String)
