package co.helius.core.domain.location

import co.helius.core.domain.vo.AltitudeSource
import kotlin.test.Test
import kotlin.test.assertEquals
import kotlin.test.assertNotNull
import kotlin.test.assertNull
import kotlin.test.assertTrue

class AltitudeFusionTest {

    private val groundFloor = BarometricCalibration(referencePressureHpa = 1013.25, referenceAltitudeM = 0.0, floorHeightM = 3.0)

    @Test
    fun `pressure equal to reference gives altitude at the reference point`() {
        val estimate = AltitudeFusion.fromBarometric(1013.25, groundFloor)

        assertEquals(0.0, estimate.altitudeM, absoluteTolerance = 0.01)
        assertEquals(AltitudeSource.BAROMETRIC, estimate.source)
        assertEquals(0, estimate.estimatedFloor)
    }

    @Test
    fun `lower pressure than reference means higher altitude`() {
        val estimate = AltitudeFusion.fromBarometric(1000.0, groundFloor)

        assertTrue(estimate.altitudeM > 0, "presión más baja que la referencia debería dar altitud positiva")
    }

    @Test
    fun `matches the well-known near-sea-level approximation of about 8_3 meters per hPa`() {
        // Aproximación estándar de ingeniería (ver docs/architecture/LOCALIZATION-3D-STATE-OF-THE-ART.md):
        // cerca del nivel del mar, una caída de presión de 1 hPa equivale a subir ~8.3 m.
        val estimate = AltitudeFusion.fromBarometric(1013.25 - 10.0, groundFloor)

        assertEquals(83.0, estimate.altitudeM, absoluteTolerance = 3.0)
    }

    @Test
    fun `floor number requires enough certainty, half a floor height or better`() {
        // Con la incertidumbre base (3 m) y pisos de 3 m, el umbral es 1.5 m -- no alcanza.
        val tooUncertain = BarometricCalibration(referencePressureHpa = 1013.25, floorHeightM = 3.0)
        val estimate = AltitudeFusion.fromBarometric(1000.0, tooUncertain)
        assertNull(estimate.estimatedFloor, "con 3 m de incertidumbre sobre un piso de 3 m, no debería arriesgar un número")

        // Con pisos más altos (6 m), el mismo margen de error sí alcanza.
        val roomier = BarometricCalibration(referencePressureHpa = 1013.25, floorHeightM = 6.0)
        val estimate2 = AltitudeFusion.fromBarometric(1000.0, roomier)
        assertNotNull(estimate2.estimatedFloor)
    }

    @Test
    fun `uwb straight up adds the full distance as vertical offset`() {
        val estimate = AltitudeFusion.fromUwb(elevationDeg = 90.0, distanceM = 5.0, peerAltitudeM = 10.0)

        assertEquals(15.0, estimate.altitudeM, absoluteTolerance = 0.01)
        assertEquals(AltitudeSource.UWB_ELEVATION, estimate.source)
    }

    @Test
    fun `uwb level with the peer adds no vertical offset`() {
        val estimate = AltitudeFusion.fromUwb(elevationDeg = 0.0, distanceM = 5.0, peerAltitudeM = 10.0)

        assertEquals(10.0, estimate.altitudeM, absoluteTolerance = 0.01)
    }

    @Test
    fun `fusing with only one source returns it unchanged, never invents the missing one`() {
        val barometric = AltitudeFusion.fromBarometric(1000.0, groundFloor)

        assertEquals(barometric, AltitudeFusion.fuse(barometric, null, groundFloor))
        assertEquals(barometric, AltitudeFusion.fuse(null, barometric, groundFloor))
        assertNull(AltitudeFusion.fuse(null, null, groundFloor))
    }

    @Test
    fun `fusing both sources is more confident than either alone and leans toward the more precise one`() {
        val barometric = AltitudeFusion.fromBarometric(1000.0, groundFloor) // ~83 m, +-3 m
        val uwb = AltitudeFusion.fromUwb(elevationDeg = 90.0, distanceM = 1.0, peerAltitudeM = 80.0) // 81 m, +-0.3 m

        val fused = AltitudeFusion.fuse(barometric, uwb, groundFloor)

        assertNotNull(fused)
        assertEquals(AltitudeSource.FUSED, fused.source)
        assertTrue(fused.accuracyM < uwb.accuracyM, "la fusión debería ser más precisa que UWB solo")
        assertTrue(fused.accuracyM < barometric.accuracyM, "la fusión debería ser más precisa que el barómetro solo")
        // Más cerca del UWB (menor incertidumbre) que del barómetro.
        val distToUwb = kotlin.math.abs(fused.altitudeM - uwb.altitudeM)
        val distToBarometric = kotlin.math.abs(fused.altitudeM - barometric.altitudeM)
        assertTrue(distToUwb < distToBarometric)
    }
}
