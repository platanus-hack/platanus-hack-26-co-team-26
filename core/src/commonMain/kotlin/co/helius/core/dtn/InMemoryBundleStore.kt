package co.helius.core.dtn

import co.helius.core.application.ports.BundleStorePort
import co.helius.core.domain.model.Bundle
import co.helius.core.domain.vo.BundleId
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.flow

/**
 * Adaptador fake de BundleStorePort (ver core/application/ports/DataPorts.kt) —
 * permite testear el motor DTN completo en JVM sin SQLDelight ni ningún
 * teléfono (ADR-0001). El adaptador real (SqlDelightStore) queda pendiente en
 * :android:storage.
 */
class InMemoryBundleStore : BundleStorePort {
    private val bundles = LinkedHashMap<String, Bundle>()

    override suspend fun save(bundle: Bundle) {
        bundles[keyOf(bundle.header.bundleId)] = bundle
    }

    override suspend fun get(id: BundleId): Bundle? = bundles[keyOf(id)]

    override suspend fun outbox(): Flow<Bundle> = flow {
        for (bundle in bundles.values.toList()) emit(bundle)
    }

    override suspend fun evict(id: BundleId) {
        bundles.remove(keyOf(id))
    }

    fun all(): List<Bundle> = bundles.values.toList()

    fun contains(id: BundleId): Boolean = bundles.containsKey(keyOf(id))

    private val hexChars = "0123456789abcdef"

    // Evita String.format (no garantizado en todos los targets KMP); portable a iosMain futuro.
    private fun keyOf(id: BundleId): String = buildString {
        for (b in id.bytes) {
            val v = b.toInt() and 0xff
            append(hexChars[v ushr 4])
            append(hexChars[v and 0x0f])
        }
    }
}
