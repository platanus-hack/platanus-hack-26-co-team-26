package co.helius.core.domain.service

import co.helius.core.crypto.BundleSigner
import co.helius.core.domain.model.Bundle
import co.helius.core.domain.model.BundleHeader
import co.helius.core.domain.model.BundlePayload
import co.helius.core.domain.model.ClockEvidence
import co.helius.core.domain.vo.BundleId
import co.helius.core.domain.vo.NodeId
import co.helius.core.domain.vo.Priority
import co.helius.core.protocol.BundleWireCodec.toWire
import java.security.MessageDigest

/**
 * Construye un Bundle firmado a partir de un payload + identidad (Sección 6.3).
 * Vive en androidMain (no en commonMain) porque compone `BundleWireCodec`
 * (protobuf) y `core/crypto` (firma Ed25519), ambos JVM-only por las mismas
 * razones documentadas en esos módulos — ver core/src/iosMain/README.md.
 * Dueño: Helmut.
 */
class BundleFactory(private val signer: BundleSigner) {

    /**
     * `bundle_id` se deriva de `disasterId + nodeId + sequence + createdAtMs`
     * (SHA-256 truncado a 16 B), no de un hash del payload serializado: eso
     * evita el problema del huevo y la gallina (el payload no puede hashearse
     * antes de tener un `Bundle` completo con el que serializar) y es además
     * la práctica estándar de identidad de bundle en DTN (RFC 9171 § 4.2.5:
     * nodo origen + timestamp de creación + secuencia, no hash de contenido).
     */
    suspend fun create(
        payload: BundlePayload,
        disasterId: String,
        nodeId: NodeId,
        sequence: ULong,
        priority: Priority,
        nowMs: ULong,
        ttlMs: ULong,
        clockEvidence: ClockEvidence,
    ): Bundle {
        val bundleId = deriveBundleId(disasterId, nodeId, sequence, nowMs)
        val header = BundleHeader(
            version = 1,
            disasterId = disasterId,
            bundleId = bundleId,
            nodeId = nodeId,
            sequence = sequence,
            createdAtMs = nowMs,
            expiresAtMs = nowMs + ttlMs,
            hopCount = 0,
            priority = priority,
            clockEvidence = clockEvidence,
        )

        // Bundle "sin firmar" (signature vacía) para poder serializar header+payload
        // y firmar sobre esos bytes exactos -- ver Sección 6.3/14.2: Sign_Kpriv(SHA-256(header||payload)).
        // BundleSigner.sign(a, b) = Sign(SHA-256(a+b)); como el protobuf ya serializa
        // header y payload juntos en un solo blob, va todo en el primer argumento.
        val unsigned = Bundle(header, payload, signature = ByteArray(0))
        val serializedHeaderAndPayload = unsigned.toWire()
        val signature = signer.sign(serializedHeaderAndPayload, ByteArray(0))

        return Bundle(header, payload, signature)
    }

    private fun deriveBundleId(disasterId: String, nodeId: NodeId, sequence: ULong, createdAtMs: ULong): BundleId {
        val input = "$disasterId|${nodeId.value}|$sequence|$createdAtMs".encodeToByteArray()
        val digest = MessageDigest.getInstance("SHA-256").digest(input)
        return BundleId(digest.copyOfRange(0, 16))
    }
}
