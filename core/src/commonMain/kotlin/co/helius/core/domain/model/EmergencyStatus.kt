package co.helius.core.domain.model

import co.helius.core.domain.vo.Battery
import co.helius.core.domain.vo.GeoPoint

/**
 * Estado de emergencia declarado por el usuario o inferido con evidencia (nunca "vitals").
 * Vocabulario obligatorio: "Análisis e Interpretación de Biomarcadores (AIB)" — ver docs/glossary.md.
 */
data class EmergencyStatus(
    val location: GeoPoint?,
    val timestampMs: Long,
    val source: String,
    val responseState: ResponseState,
    val battery: Battery,
    val deviceState: String,
    val evidenceRefs: List<String> = emptyList(),
)

/** Node y Evidence — modelos de dominio referenciados por casos de uso (Sección 4.3). */
data class Node(val id: co.helius.core.domain.vo.NodeId, val publicKey: ByteArray, val firstSeenMs: Long, val lastSeenMs: Long)

sealed interface Evidence {
    data class Motion(val purposefulMotionConfidence: Double) : Evidence
    data class Biomarker(val pulseBpm: Double?, val sqi: Double) : Evidence
    data class UserReport(val responseState: ResponseState) : Evidence
}
