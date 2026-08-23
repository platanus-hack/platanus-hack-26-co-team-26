package co.helius.core.dtn

import co.helius.core.domain.model.Bundle
import kotlin.math.min

/**
 * score = w1*severity + w2*age + w3*battery_risk + w4*delivery_probability
 *       + w5*ttl_urgency - w6*replication_count
 *
 * Pesos configurables por incidente (protocol/docs/PRIORITIES.md, Sección 8.3);
 * el cloud los envía por DTN inversa (Sección 8.6). Dueño: Helmut.
 */
class ForwardingScorer(private val weights: PriorityWeights = PriorityWeights.default()) {

    fun score(bundle: Bundle, context: ForwardingContext): Double {
        val severity = severityOf(bundle) // 0..1, P0 más severo
        val ageNormalized = ageOf(bundle, context.nowMs) // 0..1, más viejo = más urgente hasta el tope
        val batteryRisk = if (context.batteryPercent <= 20) 1.0 else 0.0
        val deliveryProbability = context.deliveryProbability.coerceIn(0.0, 1.0)
        val ttlUrgency = ttlUrgencyOf(bundle, context.nowMs)
        val replicationPenalty = min(bundle.header.hopCount, 10) / 10.0

        return weights.severity * severity +
            weights.age * ageNormalized +
            weights.batteryRisk * batteryRisk +
            weights.deliveryProbability * deliveryProbability +
            weights.ttlUrgency * ttlUrgency -
            weights.replicationCount * replicationPenalty
    }

    private fun severityOf(bundle: Bundle): Double {
        // Priority.ordinal: 0=P0_LIFE_CRITICAL ... 5=P5_DIAGNOSTIC. Invertimos para que P0 -> 1.0.
        val maxOrdinal = 5.0
        return 1.0 - (bundle.header.priority.ordinal / maxOrdinal)
    }

    private fun ageOf(bundle: Bundle, nowMs: Long): Double {
        val ageMs = (nowMs - bundle.header.createdAtMs.toLong()).coerceAtLeast(0)
        val capMs = 10 * 60 * 1000.0 // 10 min: a partir de aquí la urgencia por edad ya está saturada
        return min(1.0, ageMs / capMs)
    }

    private fun ttlUrgencyOf(bundle: Bundle, nowMs: Long): Double {
        val remainingMs = (bundle.header.expiresAtMs.toLong() - nowMs).coerceAtLeast(0)
        val totalMs = (bundle.header.expiresAtMs.toLong() - bundle.header.createdAtMs.toLong()).coerceAtLeast(1)
        // Cuanto menos tiempo de vida le queda (proporcionalmente), más urgente.
        return 1.0 - (remainingMs.toDouble() / totalMs).coerceIn(0.0, 1.0)
    }
}

data class PriorityWeights(
    val severity: Double,
    val age: Double,
    val batteryRisk: Double,
    val deliveryProbability: Double,
    val ttlUrgency: Double,
    val replicationCount: Double,
) {
    companion object {
        /** Valores ASSUMED de arranque (README raíz § C.0) — recalibrar con datos, ver protocol/docs/PRIORITIES.md. */
        fun default() = PriorityWeights(
            severity = 0.35,
            age = 0.15,
            batteryRisk = 0.15,
            deliveryProbability = 0.20,
            ttlUrgency = 0.10,
            replicationCount = 0.20,
        )
    }
}

class ForwardingContext(
    val nowMs: Long,
    val batteryPercent: Int,
    val deliveryProbability: Double = 0.5,
)
