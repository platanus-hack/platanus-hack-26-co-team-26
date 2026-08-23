package co.helius.android.transport

import android.bluetooth.BluetoothDevice
import android.bluetooth.BluetoothGatt
import android.bluetooth.BluetoothGattCallback
import android.bluetooth.BluetoothGattCharacteristic
import android.bluetooth.BluetoothGattDescriptor
import android.bluetooth.BluetoothProfile
import android.content.Context
import co.helius.core.application.ports.BundleStorePort
import co.helius.core.domain.vo.PeerId
import co.helius.core.domain.vo.PeerLink
import co.helius.core.dtn.InventoryBloom
import co.helius.core.dtn.outboxSnapshot
import co.helius.core.protocol.BundleWireCodec.toDomainBundle
import co.helius.core.protocol.BundleWireCodec.toWire
import kotlinx.coroutines.CompletableDeferred
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.launch
import kotlinx.coroutines.suspendCancellableCoroutine
import kotlinx.coroutines.withTimeoutOrNull
import kotlin.coroutines.resume
import kotlin.coroutines.resumeWithException

/**
 * Lado cliente del encuentro GATT completo: conectar → descubrir servicios →
 * habilitar notificaciones en ambas características → escribir el Bloom
 * filter propio (chunked) → recibir el del servidor + los bundles que el
 * servidor empuje → responder escribiendo los bundles que al servidor le
 * falten. Un único `BluetoothGattCallback` (la plataforma no admite más de
 * uno por conexión) cubre todo el ciclo — por eso vive aquí y no repartido
 * entre `BleTransport.connect()` y una clase de sync separada.
 *
 * `connectAndSync()` no retorna hasta que el intercambio completo termina (o
 * falla/expira) — a diferencia de `TransportPort.connect()`, que solo
 * garantiza el enlace. Dueño: Helmut.
 */
