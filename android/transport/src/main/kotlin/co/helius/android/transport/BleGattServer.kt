package co.helius.android.transport

import android.Manifest
import android.bluetooth.BluetoothDevice
import android.bluetooth.BluetoothGatt
import android.bluetooth.BluetoothGattCharacteristic
import android.bluetooth.BluetoothGattDescriptor
import android.bluetooth.BluetoothGattServer
import android.bluetooth.BluetoothGattServerCallback
import android.bluetooth.BluetoothManager
import android.content.Context
import androidx.annotation.RequiresPermission
import co.helius.core.application.ports.BundleStorePort
import co.helius.core.dtn.InventoryBloom
import co.helius.core.dtn.outboxSnapshot
import co.helius.core.protocol.BundleWireCodec.toDomainBundle
import co.helius.core.protocol.BundleWireCodec.toWire
import kotlinx.coroutines.CompletableDeferred
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.launch
import kotlinx.coroutines.withTimeoutOrNull
import java.util.concurrent.ConcurrentHashMap
import java.util.concurrent.atomic.AtomicInteger

/**
 * Lado servidor del intercambio GATT (Sección 8.1/8.4): acepta la conexión
 * que otro nodo inició, recibe su Bloom filter, le devuelve el propio y
 * empuja los bundles que le falten. Debe correr siempre que
 * `BleTransport.startAdvertising()` esté activo (se anuncia como conectable),
 * porque cualquier nodo puede iniciar la conexión hacia este teléfono.
 *
 * Soporta múltiples peers conectados a la vez: todo el estado por conexión
 * (reensambladores, MTU negociado, notificación pendiente) está indexado por
 * `device.address`, no en campos únicos — un solo `BleReassembler` compartido
 * mezclaría los chunks de dos peers distintos.
 */
