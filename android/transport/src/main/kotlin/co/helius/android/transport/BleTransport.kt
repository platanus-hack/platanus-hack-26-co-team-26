package co.helius.android.transport

import android.Manifest
import android.bluetooth.BluetoothAdapter
import android.bluetooth.BluetoothManager
import android.bluetooth.le.AdvertiseCallback
import android.bluetooth.le.AdvertiseData
import android.bluetooth.le.AdvertiseSettings
import android.bluetooth.le.ScanCallback
import android.bluetooth.le.ScanFilter
import android.bluetooth.le.ScanResult
import android.bluetooth.le.ScanSettings
import android.content.Context
import android.content.pm.PackageManager
import android.os.ParcelUuid
import androidx.core.content.ContextCompat
import co.helius.core.application.ports.BundleStorePort
import co.helius.core.application.ports.TransportKind
import co.helius.core.application.ports.TransportPort
import co.helius.core.domain.vo.BeaconPayload
import co.helius.core.domain.vo.PeerId
import co.helius.core.domain.vo.PeerLink
import co.helius.core.domain.vo.PeerSighting
import co.helius.core.domain.vo.Rssi
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.channels.awaitClose
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.callbackFlow

/**
 * Adaptador real de TransportPort sobre BLE (Sección 7, protocol/beacon/BEACON_FORMAT.md).
 * BLE es el denominador común: siempre encendido durante el incidente, los
 * demás transportes se escalan después del descubrimiento
 * (docs/architecture/OVERVIEW.md § 6). Dueño: Helmut.
 *
 * `startAdvertising()` levanta también el `BleGattServer` (para servir a
 * quien se conecte a este teléfono); `connect()` delega en `BleGattClient`,
 * que hace la conexión Y el intercambio completo de inventario/bundles antes
 * de devolver el `PeerLink` — ver esas dos clases para el protocolo real.
 *
 * IMPORTANTE (ver docs/validation/PHONE-READINESS.md): este archivo y sus
 * colaboradores (`BleGattClient`, `BleGattServer`, `BleChunking`,
 * `BleBeaconCodec`) están escritos contra la API documentada de Android BLE
 * pero **nunca se compilaron ni se corrieron** -- no hay JDK/Android SDK en el
 * entorno donde se escribieron. Antes de cualquier demo con teléfonos reales:
 * `./gradlew :android:transport:compileDebugKotlin` y luego
 * `connectedDebugAndroidTest` en al menos dos dispositivos físicos.
 */
