package co.sismomesh.core.domain.model

import co.sismomesh.core.domain.vo.BundleId
import co.sismomesh.core.domain.vo.NodeId
import co.sismomesh.core.domain.vo.Priority

/**
 * Objeto lógico único que transportan todos los adaptadores (BLE, Wi-Fi Aware, Direct, Nearby, IP).
 * Generado desde protocol/proto/sismomesh/v1/bundle.proto — NUNCA se escribe a mano en producción.
 * Dueño: Helmut (motor DTN + contratos protocol/). Ver docs/protocol/PROTOCOL.md.
 */
data class Bundle(
    val header: BundleHeader,
    val payload: BundlePayload,
    val signature: ByteArray,
)

data class BundleHeader(
    val version: Int,
    val disasterId: String,
    val bundleId: BundleId,
    val nodeId: NodeId,
    val sequence: ULong,
    val createdAtMs: ULong,
    val expiresAtMs: ULong,
    val hopCount: Int,
    val priority: Priority,
    val clockEvidence: ClockEvidence,
)

/** monotónico + skew observado — ver Sección 8.5, "Tiempo sin sincronización global". */
data class ClockEvidence(val monotonicMs: Long, val observedSkewMs: Long?)

sealed interface BundlePayload {
    data class Status(val evidence: EmergencyStatus) : BundlePayload
    data class Motion(val evidence: Any /* TODO(dueño=Alex): MotionEvidence generado desde motion.proto */) : BundlePayload
    data class Biomarker(val evidence: Any /* TODO(dueño=Alex): BiomarkerEvidence — NUNCA "vitals" */) : BundlePayload
    data class Observation(val peerObservation: Any /* TODO(dueño=Helmut): PeerObservation */) : BundlePayload
    data class Raw(val chunk: ByteArray) : BundlePayload
    data class Responder(val message: ByteArray /* DTN inversa, ver 8.6 */) : BundlePayload
}

/** ResponseState — enum cerrado, NUNCA agregar DEAD/ALIVE/INJURED (Anexo B, vocabulario prohibido). */
enum class ResponseState { UNKNOWN, SAFE, NEEDS_HELP, TRAPPED, UNCONFIRMED, NO_RECENT_EVIDENCE }

/** Tiers de tamaño del protocolo (protocol/docs/PROTOCOL.md § Tiers). T0 nunca se descarta antes que T2 (core/dtn/BundleStore.kt). */
enum class Tier { T0, T1, T2 }

val BundlePayload.tier: Tier
    get() = when (this) {
        is BundlePayload.Status -> Tier.T0
        is BundlePayload.Responder -> Tier.T0
        is BundlePayload.Motion -> Tier.T1
        is BundlePayload.Biomarker -> Tier.T1
        is BundlePayload.Observation -> Tier.T1
        is BundlePayload.Raw -> Tier.T2
    }

val Bundle.tier: Tier get() = payload.tier