class BleGattServer(
    private val context: Context,
    private val store: BundleStorePort,
    private val scope: CoroutineScope,
) {
    private var gattServer: BluetoothGattServer? = null
    private val inventoryReassemblers = ConcurrentHashMap<String, BleReassembler>()
    private val bundleReassemblers = ConcurrentHashMap<String, BleReassembler>()
    private val effectiveMtu = ConcurrentHashMap<String, Int>()
    private val pendingNotifications = ConcurrentHashMap<String, CompletableDeferred<Unit>>()
    private val nextMessageId = AtomicInteger(1)
    private val subscribedDevices = mutableSetOf<String>()

    @RequiresPermission(Manifest.permission.BLUETOOTH_CONNECT)
    fun start() {
        val manager = context.getSystemService(Context.BLUETOOTH_SERVICE) as BluetoothManager
        val server = manager.openGattServer(context, callback)
        server.addService(BleGattProfile.buildService())
        gattServer = server
    }

    @RequiresPermission(Manifest.permission.BLUETOOTH_CONNECT)
    fun stop() {
        gattServer?.close()
        gattServer = null
    }

    private val callback = object : BluetoothGattServerCallback() {
        override fun onConnectionStateChange(device: BluetoothDevice, status: Int, newState: Int) {
            if (newState == BluetoothGatt.STATE_DISCONNECTED) {
                subscribedDevices.remove(device.address)
                inventoryReassemblers.remove(device.address)
                bundleReassemblers.remove(device.address)
                effectiveMtu.remove(device.address)
                pendingNotifications.remove(device.address)
            }
        }

        override fun onMtuChanged(device: BluetoothDevice, mtu: Int) {
            effectiveMtu[device.address] = mtu
        }

        @RequiresPermission(Manifest.permission.BLUETOOTH_CONNECT)
        override fun onDescriptorWriteRequest(
            device: BluetoothDevice,
            requestId: Int,
            descriptor: BluetoothGattDescriptor,
            preparedWrite: Boolean,
            responseNeeded: Boolean,
            offset: Int,
            value: ByteArray,
        ) {
            if (descriptor.uuid == BleGattProfile.CLIENT_CHARACTERISTIC_CONFIG_UUID) {
                subscribedDevices += device.address
            }
            if (responseNeeded) {
                gattServer?.sendResponse(device, requestId, android.bluetooth.BluetoothGatt.GATT_SUCCESS, offset, value)
            }
        }

        @RequiresPermission(Manifest.permission.BLUETOOTH_CONNECT)
        override fun onCharacteristicWriteRequest(
            device: BluetoothDevice,
            requestId: Int,
            characteristic: BluetoothGattCharacteristic,
            preparedWrite: Boolean,
            responseNeeded: Boolean,
            offset: Int,
            value: ByteArray,
        ) {
            if (responseNeeded) {
                gattServer?.sendResponse(device, requestId, android.bluetooth.BluetoothGatt.GATT_SUCCESS, offset, value)
            }

            when (characteristic.uuid) {
                BleGattProfile.INVENTORY_CHARACTERISTIC_UUID -> {
                    val reassembler = inventoryReassemblers.getOrPut(device.address) { BleReassembler() }
                    val bloomBytes = reassembler.accept(value) ?: return
                    onClientInventoryReceived(device, bloomBytes)
                }
                BleGattProfile.BUNDLE_TRANSFER_CHARACTERISTIC_UUID -> {
                    val reassembler = bundleReassemblers.getOrPut(device.address) { BleReassembler() }
                    val bundleBytes = reassembler.accept(value) ?: return
                    scope.launch {
                        runCatching { bundleBytes.toDomainBundle() }
                            .onSuccess { store.save(it) }
                            // No tumbar la conexión por un bundle con payload aún no soportado
                            // (ver BundleWireCodec: Motion/Biomarker/Observation todavía NotImplementedError).
                            .onFailure { /* TODO(dueño=Helmut): registrar/telemetría, no propagar */ }
                    }
                }
            }
        }

        override fun onNotificationSent(device: BluetoothDevice, status: Int) {
            pendingNotifications[device.address]?.complete(Unit)
        }
    }

    @RequiresPermission(Manifest.permission.BLUETOOTH_CONNECT)
    private fun onClientInventoryReceived(device: BluetoothDevice, clientBloomBytes: ByteArray) {
        val clientBloom = InventoryBloom()
        clientBloom.mergeFrom(clientBloomBytes)

        scope.launch {
            val localBundles = store.outboxSnapshot()

            // 1) Nuestro propio Bloom filter, de vuelta al cliente (para que él calcule qué nos falta a nosotros).
            val localBloom = InventoryBloom()
            localBundles.forEach { localBloom.add(it.header.bundleId.bytes) }
            notifyChunked(device, BleGattProfile.INVENTORY_CHARACTERISTIC_UUID, localBloom.serialize())

            // 2) Los bundles que el cliente no tiene, empujados por notify.
            for (bundle in localBundles) {
                if (!clientBloom.mightContain(bundle.header.bundleId.bytes)) {
                    runCatching { bundle.toWire() }.onSuccess { wire ->
                        notifyChunked(device, BleGattProfile.BUNDLE_TRANSFER_CHARACTERISTIC_UUID, wire)
                    }
                    // Payloads sin codec todavía (Motion/Biomarker/Observation): se omiten en vez de crashear.
                }
            }
        }
    }

    /**
     * Envía cada chunk como una notificación GATT separada, esperando la
     * confirmación (`onNotificationSent`) antes de mandar el siguiente — la
     * pila BLE típicamente solo tolera una notificación en vuelo por
     * conexión; mandarlas todas seguidas sin esperar las hace descartarse en
     * hardware real (a diferencia de un bucle síncrono, que "funciona" en
     * cualquier mock/emulador sin BLE real detrás).
     */
    @RequiresPermission(Manifest.permission.BLUETOOTH_CONNECT)
    private suspend fun notifyChunked(device: BluetoothDevice, characteristicUuid: java.util.UUID, payload: ByteArray) {
        val server = gattServer ?: return
        if (device.address !in subscribedDevices) return // el cliente no habilitó notificaciones todavía
        val service = server.getService(BleGattProfile.SERVICE_UUID) ?: return
        val characteristic = service.getCharacteristic(characteristicUuid) ?: return

        val messageId = nextMessageId.getAndUpdate { (it % 0xffff) + 1 }
        // MTU real si ya se negoció (onMtuChanged), si no el mínimo BLE -- nunca por
        // encima del límite duro de ATT (512 B de valor de característica).
        val mtu = (effectiveMtu[device.address] ?: MIN_BLE_MTU) - ATT_OPCODE_OVERHEAD
        val maxChunkPayload = (mtu - BleChunking.HEADER_SIZE)
            .coerceAtLeast(1)
            .coerceAtMost(MAX_ATTRIBUTE_VALUE_LENGTH - BleChunking.HEADER_SIZE)
        for (chunk in BleChunking.chunk(messageId, payload, maxChunkPayload)) {
            val deferred = CompletableDeferred<Unit>()
            pendingNotifications[device.address] = deferred
            characteristic.value = chunk
            val queued = server.notifyCharacteristicChanged(device, characteristic, false)
            if (!queued) return // cola de notificaciones llena o desconectado; abortar este mensaje
            withTimeoutOrNull(NOTIFY_ACK_TIMEOUT_MS) { deferred.await() }
                ?: return // sin confirmación a tiempo: mejor abortar que seguir enviando a ciegas
        }
        pendingNotifications.remove(device.address)
    }

    companion object {
        // Límite duro de GATT (ATT), independiente del MTU negociado: nunca escribir
        // más de 512 B de valor de característica de una sola vez.
        private const val MAX_ATTRIBUTE_VALUE_LENGTH = 512
        private const val MIN_BLE_MTU = 23
        private const val ATT_OPCODE_OVERHEAD = 3
        private const val NOTIFY_ACK_TIMEOUT_MS = 5_000L
    }
}
