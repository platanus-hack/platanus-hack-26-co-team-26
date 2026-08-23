package co.sismomesh.core.dtn

import co.sismomesh.core.domain.model.Bundle

/**
 * score = w1*severity + w2*age + w3*battery_risk + w4*delivery_probability
 *       + w5*ttl_urgency - w6*replication_count
 *
 * Pesos configurables por incidente, viven en protocol/docs/PRIORITIES.md (el cloud
 * los envía por DTN inversa, Sección 8.6). Dueño: Helmut.
 */
class ForwardingScorer(private val weights: PriorityWeights) {
    fun score(bundle: Bundle, context: ForwardingContext): Double {
        TODO("dueño=Helmut: Sección 8.3")
    }
}

data class PriorityWeights(
    val severity: Double,
    val age: Double,
    val batteryRisk: Double,
    val deliveryProbability: Double,
    val ttlUrgency: Double,
    val replicationCount: Double,
)

class ForwardingContext(val nowMs: Long, val batteryPercent: Int)