class BleGattClient(
    private val context: Context,
    private val scope: CoroutineScope,
) {
    suspend fun connectAndSync(
        device: BluetoothDevice,
        localStore: BundleStorePort,
        timeoutMs: Long = 15_000,
    ): PeerLink {
        val result = withTimeoutOrNull(timeoutMs) { runSync(device, localStore) }
        return result ?: throw IllegalStateException("Encuentro BLE con ${device.address} agotó el tiempo")
    }

    private suspend fun runSync(device: BluetoothDevice, localStore: BundleStorePort): PeerLink =
        suspendCancellableCoroutine { cont ->
            val session = Session(localStore, cont)
            val gatt = device.connectGatt(context, false, session.callback)
            cont.invokeOnCancellation { runCatching { gatt.close() } }
        }

    /** Encapsula el estado mutable de UN encuentro (un objeto por llamada a connectAndSync). */
    private inner class Session(
        private val localStore: BundleStorePort,
        private val cont: kotlin.coroutines.Continuation<PeerLink>,
    ) {
        private val inventoryReassembler = BleReassembler()
        private val bundleReassembler = BleReassembler()
        private var gattRef: BluetoothGatt? = null
        private var pendingOp: CompletableDeferred<Unit>? = null
        private var descriptorsEnabled = 0
        @Volatile private var finished = false

        val callback = object : BluetoothGattCallback() {
            override fun onConnectionStateChange(gatt: BluetoothGatt, status: Int, newState: Int) {
                if (newState == BluetoothProfile.STATE_CONNECTED && status == BluetoothGatt.GATT_SUCCESS) {
                    gattRef = gatt
                    gatt.discoverServices()
                } else {
                    finishWithError(gatt, "Conexión GATT terminó, status=$status newState=$newState")
                }
            }

            override fun onServicesDiscovered(gatt: BluetoothGatt, status: Int) {
                if (status != BluetoothGatt.GATT_SUCCESS) {
                    finishWithError(gatt, "Descubrimiento de servicios falló, status=$status")
                    return
                }
                scope.launch { enableNotificationsThenSync(gatt) }
            }

            override fun onDescriptorWrite(gatt: BluetoothGatt, descriptor: BluetoothGattDescriptor, status: Int) {
                pendingOp?.complete(Unit)
            }

            override fun onCharacteristicWrite(gatt: BluetoothGatt, characteristic: BluetoothGattCharacteristic, status: Int) {
                pendingOp?.complete(Unit)
            }

            // OJO: NO usar la sobrecarga de 3 argumentos (gatt, characteristic, ByteArray)
            // -- es API 33+. Con minSdk 26, si solo se implementa esa, este callback
            // NUNCA se dispara en API < 33 (el framework llama a la de 2 argumentos,
            // que si no está sobreescrita usa la implementación no-op de la clase base)
            // y toda la recepción por notify se cuelga en silencio. La de 2 argumentos
            // sí la invoca el framework en todas las API levels (en 33+ por delegación
            // interna), así que es la única compatible con todo el rango de minSdk.
            @Suppress("DEPRECATION")
            override fun onCharacteristicChanged(gatt: BluetoothGatt, characteristic: BluetoothGattCharacteristic) {
                val value = characteristic.value ?: return
                when (characteristic.uuid) {
                    BleGattProfile.INVENTORY_CHARACTERISTIC_UUID -> {
                        val bloomBytes = inventoryReassembler.accept(value) ?: return
                        scope.launch { onServerInventoryReceived(gatt, bloomBytes) }
                    }
                    BleGattProfile.BUNDLE_TRANSFER_CHARACTERISTIC_UUID -> {
                        val bundleBytes = bundleReassembler.accept(value) ?: return
                        scope.launch {
                            runCatching { bundleBytes.toDomainBundle() }
                                .onSuccess { localStore.save(it) }
                                .onFailure { /* TODO(dueño=Helmut): telemetría — payload sin codec todavía */ }
                        }
                    }
                }
            }
        }

        private suspend fun enableNotificationsThenSync(gatt: BluetoothGatt) {
            val service = gatt.getService(BleGattProfile.SERVICE_UUID) ?: return finishWithError(gatt, "Servicio HELIUS no encontrado en el peer")
            val inventoryChar = service.getCharacteristic(BleGattProfile.INVENTORY_CHARACTERISTIC_UUID)
            val bundleChar = service.getCharacteristic(BleGattProfile.BUNDLE_TRANSFER_CHARACTERISTIC_UUID)
            if (inventoryChar == null || bundleChar == null) return finishWithError(gatt, "Características HELIUS incompletas en el peer")

            enableNotification(gatt, inventoryChar)
            enableNotification(gatt, bundleChar)

            // Bloom filter propio, chunked, al servidor.
            val localBundles = localStore.outboxSnapshot()
            val localBloom = InventoryBloom()
            localBundles.forEach { localBloom.add(it.header.bundleId.bytes) }
            writeChunked(gatt, inventoryChar, localBloom.serialize())

            // Resolvemos aquí: el enlace ya sirve para que el llamador siga adelante;
            // la recepción de bundles/bloom del servidor sigue llegando por notify
            // de forma asíncrona (onCharacteristicChanged) mientras la conexión viva.
            if (!finished) {
                finished = true
                cont.resume(PeerLink(peer = PeerId(gatt.device.address), transport = "BLE", establishedAtMs = System.currentTimeMillis()))
            }
        }

        private suspend fun onServerInventoryReceived(gatt: BluetoothGatt, serverBloomBytes: ByteArray) {
            val serverBloom = InventoryBloom()
            serverBloom.mergeFrom(serverBloomBytes)
            val service = gatt.getService(BleGattProfile.SERVICE_UUID) ?: return
            val bundleChar = service.getCharacteristic(BleGattProfile.BUNDLE_TRANSFER_CHARACTERISTIC_UUID) ?: return

            for (bundle in localStore.outboxSnapshot()) {
                if (!serverBloom.mightContain(bundle.header.bundleId.bytes)) {
                    runCatching { bundle.toWire() }.onSuccess { wire -> writeChunked(gatt, bundleChar, wire) }
                }
            }
        }

        private suspend fun enableNotification(gatt: BluetoothGatt, characteristic: BluetoothGattCharacteristic) {
            gatt.setCharacteristicNotification(characteristic, true)
            val descriptor = characteristic.getDescriptor(BleGattProfile.CLIENT_CHARACTERISTIC_CONFIG_UUID) ?: return
            val deferred = CompletableDeferred<Unit>()
            pendingOp = deferred
            @Suppress("DEPRECATION")
            descriptor.value = BluetoothGattDescriptor.ENABLE_NOTIFICATION_VALUE
            @Suppress("DEPRECATION")
            gatt.writeDescriptor(descriptor)
            withTimeoutOrNull(OP_TIMEOUT_MS) { deferred.await() }
        }

        private suspend fun writeChunked(gatt: BluetoothGatt, characteristic: BluetoothGattCharacteristic, payload: ByteArray) {
            val messageId = (0..0xfffe).random() // suficiente para no colisionar con la única transferencia en curso
            val mtu = NEGOTIATED_MTU_FALLBACK - 3 // 3 B de overhead ATT
            val maxChunkPayload = (mtu - BleChunking.HEADER_SIZE).coerceAtLeast(1)
            for (chunk in BleChunking.chunk(messageId, payload, maxChunkPayload)) {
                val deferred = CompletableDeferred<Unit>()
                pendingOp = deferred
                @Suppress("DEPRECATION")
                characteristic.value = chunk
                @Suppress("DEPRECATION")
                val queued = gatt.writeCharacteristic(characteristic)
                if (!queued) return
                withTimeoutOrNull(OP_TIMEOUT_MS) { deferred.await() } ?: return
            }
        }

        private fun finishWithError(gatt: BluetoothGatt, message: String) {
            runCatching { gatt.close() }
            if (!finished) {
                finished = true
                cont.resumeWithException(IllegalStateException(message))
            }
        }
    }

    companion object {
        private const val OP_TIMEOUT_MS = 5_000L
        // MTU por defecto de BLE si nunca se negoció uno mayor -- ver BleChunking.
        // TODO(dueño=Helmut): llamar gatt.requestMtu() antes de escribir y usar el
        // valor real reportado en onMtuChanged en vez de este fallback conservador.
        private const val NEGOTIATED_MTU_FALLBACK = 23
    }
}
