package co.helius.android.transport

import android.content.Context
import android.provider.Settings
import android.util.Base64
import com.google.android.gms.nearby.Nearby
import com.google.android.gms.nearby.connection.AdvertisingOptions
import com.google.android.gms.nearby.connection.ConnectionLifecycleCallback
import com.google.android.gms.nearby.connection.ConnectionResolution
import com.google.android.gms.nearby.connection.ConnectionInfo
import com.google.android.gms.nearby.connection.ConnectionsClient
import com.google.android.gms.nearby.connection.DiscoveryOptions
import com.google.android.gms.nearby.connection.EndpointDiscoveryCallback
import com.google.android.gms.nearby.connection.DiscoveredEndpointInfo
import com.google.android.gms.nearby.connection.Payload
import com.google.android.gms.nearby.connection.PayloadCallback
import com.google.android.gms.nearby.connection.Strategy
import kotlinx.coroutines.flow.MutableSharedFlow
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.asSharedFlow
import kotlinx.coroutines.flow.asStateFlow

/**
 * Proximidad multi-radio para dos o más instancias HELIOS.
 * Nearby Connections negocia el medio disponible (Bluetooth/BLE o Wi-Fi
 * cercano) sin exigir Internet. DTN sigue siendo responsable de decidir qué
 * paquetes se conservan y cuándo se reintentan.
 */
class NearbyConnectionsTransport(context: Context) {
    private val appContext = context.applicationContext
    private val queuePreferences = appContext.getSharedPreferences(QUEUE_PREFERENCES, Context.MODE_PRIVATE)
    val deviceId: String = runCatching {
        Settings.Secure.getString(appContext.contentResolver, Settings.Secure.ANDROID_ID)
    }.getOrNull()?.takeIf { it.isNotBlank() } ?: "id-local-no-disponible"
    private var client: ConnectionsClient? = null
    private val strategy = Strategy.P2P_CLUSTER
    private val _events = MutableSharedFlow<NearbyEvent>(extraBufferCapacity = 64)
    val events = _events.asSharedFlow()
    private val connectedEndpoints = linkedSetOf<String>()
    private val discoveredEndpoints = linkedSetOf<String>()
    private val pendingPayloads = linkedMapOf<String, ByteArray>()
    private val seenPayloads = linkedSetOf<String>()
    private val _diagnostics = MutableStateFlow(NearbyDiagnostics(deviceId = deviceId))
    val diagnostics = _diagnostics.asStateFlow()
    private var running = false

    init {
        queuePreferences.all
            .filterKeys { it.startsWith(PACKET_PREFIX) }
            .forEach { (key, value) ->
                val encoded = value as? String ?: return@forEach
                val bytes = runCatching { Base64.decode(encoded, Base64.NO_WRAP) }.getOrNull() ?: return@forEach
                pendingPayloads[key.removePrefix(PACKET_PREFIX)] = bytes
            }
        _diagnostics.value = _diagnostics.value.copy(pendingPackets = pendingPayloads.size)
    }

    private val payloadCallback = object : PayloadCallback() {
        override fun onPayloadReceived(endpointId: String, payload: Payload) {
            payload.asBytes()?.let { bytes ->
                val text = bytes.decodeToString()
                if (text.startsWith(ACK_PREFIX)) {
                    val acknowledged = text.substringAfter(ACK_PREFIX).substringBefore('|')
                    if (acknowledged.isNotBlank()) {
                        removePending(acknowledged)
                        updateDiagnostics { it.copy(acknowledgements = it.acknowledgements + 1, pendingPackets = pendingPayloads.size, lastRelay = endpointId) }
                    }
                    return@let
                }
                val key = packetKey(bytes)
                if (!rememberSeen(key)) {
                    updateDiagnostics { it.copy(packetsDeduplicated = it.packetsDeduplicated + 1) }
                    return
                }
                rememberPending(key, bytes)
                updateDiagnostics {
                    it.copy(
                        packetsReceived = it.packetsReceived + 1,
                        pendingPackets = pendingPayloads.size,
                        lastPacket = key.take(16),
                        lastOrigin = parseOrigin(bytes),
                        lastHopCount = parseHopCount(bytes),
                        lastTransport = "Nearby Connections",
                        lastRelay = endpointId,
                    )
                }
                _events.tryEmit(NearbyEvent.PayloadReceived(endpointId, bytes))
                sendAcknowledgement(endpointId, key)
                // Un dispositivo que recibe no deja de buscar ni de retransmitir.
                // No se reenvía al endpoint de origen para evitar un eco inmediato.
                forward(bytes, except = endpointId)
            }
        }

        override fun onPayloadTransferUpdate(endpointId: String, update: com.google.android.gms.nearby.connection.PayloadTransferUpdate) = Unit
    }

