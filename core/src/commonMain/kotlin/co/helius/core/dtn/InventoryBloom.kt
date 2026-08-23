package co.helius.core.dtn

import kotlin.math.ln
import kotlin.math.roundToInt

/**
 * Bloom filter de bundle_ids conocidos (m≈8192 bits, k=4, ~1 KB) — Sección 8.4.
 * Al encontrarse dos peers, intercambian filtros y solo se transfieren los
 * faltantes. Dueño: Helmut. Nunca usar solo para P0 sin reconciliación/ACK
 * (falso positivo = bundle perdido, ver docs/architecture/OVERVIEW.md § 7).
 */
class InventoryBloom(private val bitCount: Int = 8192, private val hashCount: Int = 4) {
    private val bits = BooleanArray(bitCount)

    fun add(bundleId: ByteArray) {
        for (seed in 0 until hashCount) {
            bits[indexFor(bundleId, seed)] = true
        }
    }

    fun mightContain(bundleId: ByteArray): Boolean {
        for (seed in 0 until hashCount) {
            if (!bits[indexFor(bundleId, seed)]) return false
        }
        return true
    }

    /** Empaqueta los bits en bytes (LSB primero) — cabe en la MTU de BLE (~1 KB para m=8192). */
    fun serialize(): ByteArray {
        val out = ByteArray((bitCount + 7) / 8)
        for (i in 0 until bitCount) {
            if (bits[i]) out[i / 8] = (out[i / 8].toInt() or (1 shl (i % 8))).toByte()
        }
        return out
    }

    /** Fusión de dos filtros del mismo tamaño (unión de bits) — para acumular inventarios recibidos. */
    fun mergeFrom(serialized: ByteArray) {
        require(serialized.size == (bitCount + 7) / 8) { "Tamaño de filtro incompatible" }
        for (i in 0 until bitCount) {
            if ((serialized[i / 8].toInt() shr (i % 8)) and 1 == 1) bits[i] = true
        }
    }

    /**
     * Double hashing (Kirsch-Mitzenmacher): deriva k índices a partir de solo
     * dos hashes base, evita implementar k funciones hash independientes.
     */
    private fun indexFor(bundleId: ByteArray, seed: Int): Int {
        val h1 = fnv1a(bundleId, 0)
        val h2 = fnv1a(bundleId, 1)
        val combined = h1 + seed * h2
        return (combined.mod(bitCount))
    }

    private fun fnv1a(data: ByteArray, salt: Int): Int {
        var hash = -0x7ee3623b + salt * -0x61c88647 // offset basis mezclado con salt
        for (b in data) {
            hash = hash xor (b.toInt() and 0xff)
            hash *= 0x01000193 // FNV prime
        }
        return hash
    }

    companion object {
        /** k óptimo para n elementos esperados y m bits: k = (m/n)*ln(2) — ver README raíz § C.5. */
        fun optimalHashCount(bitCount: Int, expectedElements: Int): Int =
            ((bitCount.toDouble() / expectedElements) * ln(2.0)).roundToInt().coerceAtLeast(1)
    }
}
