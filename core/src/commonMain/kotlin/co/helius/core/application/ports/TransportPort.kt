package co.helius.core.application.ports

import co.helius.core.domain.vo.BeaconPayload
import co.helius.core.domain.vo.PeerId
import co.helius.core.domain.vo.PeerLink
import co.helius.core.domain.vo.PeerSighting
import kotlinx.coroutines.flow.Flow

/**
 * Puerto de transporte: advertise / scan / connect / send.
 * Dueño: Helmut (Transporte y DTN). Adaptadores: BleTransport, WifiAwareTransport,
 * WifiDirectTransport, NearbyTransport, LoopbackFake (tests en JVM sin hardware).
 * Etiqueta de madurez: ENGINEERING — ver docs/team/DIVISION-DE-TRABAJO.md.
 */
interface TransportPort {
    fun capabilities(): Set<TransportKind>

    suspend fun startAdvertising(beacon: BeaconPayload)

    fun observePeers(): Flow<PeerSighting> // incluye RSSI

    suspend fun connect(peer: PeerId): PeerLink

    suspend fun stop()
}

enum class TransportKind { BLE, WIFI_AWARE, WIFI_DIRECT, NEARBY, UWB, ACOUSTIC }
