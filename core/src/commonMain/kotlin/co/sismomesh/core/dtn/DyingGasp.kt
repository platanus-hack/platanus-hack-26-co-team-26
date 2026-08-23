package co.sismomesh.core.dtn

import co.sismomesh.core.application.ports.BundleStorePort
import co.sismomesh.core.application.ports.TransportPort
import co.sismomesh.core.domain.model.Bundle
import co.sismomesh.core.domain.vo.PeerLink
import kotlinx.coroutines.flow.firstOrNull
import kotlinx.coroutines.withTimeoutOrNull

/**
 * Antes de entrar en <5% de batería, el nodo intenta volcar su estado completo
 * a cualquier vecino alcanzable — último intento, sin reintentos ni backoff
 * (Sección 7.5). `transferAll` es la mecánica real de transferencia (la
 * ejecuta `EncounterStateMachine` en el flujo normal); aquí solo se orquesta
 * el disparo de emergencia. Dueño: Helmut.
 */
class DyingGasp(
    private val transport: TransportPort,
    private val store: BundleStorePort,
    private val transferAll: suspend (PeerLink, List<Bundle>) -> Unit,
) {
    suspend fun trigger(discoveryTimeoutMs: Long = 5_000) {
        val bundles = store.outboxSnapshot()
        if (bundles.isEmpty()) return

        val sighting = withTimeoutOrNull(discoveryTimeoutMs) { transport.observePeers().firstOrNull() } ?: return
        val link = transport.connect(sighting.peer)
        transferAll(link, bundles)
    }
}
