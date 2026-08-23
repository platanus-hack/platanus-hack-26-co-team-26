package co.helius.core.domain.service

import co.helius.core.domain.model.Bundle

/**
 * `BundleFactory` (construcción + firma de un Bundle) vive en androidMain,
 * no aquí — compone `BundleWireCodec` (protobuf) y `core/crypto` (Ed25519),
 * ambos JVM-only. Ver core/src/androidMain/kotlin/co/helius/core/domain/service/BundleFactory.kt.
 */

/**
 * Reconstruye causalidad sin reloj global, a partir del grafo de encuentros y
 * relojes vectoriales ligeros (Sección 8.5, "Tiempo sin sincronización global").
 * Dueño: Helmut (dominio) + Miguel (backend, Sección 12).
 *
 * Implementación actual: heurística determinista, NO vector clocks reales
 * todavía. Dentro de un mismo `nodeId`, `sequence` sí es una garantía de
 * causalidad real (el emisor los genera en orden). Entre nodos distintos, sin
 * reloj vectorial no hay garantía formal — se usa `createdAtMs` (declarado
 * por el emisor, no confiable, ver `BundleHeader.createdAtMs`) solo como
 * heurística de desempate. TODO(dueño=Helmut): sustituir por relojes
 * vectoriales reales derivados del grafo de encuentros
 * (`core/dtn/EncounterStateMachine`) antes de depender de este orden para
 * algo más que presentación/depuración.
 */
class CausalityResolver {
    fun resolve(bundles: List<Bundle>): List<Bundle> =
        bundles.sortedWith(
            compareBy<Bundle> { it.header.nodeId.value }
                .thenBy { it.header.sequence }
                .thenBy { it.header.createdAtMs },
        )
}
