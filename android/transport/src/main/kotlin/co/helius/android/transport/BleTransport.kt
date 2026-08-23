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
import androidx.annotation.RequiresPermission
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
import kotlinx.coroutines.delay
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.callbackFlow
import kotlinx.coroutines.flow.retryWhen

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
 * Estado de verificación: compila y `:android:transport` pasa lint, pero **el
 * comportamiento en radio no está probado en hardware**. La guía de prueba en
 * dispositivos está en `docs/validation/BLE-INTERCONNECTION-TEST.md`.
 */
class BleTransport(
    private val context: Context,
    private val localStore: BundleStorePort,
    private val scope: CoroutineScope,
    private val sessionKey: () -> ByteArray,
    private val protocolVersion: Int = 1,
    /**
     * Se invoca cuando el radio falla de una forma que la UI debe poder mostrar.
     * Antes estos fallos se perdían: `onStartFailure` del advertising era un TODO
     * vacío y `onScanFailed` cerraba el Flow con una excepción. Un teléfono que no
     * anunciaba se veía idéntico a uno que sí.
     */
    private val onRadioEvent: (BleRadioEvent) -> Unit = {},
) : TransportPort {

    private val adapter: BluetoothAdapter? by lazy {
        (context.getSystemService(Context.BLUETOOTH_SERVICE) as? BluetoothManager)?.adapter
    }

    private val gattClient = BleGattClient(context, scope)
    private val gattServer = BleGattServer(context, localStore, scope)

    private var advertiseCallback: AdvertiseCallback? = null
    private var serverStarted = false

    /** Para que la UI explique *por qué* no hay descubrimiento en vez de decir "error". */
    fun readiness(): BleReadiness = BlePermissions.diagnose(context)

    override fun capabilities(): Set<TransportKind> {
        val hasBle = context.packageManager.hasSystemFeature(PackageManager.FEATURE_BLUETOOTH_LE)
        return if (hasBle) setOf(TransportKind.BLE) else emptySet()
    }

    @RequiresPermission(allOf = [Manifest.permission.BLUETOOTH_ADVERTISE, Manifest.permission.BLUETOOTH_CONNECT])
    override suspend fun startAdvertising(beacon: BeaconPayload) {
        requirePermissions()

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
        //
        // CONSECUENCIA CRÍTICA, y era un bug real: como el anuncio NO lleva una AD
        // structure de "service UUID list", `ScanRecord.getServiceUuids()` viene
        // vacío en el receptor, y por tanto un `ScanFilter.setServiceUuid(...)` NO
        // hace match nunca. El filtro del scan debe ser por service DATA — ver
        // observePeers().
        val data = AdvertiseData.Builder()
            .setIncludeDeviceName(false)
            .addServiceData(SERVICE_UUID, wireBytes)
            .build()

        val callback = object : AdvertiseCallback() {
            override fun onStartSuccess(settingsInEffect: AdvertiseSettings?) {
                onRadioEvent(BleRadioEvent.AdvertisingStarted)
            }

            override fun onStartFailure(errorCode: Int) {
                onRadioEvent(BleRadioEvent.AdvertisingFailed(errorCode, describeAdvertiseError(errorCode)))
            }
        }
        advertiseCallback = callback
        advertiser.startAdvertising(settings, data, callback)
    }

    /**
     * Escaneo continuo con reintento. Dos cambios de comportamiento respecto a la
     * versión anterior, y los dos eran fallos de campo:
     *
     * 1. **Filtro por service data, no por service UUID.** El anuncio solo lleva una
     *    AD structure de *service data* (ver startAdvertising), así que filtrar por
     *    `setServiceUuid` no hacía match con ningún anuncio: el escaneo corría, no
     *    daba error, y no reportaba un solo peer. Con `setServiceData` y máscara
     *    vacía se acepta cualquier contenido bajo nuestro UUID, que es lo correcto
     *    (el beacon se valida después, por MAGIC + AUTH, en BleBeaconCodec).
     * 2. **Un fallo de escaneo ya no es terminal.** Antes `onScanFailed` hacía
     *    `close(excepción)`, y un `callbackFlow` cerrado no se puede reabrir: el
     *    primer error dejaba el descubrimiento muerto hasta reiniciar el proceso.
     *    Eso explicaba el "una vez marca error, de ahí en adelante marca error".
     *    Ahora se reintenta con backoff, respetando el límite del sistema de 5
     *    `startScan` por ventana de 30 s (`SCAN_FAILED_SCANNING_TOO_FREQUENTLY`).
     */
    @RequiresPermission(Manifest.permission.BLUETOOTH_SCAN)
    override fun observePeers(): Flow<PeerSighting> = scanOnce().retryWhen { cause, attempt ->
        val scanError = cause as? BleScanException
        if (scanError?.permanent == true) return@retryWhen false
        val waitMs = when {
            scanError?.errorCode == SCAN_FAILED_SCANNING_TOO_FREQUENTLY -> THROTTLE_WINDOW_MS
            else -> (BACKOFF_BASE_MS shl attempt.toInt().coerceAtMost(4)).coerceAtMost(THROTTLE_WINDOW_MS)
        }
        onRadioEvent(BleRadioEvent.ScanRetrying(attempt, waitMs, cause.message ?: "sin detalle"))
        delay(waitMs)
        true
    }

    @RequiresPermission(Manifest.permission.BLUETOOTH_SCAN)
    private fun scanOnce(): Flow<PeerSighting> = callbackFlow {
        val readiness = readiness()
        if (!readiness.ready) {
            // Permanente: reintentar no cambia nada hasta que el usuario actúe.
            val blocker = readiness.firstBlocker() ?: "BLE no está listo"
            onRadioEvent(BleRadioEvent.NotReady(readiness))
            close(BleScanException(errorCode = null, permanent = true, message = blocker))
            return@callbackFlow
        }
        val scanner = adapter?.bluetoothLeScanner
            ?: run {
                close(BleScanException(null, permanent = true, message = "BLE scanner no disponible"))
                return@callbackFlow
            }

        // Máscara de longitud 0 = "cualquier service data bajo este UUID".
        val filter = ScanFilter.Builder()
            .setServiceData(SERVICE_UUID, ByteArray(0), ByteArray(0))
            .build()
        val settings = ScanSettings.Builder()
            .setScanMode(ScanSettings.SCAN_MODE_LOW_LATENCY)
            .setCallbackType(ScanSettings.CALLBACK_TYPE_ALL_MATCHES)
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

            override fun onBatchScanResults(results: MutableList<ScanResult>?) {
                results?.forEach { onScanResult(ScanSettings.CALLBACK_TYPE_ALL_MATCHES, it) }
            }

            override fun onScanFailed(errorCode: Int) {
                onRadioEvent(BleRadioEvent.ScanFailed(errorCode, describeScanError(errorCode)))
                close(
                    BleScanException(
                        errorCode = errorCode,
                        // FEATURE_UNSUPPORTED no se arregla reintentando; el resto sí.
                        permanent = errorCode == SCAN_FAILED_FEATURE_UNSUPPORTED,
                        message = describeScanError(errorCode),
                    ),
                )
            }
        }

        scanner.startScan(listOf(filter), settings, callback)
        onRadioEvent(BleRadioEvent.ScanStarted)
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
    @RequiresPermission(Manifest.permission.BLUETOOTH_CONNECT)
    override suspend fun connect(peer: PeerId): PeerLink {
        requirePermissions()
        val device = adapter?.getRemoteDevice(peer.value)
            ?: throw IllegalStateException("Adapter BLE no disponible")
        return gattClient.connectAndSync(device, localStore)
    }

    /**
     * Best-effort a propósito: parar no debe fallar por falta de permiso. Si el
     * usuario revocó `BLUETOOTH_ADVERTISE` mientras la app corría, lo que hay que
     * hacer es soltar los recursos que se pueda, no lanzar.
     */
    @RequiresPermission(allOf = [Manifest.permission.BLUETOOTH_ADVERTISE, Manifest.permission.BLUETOOTH_CONNECT])
    override suspend fun stop() {
        if (BlePermissions.hasAll(context)) {
            runCatching { advertiseCallback?.let { adapter?.bluetoothLeAdvertiser?.stopAdvertising(it) } }
        }
        advertiseCallback = null
        if (serverStarted) {
            runCatching { gattServer.stop() }
            serverStarted = false
        }
    }

    private fun requirePermissions() {
        val missing = BlePermissions.missing(context)
        check(missing.isEmpty()) {
            "Permisos de runtime no concedidos: ${missing.joinToString { it.substringAfterLast('.') }}. " +
                "La UI debe pedirlos antes de usar el transporte (ver BlePermissions.required())."
        }
    }

    companion object {
        // TODO(dueño=Helmut): reservar/registrar un UUID de servicio propio antes
        // de release; este es un valor de desarrollo, no oficial. DEBE seguir
        // siendo el mismo valor que BleGattProfile.SERVICE_UUID -- si divergen,
        // un cliente encuentra el beacon por scan pero no encuentra el servicio
        // GATT al conectarse (bug real que hubo aquí, corregido: ver
        // docs/validation/PHONE-READINESS.md).
        val SERVICE_UUID: ParcelUuid = ParcelUuid(BleGattProfile.SERVICE_UUID)

        // Constantes de ScanCallback: se copian en vez de referenciar
        // ScanCallback.SCAN_FAILED_* porque esos campos son `protected` en la clase
        // abstracta y no se pueden leer desde fuera de una subclase.
        const val SCAN_FAILED_ALREADY_STARTED = 1
        const val SCAN_FAILED_APPLICATION_REGISTRATION_FAILED = 2
        const val SCAN_FAILED_INTERNAL_ERROR = 3
        const val SCAN_FAILED_FEATURE_UNSUPPORTED = 4
        const val SCAN_FAILED_OUT_OF_HARDWARE_RESOURCES = 5
        const val SCAN_FAILED_SCANNING_TOO_FREQUENTLY = 6

        /** El sistema permite 5 `startScan` por ventana de 30 s. */
        const val THROTTLE_WINDOW_MS = 31_000L
        const val BACKOFF_BASE_MS = 1_000L

        fun describeScanError(code: Int): String = when (code) {
            SCAN_FAILED_ALREADY_STARTED -> "ya había un escaneo registrado para esta app"
            SCAN_FAILED_APPLICATION_REGISTRATION_FAILED -> "el sistema rechazó registrar la app para escanear"
            SCAN_FAILED_INTERNAL_ERROR -> "error interno del stack Bluetooth"
            SCAN_FAILED_FEATURE_UNSUPPORTED -> "este equipo no soporta el modo de escaneo pedido"
            SCAN_FAILED_OUT_OF_HARDWARE_RESOURCES -> "sin recursos de hardware (demasiados escaneos/conexiones)"
            SCAN_FAILED_SCANNING_TOO_FREQUENTLY ->
                "escaneos demasiado frecuentes: el sistema limita a 5 por cada 30 s"
            else -> "código de fallo de escaneo desconocido ($code)"
        }

        fun describeAdvertiseError(code: Int): String = when (code) {
            AdvertiseCallback.ADVERTISE_FAILED_DATA_TOO_LARGE ->
                "el paquete de anuncio excede el presupuesto del fabricante"
            AdvertiseCallback.ADVERTISE_FAILED_TOO_MANY_ADVERTISERS -> "demasiados anunciantes activos en el sistema"
            AdvertiseCallback.ADVERTISE_FAILED_ALREADY_STARTED -> "ya se estaba anunciando"
            AdvertiseCallback.ADVERTISE_FAILED_INTERNAL_ERROR -> "error interno del stack Bluetooth"
            AdvertiseCallback.ADVERTISE_FAILED_FEATURE_UNSUPPORTED ->
                "este equipo no soporta el rol periférico (no puede anunciarse)"
            else -> "código de fallo de anuncio desconocido ($code)"
        }
    }
}

/** Fallo de escaneo con la información que hace falta para decidir si reintentar. */
class BleScanException(
    val errorCode: Int?,
    val permanent: Boolean,
    message: String,
) : IllegalStateException(message)

/**
 * Eventos del radio que la UI necesita ver. Sin esto, los fallos de BLE son
 * invisibles: es la diferencia entre "no encuentra dispositivos" y "el Bluetooth
 * está apagado" / "esta tablet no puede anunciarse".
 */
sealed interface BleRadioEvent {
    data object ScanStarted : BleRadioEvent
    data object AdvertisingStarted : BleRadioEvent
    data class NotReady(val readiness: BleReadiness) : BleRadioEvent
    data class ScanFailed(val errorCode: Int, val reason: String) : BleRadioEvent
    data class ScanRetrying(val attempt: Long, val waitMs: Long, val reason: String) : BleRadioEvent
    data class AdvertisingFailed(val errorCode: Int, val reason: String) : BleRadioEvent
}
