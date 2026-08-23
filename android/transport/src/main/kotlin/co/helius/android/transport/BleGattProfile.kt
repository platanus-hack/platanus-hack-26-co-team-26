package co.helius.android.transport

import android.bluetooth.BluetoothGattCharacteristic
import android.bluetooth.BluetoothGattDescriptor
import android.bluetooth.BluetoothGattService
import java.util.UUID

/**
 * Esquema GATT para el intercambio de inventario (Bloom filter) y bundles
 * (Sección 7.2/8.1). Cada teléfono corre AMBOS roles a la vez: servidor
 * (`BleGattServer`, para cuando otro nodo se conecta a él) y cliente
 * (`BleGattClient`, para cuando él inicia la conexión) — cualquier nodo puede
 * ser "A" o "B" en un encuentro.
 *
 * TODO(dueño=Helmut): UUIDs de desarrollo, no oficiales — registrar antes de release.
 */
object BleGattProfile {
    // IMPORTANTE: este UUID de servicio es también el que se anuncia por BLE
    // (BleTransport.SERVICE_UUID toma este mismo valor -- deben ser idénticos,
    // ver el comentario en BleTransport). Sigue EXACTAMENTE el patrón de Base
    // UUID de Bluetooth SIG (grupo 2 = "0000", grupos 3-5 = los de la base
    // estándar) para que el stack de Android lo comprima a 16 bits (2 B) en el
    // advertising -- si el grupo 2 no es "0000" no se comprime y el beacon de
    // 23 B ya no cabe en los 31 B de legacy advertising. Las características,
    // que nunca se anuncian, no tienen esa restricción.
    val SERVICE_UUID: UUID = UUID.fromString("0000f5a5-0000-1000-8000-00805f9b34fb")

    /** Write (cliente→servidor): Bloom filter del cliente. Notify (servidor→cliente): Bloom filter del servidor. */
    val INVENTORY_CHARACTERISTIC_UUID: UUID = UUID.fromString("6ac05a10-f5a5-4b1e-9c3a-0f1e6a2b3c01")

    /** Write (cliente→servidor) + Notify (servidor→cliente): bundles en tránsito, en chunks (ver BleChunking). */
    val BUNDLE_TRANSFER_CHARACTERISTIC_UUID: UUID = UUID.fromString("6ac05a10-f5a5-4b1e-9c3a-0f1e6a2b3c02")

    /** Descriptor estándar para habilitar notificaciones (0x2902) — igual en todo dispositivo BLE. */
    val CLIENT_CHARACTERISTIC_CONFIG_UUID: UUID = UUID.fromString("00002902-0000-1000-8000-00805f9b34fb")

    /**
     * Ambas características son bidireccionales: WRITE (cliente→servidor) +
     * NOTIFY (servidor→cliente) con su propio CCCD. El protocolo completo
     * (ver BleGattClient/BleGattServer) es simétrico: cada lado escribe su
     * Bloom filter y recibe por notify el del otro, y cada lado empuja por
     * notify los bundles que el otro no tiene y recibe por write los que le
     * faltan a él.
     */
    fun buildService(): BluetoothGattService {
        val service = BluetoothGattService(SERVICE_UUID, BluetoothGattService.SERVICE_TYPE_PRIMARY)
        service.addCharacteristic(notifiableWritableCharacteristic(INVENTORY_CHARACTERISTIC_UUID))
        service.addCharacteristic(notifiableWritableCharacteristic(BUNDLE_TRANSFER_CHARACTERISTIC_UUID))
        return service
    }

    private fun notifiableWritableCharacteristic(uuid: UUID): BluetoothGattCharacteristic {
        val characteristic = BluetoothGattCharacteristic(
            uuid,
            BluetoothGattCharacteristic.PROPERTY_WRITE or BluetoothGattCharacteristic.PROPERTY_NOTIFY,
            BluetoothGattCharacteristic.PERMISSION_WRITE,
        )
        characteristic.addDescriptor(
            BluetoothGattDescriptor(
                CLIENT_CHARACTERISTIC_CONFIG_UUID,
                BluetoothGattDescriptor.PERMISSION_READ or BluetoothGattDescriptor.PERMISSION_WRITE,
            ),
        )
        return characteristic
    }
}