    private val lifecycleCallback = object : ConnectionLifecycleCallback() {
        override fun onConnectionInitiated(endpointId: String, connectionInfo: ConnectionInfo) {
            client?.acceptConnection(endpointId, payloadCallback)
                ?.addOnFailureListener { _events.tryEmit(NearbyEvent.Error("No se pudo aceptar el dispositivo cercano: ${it.message ?: "error desconocido"}")) }
        }

        override fun onConnectionResult(endpointId: String, result: ConnectionResolution) {
            if (result.status.isSuccess) {
                connectedEndpoints += endpointId
                _events.tryEmit(NearbyEvent.Connected(endpointId))
                updateDiagnostics { it.copy(connectedPeers = connectedEndpoints.size) }
                flushPending(endpointId)
            } else {
                _events.tryEmit(NearbyEvent.Error("El enlace cercano no fue confirmado (${result.status.statusCode})"))
            }
        }

        override fun onDisconnected(endpointId: String) {
            connectedEndpoints -= endpointId
            _events.tryEmit(NearbyEvent.Disconnected(endpointId))
            updateDiagnostics { it.copy(connectedPeers = connectedEndpoints.size) }
        }
    }

    private val discoveryCallback = object : EndpointDiscoveryCallback() {
        override fun onEndpointFound(endpointId: String, info: DiscoveredEndpointInfo) {
            discoveredEndpoints += endpointId
            _events.tryEmit(NearbyEvent.Discovered(endpointId, info.endpointName))
            updateDiagnostics { it.copy(discoveredPeers = discoveredEndpoints.size) }
            client?.requestConnection("HELIOS", endpointId, lifecycleCallback)
                ?.addOnFailureListener { _events.tryEmit(NearbyEvent.Error("No se pudo solicitar el enlace cercano: ${it.message ?: "error desconocido"}")) }
        }

        override fun onEndpointLost(endpointId: String) {
            discoveredEndpoints -= endpointId
            _events.tryEmit(NearbyEvent.Lost(endpointId))
            updateDiagnostics { it.copy(discoveredPeers = discoveredEndpoints.size) }
        }
    }

    fun start() {
        if (running) return
        running = true
        val nearbyClient = runCatching { Nearby.getConnectionsClient(appContext) }
            .onFailure { _events.tryEmit(NearbyEvent.Error("Servicios de proximidad no disponibles: ${it.message ?: "Google Play Services no responde"}")) }
            .getOrNull()
        if (nearbyClient == null) {
            running = false
            return
        }
        client = nearbyClient
        updateDiagnostics { it.copy(availableTransports = setOf("Nearby Connections · Bluetooth/BLE o Wi‑Fi local")) }
        val advertising = nearbyClient.startAdvertising(
            "HELIOS",
            SERVICE_ID,
            lifecycleCallback,
            AdvertisingOptions.Builder().setStrategy(strategy).build(),
        )
        advertising.addOnSuccessListener { _events.tryEmit(NearbyEvent.AdvertisingStarted) }
            .addOnFailureListener { _events.tryEmit(NearbyEvent.Error("No se pudo anunciar HELIOS: ${it.message ?: "error desconocido"}")) }

        val discovery = nearbyClient.startDiscovery(
            SERVICE_ID,
            discoveryCallback,
            DiscoveryOptions.Builder().setStrategy(strategy).build(),
        )
        discovery.addOnSuccessListener { _events.tryEmit(NearbyEvent.DiscoveryStarted) }
            .addOnFailureListener { _events.tryEmit(NearbyEvent.Error("No se pudo buscar dispositivos HELIOS: ${it.message ?: "error desconocido"}")) }
    }

    fun send(bytes: ByteArray) {
        val key = packetKey(bytes)
        rememberSeen(key)
        rememberPending(key, bytes)
        updateDiagnostics {
            it.copy(
                packetsCreated = it.packetsCreated + 1,
                pendingPackets = pendingPayloads.size,
                lastPacket = key.take(16),
                lastOrigin = parseOrigin(bytes),
                lastHopCount = parseHopCount(bytes),
                lastTransport = "Nearby Connections",
                lastRelay = null,
            )
        }
        if (client == null) {
            _events.tryEmit(NearbyEvent.Error("La búsqueda cercana no está activa; el paquete quedó pendiente en la cola local de esta sesión."))
            return
        }
        if (connectedEndpoints.isEmpty()) {
            _events.tryEmit(NearbyEvent.Error("No hay dispositivos HELIOS conectados; el paquete quedó pendiente para la próxima conexión."))
            return
        }
        forward(bytes)
    }

    fun stop() {
        if (!running) return
        running = false
        client?.stopAdvertising()
        client?.stopDiscovery()
        connectedEndpoints.toList().forEach { client?.disconnectFromEndpoint(it) }
        connectedEndpoints.clear()
        discoveredEndpoints.clear()
        client = null
        updateDiagnostics { it.copy(connectedPeers = 0, discoveredPeers = 0, availableTransports = emptySet(), pendingPackets = pendingPayloads.size) }
    }

