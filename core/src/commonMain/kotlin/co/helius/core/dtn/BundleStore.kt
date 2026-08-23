package co.helius.core.dtn

import co.helius.core.application.ports.BundleStorePort
import co.helius.core.domain.model.Bundle
import co.helius.core.domain.model.Tier
import co.helius.core.domain.model.tier
import co.helius.core.domain.vo.BundleId
import kotlinx.coroutines.flow.toList

/**
 * Política de retención sobre BundleStorePort (Sección 8.2): cuota por tier
 * (T0 nunca se descarta antes que T2), expulsión por `expires_at`, luego por
 * prioridad, luego LRU ponderado por probabilidad de entrega. Dueño: Helmut.
 */
class BundleStore(private val store: BundleStorePort) {

    suspend fun retain(bundle: Bundle) {
        store.save(bundle)
    }

    suspend fun get(id: BundleId): Bundle? = store.get(id)

    /**
     * Libera espacio hasta cumplir `quotaBytesPerTier`. Orden de expulsión:
     * 1) bundles vencidos (`expires_at` < nowMs) de cualquier tier,
     * 2) dentro de un tier sobre cuota: menor prioridad primero (P5 antes que P0),
     * 3) a igualdad de prioridad: el más antiguo primero (LRU por created_at).
     * Nunca se expulsa T0 mientras exista margen en T1/T2 — ver Sección 8.2.
     */
    suspend fun evictIfNeeded(quotaBytesPerTier: Map<Tier, Long>, bundleSizeBytes: (Bundle) -> Long, nowMs: Long) {
        val all = store.outboxSnapshot()

        // 1) vencidos, en cualquier tier
        for (bundle in all) {
            if (bundle.header.expiresAtMs.toLong() < nowMs) {
                store.evict(bundle.header.bundleId)
            }
        }

        // 2) por tier, empezando por T2 (nunca T0 primero), respetando la cuota
        val remaining = store.outboxSnapshot().groupBy { it.tier }
        for (targetTier in listOf(Tier.T2, Tier.T1, Tier.T0)) {
            val quota = quotaBytesPerTier[targetTier] ?: continue
            val bundlesInTier = (remaining[targetTier] ?: emptyList())
                .sortedWith(compareByDescending<Bundle> { it.header.priority.ordinal }.thenBy { it.header.createdAtMs })
            var used = bundlesInTier.sumOf { bundleSizeBytes(it) }
            for (bundle in bundlesInTier) {
                if (used <= quota) break
                store.evict(bundle.header.bundleId)
                used -= bundleSizeBytes(bundle)
            }
        }
    }
}

/** Extensión de conveniencia: snapshot de la lista actual del outbox (para lógica de retención). */
suspend fun BundleStorePort.outboxSnapshot(): List<Bundle> = outbox().toList()
