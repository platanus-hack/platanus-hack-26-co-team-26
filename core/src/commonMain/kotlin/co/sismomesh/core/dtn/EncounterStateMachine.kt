package co.sismomesh.core.dtn

import co.sismomesh.core.application.ports.BundleStorePort

/**
 * Secuencia de encuentro (Sección 7.2), objetivo TTFC < 4 s en modo T0:
 * advertise+scan → MAGIC/SESSION → handshake (X25519+HKDF, patrón Noise XX,
 * ver core/crypto) → negociación de capacidades → intercambio de inventarios
 * (Bloom filter) → transferencia priorizada T0→T1→T2 → ACK/delivery receipts
 * → registro de PeerObservation → desconexión limpia + backoff.
 *
 * `exchange()` implementa el corazón testeable de ese ciclo — el intercambio
 * de inventarios y el store-carry-forward resultante — sin necesitar la
 * negociación de transporte/cripto real, que la orquesta la app (androidMain)
 * llamando a esta función con los `BundleStorePort` de ambos lados una vez el
 * canal ya está autenticado. Dueño: Helmut. Testeado en JVM con `InMemoryBundleStore`.
 */
class EncounterStateMachine {
    // TODO(dueño=Helmut): este enum documenta la secuencia completa pero NO está
    // conectado todavía a ninguna transición real -- exchange() de abajo cubre
    // solo ExchangingInventory+Transferring de forma síncrona. Discovering/
    // Handshaking/NegotiatingCapabilities/Closing viven hoy fuera de esta clase
    // (BleTransport.observePeers()/connect(), core/crypto/Identity.kt). No
    // asumir que "existe el enum" significa "el ciclo de vida está implementado".
    sealed interface State {
        data object Idle : State
        data object Discovering : State
        data object Handshaking : State
        data object NegotiatingCapabilities : State
        data object ExchangingInventory : State
        data object Transferring : State
        data object Closing : State
    }

    /**
     * Intercambia inventarios (Bloom filter) entre dos nodos y transfiere a
     * cada lado los bundles que le faltan — store-carry-forward bidireccional
     * de la Sección 8.1. Deduplicado por `bundle_id`, sin reenviar lo que el
     * peer ya tiene (según su Bloom filter, con la tasa de falso positivo
     * documentada en README raíz § C.5).
     */
    suspend fun exchange(local: BundleStorePort, remote: BundleStorePort) {
        val localBundles = local.outboxSnapshot()
        val remoteBundles = remote.outboxSnapshot()

        val localBloom = InventoryBloom()
        localBundles.forEach { localBloom.add(it.header.bundleId.bytes) }

        val remoteBloom = InventoryBloom()
        remoteBundles.forEach { remoteBloom.add(it.header.bundleId.bytes) }

        for (bundle in localBundles) {
            if (!remoteBloom.mightContain(bundle.header.bundleId.bytes)) {
                remote.save(bundle)
            }
        }
        for (bundle in remoteBundles) {
            if (!localBloom.mightContain(bundle.header.bundleId.bytes)) {
                local.save(bundle)
            }
        }
    }
}
