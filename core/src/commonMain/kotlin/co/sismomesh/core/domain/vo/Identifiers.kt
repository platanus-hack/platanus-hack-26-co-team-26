package co.sismomesh.core.domain.vo

/** Value objects base del dominio. Sin dependencias de plataforma (regla arch-guard). */

@JvmInline
value class NodeId(val value: String)

@JvmInline
value class PeerId(val value: String)

@JvmInline
value class BundleId(val bytes: ByteArray)

@JvmInline
value class Rssi(val dbm: Int)

@JvmInline
value class Battery(val percent: Int)

data class GeoPoint(val lat: Double, val lon: Double, val accuracyM: Double? = null)

enum class Priority { P0_LIFE_CRITICAL, P1_LOCATION, P2_STATUS, P3_NETWORK_OBS, P4_RAW_SENSOR, P5_DIAGNOSTIC }

/** Payload mínimo del anuncio BLE (≤26 B) — ver protocol/beacon/BEACON_FORMAT.md. */
data class BeaconPayload(
    val sessionHash: Short,
    val ephemeralNodeId: ByteArray,
    val flags: Byte,
    val battery: Byte,
    val status: Byte,
    val seq: Short,
    val hops: Byte,
)

data class PeerSighting(val peer: PeerId, val rssi: Rssi, val beacon: BeaconPayload, val observedAtMs: Long)

data class PeerLink(val peer: PeerId, val transport: String, val establishedAtMs: Long)
