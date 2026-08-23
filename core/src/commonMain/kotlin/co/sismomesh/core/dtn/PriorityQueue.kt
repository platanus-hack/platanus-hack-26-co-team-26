package co.sismomesh.core.dtn

import co.sismomesh.core.domain.model.Bundle

/**
 * Cola de reenvío ordenada por ForwardingScorer, con anti-flooding: max_copies por
 * bundle (estilo Spray-and-Wait), decreciente con hop_count. Dueño: Helmut.
 */
class PriorityQueue(private val scorer: ForwardingScorer) {
    fun enqueue(bundle: Bundle) {
        TODO("dueño=Helmut")
    }

    fun nextBatch(budgetBytes: Long): List<Bundle> {
        TODO("dueño=Helmut")
    }
}
