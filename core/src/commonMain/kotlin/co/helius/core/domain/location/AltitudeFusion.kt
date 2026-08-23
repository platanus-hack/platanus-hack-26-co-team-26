package co.helius.core.domain.location

import co.helius.core.domain.vo.AltitudeSource
import kotlin.math.pow
import kotlin.math.round
import kotlin.math.sin
import kotlin.math.sqrt

/**
 * Fusión de altitud relativa (barómetro + UWB) — la parte de ADR-0009
 * (`docs/architecture/ADR/0009-3d-localization.md`) que le corresponde a
 * Helmut: medición/fusión dispositivo-a-dispositivo. El factor graph
 * completo que combina esto con observaciones RSSI de múltiples nodos es
 * responsabilidad de Miguel en `services/localization` (todavía sin
 * implementar, ver su README) — esto NO reemplaza esa pieza, la alimenta.
 *
 * Fundamento de las fórmulas y márgenes de error reales:
 * `docs/architecture/LOCALIZATION-3D-STATE-OF-THE-ART.md`.
 *
 * Nunca produce un piso "exacto" — toda salida trae incertidumbre explícita
 * y un número de piso solo se reporta cuando esa incertidumbre es menor que
 * medio piso (ver [floorOf]), igual que el resto de localización del
 * proyecto (`docs/glossary.md`: "zona candidata con confianza", nunca
 * "ubicación exacta").
 */

/**
 * Presión de referencia del edificio/escenario (calibración) y altura de
 * piso asumida. ADR-0009: "la altura de piso no es universal... se registra
 * como parámetro ASSUMED por escenario, igual que `n` en el modelo
 * log-distance — nunca una constante fija en código". Por eso esto es un
 * parámetro que el llamador debe proveer, no un default silencioso.
 */
data class BarometricCalibration(
    val referencePressureHpa: Double,
    val referenceAltitudeM: Double = 0.0,
    val floorHeightM: Double = 3.0,
)

data class AltitudeEstimate(
    val altitudeM: Double,
    val accuracyM: Double,
    val source: AltitudeSource,
    /** Solo no-null si la incertidumbre alcanza para distinguir un piso del siguiente. */
    val estimatedFloor: Int? = null,
)

object AltitudeFusion {

    // Fórmula barométrica internacional (ICAO) — la misma que usan los
    // altímetros de consumo (p.ej. datasheet Bosch BMP280/BME280). Válida
    // para diferencias de altitud de edificio, no de vuelo.
    private const val BAROMETRIC_EXPONENT = 0.190263
    private const val BAROMETRIC_COEFFICIENT = 44330.77

    // Incertidumbre base sin recalibración reciente -- la deriva por clima
    // (frente de presión, viento) puede acumular varios metros en horas.
    // Ver docs/architecture/LOCALIZATION-3D-STATE-OF-THE-ART.md.
    const val BAROMETRIC_BASE_UNCERTAINTY_M = 3.0
    const val UWB_BASE_UNCERTAINTY_M = 0.3

    fun fromBarometric(pressureHpa: Double, calibration: BarometricCalibration): AltitudeEstimate {
        require(pressureHpa > 0) { "pressureHpa debe ser positivo" }
        require(calibration.referencePressureHpa > 0) { "referencePressureHpa debe ser positivo" }
        val relative = BAROMETRIC_COEFFICIENT *
            (1.0 - (pressureHpa / calibration.referencePressureHpa).pow(BAROMETRIC_EXPONENT))
        val altitude = calibration.referenceAltitudeM + relative
        return AltitudeEstimate(
            altitudeM = altitude,
            accuracyM = BAROMETRIC_BASE_UNCERTAINTY_M,
            source = AltitudeSource.BAROMETRIC,
            estimatedFloor = floorOf(altitude, BAROMETRIC_BASE_UNCERTAINTY_M, calibration),
        )
    }

    /**
     * Distancia+ángulo entre dos nodos -> componente vertical relativa al
     * nodo que mide. Solo tiene sentido como altitud ABSOLUTA si el peer de
     * referencia ya tiene una altitud conocida -- por eso pide
     * `peerAltitudeM` explícito, nunca asume 0 (asumir que el peer está en
     * el suelo sería inventar un dato que no llegó).
     */
    fun fromUwb(elevationDeg: Double, distanceM: Double, peerAltitudeM: Double): AltitudeEstimate {
        require(distanceM >= 0) { "distanceM no puede ser negativo" }
        val verticalOffset = distanceM * sin(elevationDeg.toRadians())
        return AltitudeEstimate(
            altitudeM = peerAltitudeM + verticalOffset,
            accuracyM = UWB_BASE_UNCERTAINTY_M,
            source = AltitudeSource.UWB_ELEVATION,
            // UWB por sí solo no conoce la calibración de piso del edificio.
            estimatedFloor = null,
        )
    }

    /**
     * Combina barométrico + UWB (ambos opcionales) en una sola estimación
     * por media ponderada inversamente por varianza -- UWB pesa más porque
     * su incertidumbre base es menor, pero nunca ignora por completo al
     * barómetro (el UWB podría estar en un tramo NLOS sin que el llamador
     * lo sepa). Si solo llegó una fuente, no hay "fusión" posible: se
     * devuelve tal cual, nunca se inventa la que falta.
     */
    fun fuse(
        barometric: AltitudeEstimate?,
        uwb: AltitudeEstimate?,
        calibration: BarometricCalibration?,
    ): AltitudeEstimate? {
        if (barometric == null) return uwb
        if (uwb == null) return barometric

        val weightBarometric = 1.0 / (barometric.accuracyM * barometric.accuracyM)
        val weightUwb = 1.0 / (uwb.accuracyM * uwb.accuracyM)
        val altitude = (barometric.altitudeM * weightBarometric + uwb.altitudeM * weightUwb) /
            (weightBarometric + weightUwb)
        val accuracy = sqrt(1.0 / (weightBarometric + weightUwb))
        return AltitudeEstimate(
            altitudeM = altitude,
            accuracyM = accuracy,
            source = AltitudeSource.FUSED,
            estimatedFloor = calibration?.let { floorOf(altitude, accuracy, it) },
        )
    }

    /** null si `floorHeightM` es inválido o si la incertidumbre es mayor que
     * medio piso -- por debajo de esa confianza es más honesto no dar un
     * número que dar uno que probablemente esté equivocado (ADR-0009:
     * "nunca un punto/piso exacto"). */
    private fun floorOf(altitudeM: Double, accuracyM: Double, calibration: BarometricCalibration): Int? {
        if (calibration.floorHeightM <= 0) return null
        if (accuracyM > calibration.floorHeightM / 2.0) return null
        return round(altitudeM / calibration.floorHeightM).toInt()
    }

    private fun Double.toRadians(): Double = this * kotlin.math.PI / 180.0
}