    fun clearDiagnostics() {
        pendingPayloads.clear()
        seenPayloads.clear()
        queuePreferences.edit().clear().apply()
        _diagnostics.value = NearbyDiagnostics(deviceId = deviceId)
    }

    private fun flushPending(endpointId: String) {
        pendingPayloads.values.toList().forEach { forward(it, only = endpointId) }
    }

    private fun forward(bytes: ByteArray, except: String? = null, only: String? = null) {
        val nearbyClient = client ?: return
        val targets = when {
            only != null -> listOf(only)
            else -> connectedEndpoints.filterNot { it == except }
        }
        if (targets.isEmpty()) return
        nearbyClient.sendPayload(targets, Payload.fromBytes(bytes))
            .addOnSuccessListener {
                updateDiagnostics {
                    it.copy(
                        packetsForwarded = it.packetsForwarded + targets.size,
                        lastRelay = targets.lastOrNull(),
                        pendingPackets = pendingPayloads.size,
                    )
                }
            }
            .addOnFailureListener {
                _events.tryEmit(NearbyEvent.Error("El paquete quedó pendiente: ${it.message ?: "fallo de transporte"}"))
            }
    }

    private fun updateDiagnostics(transform: (NearbyDiagnostics) -> NearbyDiagnostics) {
        _diagnostics.value = transform(_diagnostics.value)
    }

    private fun rememberSeen(key: String): Boolean {
        if (seenPayloads.contains(key)) return false
        if (seenPayloads.size >= MAX_SEEN_PACKETS) seenPayloads.remove(seenPayloads.firstOrNull())
        return seenPayloads.add(key)
    }

    private fun rememberPending(key: String, bytes: ByteArray) {
        if (!pendingPayloads.containsKey(key) && pendingPayloads.size >= MAX_PENDING_PACKETS) {
            pendingPayloads.keys.firstOrNull()?.let(::removePending)
        }
        pendingPayloads[key] = bytes
        queuePreferences.edit().putString(PACKET_PREFIX + key, Base64.encodeToString(bytes, Base64.NO_WRAP)).apply()
    }

    private fun removePending(key: String) {
        pendingPayloads.remove(key)
        queuePreferences.edit().remove(PACKET_PREFIX + key).apply()
    }

    private fun sendAcknowledgement(endpointId: String, key: String) {
        client?.sendPayload(endpointId, Payload.fromBytes("$ACK_PREFIX$key|$deviceId".encodeToByteArray()))
    }

    private fun packetKey(bytes: ByteArray): String = runCatching {
        java.security.MessageDigest.getInstance("SHA-256").digest(bytes).joinToString("") { "%02x".format(it) }
    }.getOrElse { bytes.contentHashCode().toString() }

    private fun parseOrigin(bytes: ByteArray): String {
        val text = bytes.decodeToString()
        return text.split('|').getOrNull(2)?.takeIf { it.isNotBlank() } ?: "no disponible"
    }

    private fun parseHopCount(bytes: ByteArray): Int? {
        val match = Regex("(?:hop|saltos)=([0-9]+)").find(bytes.decodeToString())
        return match?.groupValues?.getOrNull(1)?.toIntOrNull()
    }

    companion object {
        private const val SERVICE_ID = "co.helius.nearby.v1"
        private const val ACK_PREFIX = "HELIOS_ACK|"
        private const val QUEUE_PREFERENCES = "helios.nearby.queue"
        private const val PACKET_PREFIX = "packet."
        private const val MAX_SEEN_PACKETS = 512
        private const val MAX_PENDING_PACKETS = 128
    }
}

data class NearbyDiagnostics(
    val deviceId: String,
    val role: String = "ORIGEN + RELAY (sesión local)",
    val discoveredPeers: Int = 0,
    val connectedPeers: Int = 0,
    val availableTransports: Set<String> = emptySet(),
    val packetsCreated: Int = 0,
    val packetsReceived: Int = 0,
    val packetsForwarded: Int = 0,
    val packetsDeduplicated: Int = 0,
    val pendingPackets: Int = 0,
    val acknowledgements: Int = 0,
    val lastPacket: String? = null,
    val lastOrigin: String? = null,
    val lastHopCount: Int? = null,
    val lastTransport: String? = null,
    val lastRelay: String? = null,
)

sealed interface NearbyEvent {
    data object AdvertisingStarted : NearbyEvent
    data object DiscoveryStarted : NearbyEvent
    data class Discovered(val endpointId: String, val name: String) : NearbyEvent
    data class Connected(val endpointId: String) : NearbyEvent
    data class Disconnected(val endpointId: String) : NearbyEvent
    data class Lost(val endpointId: String) : NearbyEvent
    data class PayloadReceived(val endpointId: String, val bytes: ByteArray) : NearbyEvent
    data class Error(val message: String) : NearbyEvent
}
