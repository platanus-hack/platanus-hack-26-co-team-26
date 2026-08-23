package co.sismomesh.core.dtn

import co.sismomesh.core.domain.model.Bundle
import co.sismomesh.core.domain.vo.BundleId

/**
 * Cola de reenvío ordenada por ForwardingScorer, con anti-flooding: max_copies
 * por bundle (estilo Spray-and-Wait), decreciente con hop_count. Dueño: Helmut.
 */
class PriorityQueue(
    private val scorer: ForwardingScorer = ForwardingScorer(),
    private val maxCopies: Int = 5,
) {
    private val pending = LinkedHashMap<String, Bundle>()
    private val copiesSent = HashMap<String, Int>()

    fun enqueue(bundle: Bundle) {
        pending[keyOf(bundle.header.bundleId)] = bundle
    }

    fun remove(id: BundleId) {
        pending.remove(keyOf(id))
    }

    /** Marca que se envió una copia a un peer; una vez alcanzado max_copies el bundle deja de reenviarse (anti-flooding). */
    fun recordCopySent(id: BundleId) {
        val key = keyOf(id)
        copiesSent[key] = (copiesSent[key] ?: 0) + 1
    }

    fun copiesRemaining(id: BundleId): Int = (maxCopies - (copiesSent[keyOf(id)] ?: 0)).coerceAtLeast(0)

    /**
     * Siguiente lote a transferir, ordenado por score descendente, respetando
     * un presupuesto de bytes y excluyendo bundles que ya agotaron max_copies.
     */
    fun nextBatch(budgetBytes: Long, bundleSizeBytes: (Bundle) -> Long, context: ForwardingContext): List<Bundle> {
        val eligible = pending.values.filter { copiesRemaining(it.header.bundleId) > 0 }
        val ordered = eligible.sortedByDescending { scorer.score(it, context) }
        val batch = mutableListOf<Bundle>()
        var used = 0L
        for (bundle in ordered) {
            val size = bundleSizeBytes(bundle)
            if (used + size > budgetBytes) continue
            batch += bundle
            used += size
        }
        return batch
    }

    fun size(): Int = pending.size

    private fun keyOf(id: BundleId): String = buildString {
        val hexChars = "0123456789abcdef"
        for (b in id.bytes) {
            val v = b.toInt() and 0xff
            append(hexChars[v ushr 4])
            append(hexChars[v and 0x0f])
        }
    }
}
