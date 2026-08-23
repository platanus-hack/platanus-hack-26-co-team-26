package co.sismomesh.core.dtn

import co.sismomesh.core.application.ports.BundleStorePort
import co.sismomesh.core.domain.model.Bundle
import co.sismomesh.core.domain.vo.BundleId

/**
 * Motor DTN — 100% Kotlin puro, testeable en JVM sin ningún teléfono (Sección 8.1).
 * Dueño: Helmut. Retención por cuota de tier (T0 nunca se descarta antes que T2),
 * expulsión por expires_at, luego por priority, luego LRU ponderado por probabilidad de entrega.
 */
class BundleStore(private val store: BundleStorePort) {
    suspend fun retain(bundle: Bundle) {
        TODO("dueño=Helmut: política de retención por tier/expiración/prioridad, Sección 8.2")
    }

    suspend fun evictIfNeeded(quotaBytesPerTier: Map<Int, Long>) {
        TODO("dueño=Helmut")
    }

    suspend fun get(id: BundleId): Bundle? = store.get(id)
}
