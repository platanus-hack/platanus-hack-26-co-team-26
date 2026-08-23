package co.sismomesh.core.crypto

/** Identidad persistente Ed25519 (StrongBox si existe) + pseudónimo efímero por desastre. */
class IdentityManager {
    fun ed25519KeyPair(): Any = TODO("dueño=Helmut")
    fun ephemeralPseudonym(disasterId: String, epoch: Long): ByteArray = TODO("dueño=Helmut: HKDF(identidad, disaster_id, epoch)")
}

/** Handshake X25519 + HKDF, patrón tipo Noise XX (Sección 14.2). */
class Handshake {
    suspend fun perform(remotePublicKey: ByteArray): ByteArray = TODO("dueño=Helmut")
}

/** Cifrado de payload — ChaCha20-Poly1305 (o AES-GCM con aceleración HW). */
class PayloadCipher {
    fun encrypt(plaintext: ByteArray, key: ByteArray): ByteArray = TODO("dueño=Helmut")
    fun decrypt(ciphertext: ByteArray, key: ByteArray): ByteArray = TODO("dueño=Helmut")
}
