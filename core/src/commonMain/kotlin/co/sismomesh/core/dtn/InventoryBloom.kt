package co.sismomesh.core.dtn

/**
 * Bloom filter de bundle_ids conocidos (m≈8192 bits, k=4, ~1 KB) — Sección 8.4.
 * Al encontrarse dos peers, intercambian filtros y solo se transfieren los faltantes.
 * Dueño: Helmut. Nunca usar solo para P0 sin reconciliación/ACK (falso positivo = bundle perdido).
 */
class InventoryBloom(private val bitCount: Int = 8192, private val hashCount: Int = 4) {
    private val bits = BooleanArray(bitCount)

    fun add(bundleId: ByteArray) {
        TODO("dueño=Helmut")
    }

    fun mightContain(bundleId: ByteArray): Boolean {
        TODO("dueño=Helmut")
    }

    fun serialize(): ByteArray {
        TODO("dueño=Helmut: empaquetar bits para caber en la MTU de BLE")
    }
}