class BleTransport(
    private val context: Context,
    private val localStore: BundleStorePort,
    private val scope: CoroutineScope,
    private val sessionKey: () -> ByteArray,
    private val protocolVersion: Int = 1,
) : TransportPort {

    private val adapter: BluetoothAdapter? by lazy {
        (context.getSystemService(Context.BLUETOOTH_SERVICE) as? BluetoothManager)?.adapter
    }

    private val gattClient = BleGattClient(context, scope)
    private val gattServer = BleGattServer(context, localStore, scope)

    private var advertiseCallback: AdvertiseCallback? = null
    private var serverStarted = false

    override fun capabilities(): Set<TransportKind> {
        val hasBle = context.packageManager.hasSystemFeature(PackageManager.FEATURE_BLUETOOTH_LE)
        return if (hasBle) setOf(TransportKind.BLE) else emptySet()
    }

    override suspend fun startAdvertising(beacon: BeaconPayload) {
        requirePermission(Manifest.permission.BLUETOOTH_ADVERTISE)
        requirePermission(Manifest.permission.BLUETOOTH_CONNECT) // openGattServer también lo exige

        if (!serverStarted) {
            gattServer.start()
            serverStarted = true
        }

        val advertiser = adapter?.bluetoothLeAdvertiser
            ?: throw IllegalStateException("BLE advertiser no disponible (adapter apagado o sin hardware)")

        val wireBytes = BleBeaconCodec.encode(protocolVersion, beacon, sessionKey())

        val settings = AdvertiseSettings.Builder()
            .setAdvertiseMode(AdvertiseSettings.ADVERTISE_MODE_LOW_LATENCY)
            .setTxPowerLevel(AdvertiseSettings.ADVERTISE_TX_POWER_HIGH)
            .setConnectable(true) // permite que un peer inicie GATT tras verlo en el scan
            .build()

        // OJO presupuesto: legacy advertising son 31 B totales. NO llamar también a
        // addServiceUuid(SERVICE_UUID) aquí -- sería una AD structure separada y
        // redundante (el UUID ya va dentro de la AD structure de service data),
        // y el presupuesto de 23 B del beacon (BEACON_FORMAT.md) ya está calculado
        // justo para caber en Flags(3B) + ServiceData header+UUID(4B, con UUID
        // comprimido a 16 bits vía el patrón de Base UUID de SERVICE_UUID) + 23B.
        // Con las dos llamadas se excede el límite y el advertising falla o se trunca.
        val data = AdvertiseData.Builder()
            .setIncludeDeviceName(false)
            .addServiceData(SERVICE_UUID, wireBytes)
            .build()

        val callback = object : AdvertiseCallback() {
            override fun onStartFailure(errorCode: Int) {
                // TODO(dueño=Helmut): propagar el error (p. ej. ADVERTISE_FAILED_DATA_TOO_LARGE
                // si algún fabricante recorta el presupuesto de 26 B) a PowerPolicy/UI.
            }
        }
        advertiseCallback = callback
        advertiser.startAdvertising(settings, data, callback)
    }

    override fun observePeers(): Flow<PeerSighting> = callbackFlow {
        requirePermission(Manifest.permission.BLUETOOTH_SCAN)
        val scanner = adapter?.bluetoothLeScanner
            ?: throw IllegalStateException("BLE scanner no disponible (adapter apagado o sin hardware)")

        val filter = ScanFilter.Builder().setServiceUuid(SERVICE_UUID).build()
        val settings = ScanSettings.Builder()
            .setScanMode(ScanSettings.SCAN_MODE_LOW_LATENCY)
            .build()

        val callback = object : ScanCallback() {
            override fun onScanResult(callbackType: Int, result: ScanResult) {
                val serviceData = result.scanRecord?.getServiceData(SERVICE_UUID) ?: return
                val decoded = BleBeaconCodec.decode(serviceData, sessionKey()) ?: return
                trySend(
                    PeerSighting(
                        peer = PeerId(result.device.address),
                        rssi = Rssi(result.rssi),
                        beacon = decoded.beacon,
                        observedAtMs = System.currentTimeMillis(),
                    ),
                )
            }

            override fun onScanFailed(errorCode: Int) {
                close(IllegalStateException("BLE scan falló, código $errorCode"))
            }
        }

        scanner.startScan(listOf(filter), settings, callback)
        awaitClose {
            runCatching { scanner.stopScan(callback) }
        }
    }

    /**
     * Conecta Y sincroniza (Bloom filter + bundles faltantes en ambos
     * sentidos) antes de devolver el `PeerLink` — ver `BleGattClient`. Para
     * BLE, "conectar" y "hacer el encuentro DTN completo" son la misma
     * operación: no tiene sentido abrir la conexión sin intercambiar nada.
     */
    override suspend fun connect(peer: PeerId): PeerLink {
        requirePermission(Manifest.permission.BLUETOOTH_CONNECT)
        val device = adapter?.getRemoteDevice(peer.value)
            ?: throw IllegalStateException("Adapter BLE no disponible")
        return gattClient.connectAndSync(device, localStore)
    }

    override suspend fun stop() {
        requirePermission(Manifest.permission.BLUETOOTH_ADVERTISE)
        advertiseCallback?.let { adapter?.bluetoothLeAdvertiser?.stopAdvertising(it) }
        advertiseCallback = null
        if (serverStarted) {
            gattServer.stop()
            serverStarted = false
        }
    }

    private fun requirePermission(permission: String) {
        val granted = ContextCompat.checkSelfPermission(context, permission) == PackageManager.PERMISSION_GRANTED
        check(granted) { "Permiso requerido no concedido: $permission" }
    }

    companion object {
        // TODO(dueño=Helmut): reservar/registrar un UUID de servicio propio antes
        // de release; este es un valor de desarrollo, no oficial. DEBE seguir
        // siendo el mismo valor que BleGattProfile.SERVICE_UUID -- si divergen,
        // un cliente encuentra el beacon por scan pero no encuentra el servicio
        // GATT al conectarse (bug real que hubo aquí, corregido: ver
        // docs/validation/PHONE-READINESS.md).
        val SERVICE_UUID: ParcelUuid = ParcelUuid(BleGattProfile.SERVICE_UUID)
    }
}
