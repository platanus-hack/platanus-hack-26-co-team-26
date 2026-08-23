package co.sismomesh.core.domain.service

import co.sismomesh.core.domain.model.Bundle

/** Construye Bundle firmado a partir de un payload + identidad. Dueño: Helmut. */
class BundleFactory {
    fun create(payload: Any, signer: (ByteArray) -> ByteArray): Bundle = TODO("dueño=Helmut")
}

/**
 * Reconstruye causalidad sin reloj global, a partir del grafo de encuentros y relojes
 * vectoriales ligeros (Sección 8.5). Dueño: Helmut (dominio) + Miguel (backend, Sección 12).
 */
class CausalityResolver {
    fun resolve(bundles: List<Bundle>): List<Bundle> = TODO("dueño=Helmut")
}
