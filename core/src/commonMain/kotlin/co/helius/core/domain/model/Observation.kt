package co.helius.core.domain.model

import co.helius.core.domain.vo.GeoPoint
import co.helius.core.domain.vo.NodeId

/**
 * Lo que un nodo registra al ver a otro: RSSI, transporte, timestamp, y
 * opcionalmente el aporte vertical de UWB/barómetro (ADR-0009, mapa 3D).
 * Alimenta la localización probabilística (Sección 9, `services/localization`).
 * Generado conceptualmente desde `protocol/proto/helius/v1/observation.proto`
 * — mantener los dos en sincronía; cambios aquí requieren ADR si tocan el wire.
 *
 * Dueño: Helmut (captura en `android/transport`) / Miguel (consumo en el backend).
 */
data class PeerObservation(
    val incidentId: ByteArray,
    val nodeA: NodeId,
    val nodeB: NodeId,
    val rssiDbm: Double,
    val transport: String,
    val observedAtMs: ULong,
    val observerGeo: GeoPoint? = null,
    val observerAccM: Double? = null,
    // Aporte vertical opcional (ADR-0009) -- solo se llena con fuente real
    // (UWB / barómetro), nunca inferido de rssiDbm.
    val uwbElevationDeg: Double? = null,
    val uwbAzimuthDeg: Double? = null,
    val uwbDistanceM: Double? = null,
    val barometricPressureHpa: Double? = null,
) {
    override fun equals(other: Any?): Boolean {
        if (this === other) return true
        if (other !is PeerObservation) return false
        return incidentId.contentEquals(other.incidentId) &&
            nodeA == other.nodeA && nodeB == other.nodeB &&
            rssiDbm == other.rssiDbm && transport == other.transport &&
            observedAtMs == other.observedAtMs && observerGeo == other.observerGeo &&
            observerAccM == other.observerAccM && uwbElevationDeg == other.uwbElevationDeg &&
            uwbAzimuthDeg == other.uwbAzimuthDeg && uwbDistanceM == other.uwbDistanceM &&
            barometricPressureHpa == other.barometricPressureHpa
    }

    override fun hashCode(): Int {
        var result = incidentId.contentHashCode()
        result = 31 * result + nodeA.hashCode()
        result = 31 * result + nodeB.hashCode()
        return result
    }
}
