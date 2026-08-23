package co.helius.core.signal.ppg

import kotlin.math.PI
import kotlin.math.sin
import kotlin.test.Test
import kotlin.test.assertNotNull
import kotlin.test.assertNull
import kotlin.test.assertTrue

/**
 * NOTA: escrito sin poder correr ./gradlew en este entorno (ver
 * docs/validation/PHONE-READINESS.md) -- las tolerancias son deliberadamente
 * amplias porque no se pudo verificar el valor exacto que produce la cadena
 * completa de interpolación/detrend/filtro/normalización. Quien integre esto
 * en Android Studio debe correrlo como parte de L1 y ajustar si hace falta.
 */
class PpgSignalProcessorTest {

    private fun cleanPulseSamples(seconds: Int, bpm: Double, fs: Int = 30): List<FrameSample> {
        val hz = bpm / 60.0
        val n = seconds * fs
        return List(n) { index ->
            val t = index.toDouble() / fs
            val red = 100f + 20f * sin(2 * PI * hz * t).toFloat()
            FrameSample(
                timestampNs = (index * 1_000_000_000L) / fs,
                red = red,
                green = 80f,
                blue = 60f,
                lumaStd = 1f,
                saturatedFraction = 0f,
                motion = 0f,
            )
        }
    }

    @Test
    fun `sdnn and pnn50 populate with enough beats in a regular clean pulse`() {
        // 20s a 72bpm ~ 24 picos, por encima de MIN_BEATS_FOR_PNN50 (10).
        val samples = cleanPulseSamples(seconds = 20, bpm = 72.0)

        val result = PpgSignalProcessor().process(samples)

        assertNotNull(result, "la ventana sintética debería producir un ProcessedPpg")
        val sdnn = result.features.sdnnMs
        val pnn50 = result.features.pnn50
        assertNotNull(sdnn, "con suficientes picos, SDNN no debería ser null")
        assertNotNull(pnn50, "con >= MIN_BEATS_FOR_PNN50 picos, pNN50 no debería ser null")
        // Un pulso perfectamente periódico produce IBIs casi idénticos: SDNN bajo
        // y pocos pares con diferencia > 50ms. Tolerancias amplias a propósito.
        assertTrue(sdnn < 60f, "SDNN de un pulso sintético limpio debería ser bajo, fue $sdnn")
        assertTrue(pnn50 < 0.5f, "pNN50 de un pulso sintético limpio debería ser bajo, fue $pnn50")
    }

    @Test
    fun `pnn50 stays null when the window has too few beats`() {
        // 6s a 72bpm ~ 7 picos, por debajo de MIN_BEATS_FOR_PNN50 (10).
        val samples = cleanPulseSamples(seconds = 6, bpm = 72.0)

        val result = PpgSignalProcessor().process(samples)

        assertNotNull(result)
        assertNull(result.features.pnn50, "con pocos picos, pNN50 debe quedarse en null, no en un ratio ruidoso")
    }
}
