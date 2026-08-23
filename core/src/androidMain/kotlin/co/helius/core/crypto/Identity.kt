package co.helius.core.crypto

import co.helius.core.application.ports.IdentityPort
import co.helius.core.platform.secureRandomBytes
import java.security.KeyFactory

import java.security.KeyPairGenerator
import java.security.PrivateKey
import java.security.PublicKey
import java.security.Signature
import java.security.spec.NamedParameterSpec
import java.security.spec.XECPublicKeySpec

/**
 * Identidad persistente Ed25519 (Sección 14.2). Adaptador real de IdentityPort
 * (core/application/ports/SystemPorts.kt) — vive en androidMain porque usa
 * javax.crypto/java.security, JVM-only (ver core/src/iosMain/README.md).
 *
 * TODO(dueño=Helmut, antes de producción): respaldar con Android Keystore
 * (StrongBox si existe) en vez de mantener la clave en memoria/heap Java —
 * ver docs/security/THREAT-MODEL.md § Criptografía. Esta clase es la base
 * funcional; el `KeyStore`-backing es un paso de hardening posterior.
 *
 * NOTA DE COMPATIBILIDAD: "Ed25519"/"X25519" via java.security requieren un
 * proveedor JCA que los soporte. En JVM de escritorio (usado para tests, ver
 * ADR-0001: "todo el motor DTN se testea en JVM") funcionan out-of-the-box
 * desde JDK 15+. En Android, la disponibilidad por API level debe verificarse
 * en la matriz de dispositivos (docs/validation/VALIDATION.md); si un
 * dispositivo no expone estos algoritmos, la mitigación documentada es sumar
 * BouncyCastle como proveedor JCA adicional — no reinventar la primitiva.
 */
class Ed25519Identity private constructor(
    private val privateKey: PrivateKey,
    val publicKeyBytes: ByteArray,
) : IdentityPort {

    override suspend fun ed25519PublicKey(): ByteArray = publicKeyBytes

    override suspend fun sign(data: ByteArray): ByteArray {
        val signature = Signature.getInstance("Ed25519")
        signature.initSign(privateKey)
        signature.update(data)
        return signature.sign()
    }

    companion object {
        /** Genera una identidad nueva. Un nodo real la genera una sola vez y la persiste. */
        fun generate(): Ed25519Identity {
            val kpg = KeyPairGenerator.getInstance("Ed25519")
            val kp = kpg.generateKeyPair()
            val rawPublic = extractRawEd25519PublicKey(kp.public)
            return Ed25519Identity(kp.private, rawPublic)
        }

        /**
         * Extrae los 32 bytes crudos de la clave pública Ed25519 desde su
         * codificación X.509/DER (java.security no expone getters directos).
         * El punto Ed25519 son los últimos 32 bytes del encoded (SubjectPublicKeyInfo).
         */
        private fun extractRawEd25519PublicKey(publicKey: PublicKey): ByteArray {
            val encoded = publicKey.encoded
            return encoded.copyOfRange(encoded.size - 32, encoded.size)
        }
    }
}

/**
 * `HKDF(identidad, disaster_id, epoch)` — Sección 14.2. El pseudónimo cambia
 * por desastre y por época (rotación), nunca es el mismo identificador entre
 * emergencias — evita el rastreo de personas en tiempos normales (Sección 14.1).
 */
object PseudonymDeriver {
    fun derive(identitySeed: ByteArray, disasterId: String, epoch: Long): ByteArray {
        val info = "helius-pseudonym-v1:$disasterId:$epoch".encodeToByteArray()
        return Hkdf.deriveKey(ikm = identitySeed, salt = ByteArray(0), info = info, length = 8)
    }
}

/**
 * Handshake X25519 + HKDF, patrón tipo Noise XX simplificado (Sección 14.2):
 * ambos lados generan un par efímero, calculan el secreto compartido ECDH y
 * derivan una clave de sesión con HKDF sobre una transcripción del handshake
 * (evita que un shared secret crudo se use directo como clave).
 */
class X25519Handshake {
    fun generateEphemeralKeyPair(): java.security.KeyPair =
        KeyPairGenerator.getInstance("X25519").generateKeyPair()

    /** Reconstruye una clave pública X25519 desde 32 bytes crudos (u-coordinate). */
    fun publicKeyFromRaw(raw: ByteArray): PublicKey {
        require(raw.size == 32) { "X25519 public key debe ser 32 bytes" }
        val u = java.math.BigInteger(1, raw.reversedArray()) // little-endian -> BigInteger
        val spec = XECPublicKeySpec(NamedParameterSpec.X25519, u)
        return KeyFactory.getInstance("X25519").generatePublic(spec)
    }

    fun sharedSecret(ownPrivate: PrivateKey, remotePublic: PublicKey): ByteArray {
        // "XDH" (no "X25519") es el nombre de algoritmo documentado para KeyAgreement
        // desde JDK 11 (JEP 324); la curva ya queda fijada por las claves (NamedParameterSpec.X25519).
        val ka = javax.crypto.KeyAgreement.getInstance("XDH")
        ka.init(ownPrivate)
        ka.doPhase(remotePublic, true)
        return ka.generateSecret()
    }

    /**
     * Deriva la clave de sesión (32 bytes, para ChaCha20-Poly1305) a partir del
     * secreto compartido y una transcripción (p. ej. ambas claves públicas
     * efímeras concatenadas) para *key confirmation* implícita.
     */
    fun deriveSessionKey(sharedSecret: ByteArray, transcript: ByteArray): ByteArray =
        Hkdf.deriveKey(ikm = sharedSecret, salt = transcript, info = "helius-session-v1".encodeToByteArray(), length = 32)

    /** Extrae los 32 bytes crudos (u-coordinate) de una clave pública X25519 generada por la JVM. */
    fun rawPublicKey(publicKey: PublicKey): ByteArray {
        val encoded = publicKey.encoded
        return encoded.copyOfRange(encoded.size - 32, encoded.size)
    }

    /**
     * Handshake completo de un lado: genera par efímero propio, deriva la
     * clave de sesión contra la pública remota. Devuelve (miPúblicaEfímeraRaw,
     * claveDeSesión) — el llamador (EncounterStateMachine) debe enviar la
     * primera al peer para que éste pueda derivar la misma clave de sesión.
     *
     * TODO(dueño=Helmut): `IdentityPort`/`Handshake` en
     * core/application/ports/SystemPorts.kt declara `perform(): ByteArray`
     * (solo la clave de sesión) — ampliar el puerto para exponer también la
     * pública efímera propia, o resolverlo en el llamador con este método.
     */
    fun performReturningOwnPublic(remotePublicKeyRaw: ByteArray): Pair<ByteArray, ByteArray> {
        val ephemeral = generateEphemeralKeyPair()
        val ownPublicRaw = rawPublicKey(ephemeral.public)
        val remotePublic = publicKeyFromRaw(remotePublicKeyRaw)
        val secret = sharedSecret(ephemeral.private, remotePublic)
        val sessionKey = deriveSessionKey(secret, ownPublicRaw + remotePublicKeyRaw)
        return ownPublicRaw to sessionKey
    }

    fun perform(remotePublicKeyRaw: ByteArray): ByteArray = performReturningOwnPublic(remotePublicKeyRaw).second
}

/** Cifrado de payload — ChaCha20-Poly1305 (Sección 14.2). Nonce de 12 bytes, aleatorio, prependido al ciphertext. */
class PayloadCipher {
    fun encrypt(plaintext: ByteArray, key: ByteArray, associatedData: ByteArray = ByteArray(0)): ByteArray {
        require(key.size == 32) { "Clave ChaCha20-Poly1305 debe ser 32 bytes" }
        val nonce = secureRandomBytes(12)
        val cipher = javax.crypto.Cipher.getInstance("ChaCha20-Poly1305")
        val secretKey = javax.crypto.spec.SecretKeySpec(key, "ChaCha20")
        cipher.init(javax.crypto.Cipher.ENCRYPT_MODE, secretKey, javax.crypto.spec.IvParameterSpec(nonce))
        if (associatedData.isNotEmpty()) cipher.updateAAD(associatedData)
        val ciphertext = cipher.doFinal(plaintext)
        return nonce + ciphertext
    }

    fun decrypt(payload: ByteArray, key: ByteArray, associatedData: ByteArray = ByteArray(0)): ByteArray {
        require(key.size == 32) { "Clave ChaCha20-Poly1305 debe ser 32 bytes" }
        // 12 B nonce + al menos 16 B de tag Poly1305; cualquier cosa más corta no puede ser válida.
        require(payload.size >= 12 + 16) { "Payload demasiado corto para contener nonce + tag" }
        val nonce = payload.copyOfRange(0, 12)
        val ciphertext = payload.copyOfRange(12, payload.size)
        val cipher = javax.crypto.Cipher.getInstance("ChaCha20-Poly1305")
        val secretKey = javax.crypto.spec.SecretKeySpec(key, "ChaCha20")
        cipher.init(javax.crypto.Cipher.DECRYPT_MODE, secretKey, javax.crypto.spec.IvParameterSpec(nonce))
        if (associatedData.isNotEmpty()) cipher.updateAAD(associatedData)
        return cipher.doFinal(ciphertext)
    }
}

/** Firma de bundle: `Sign_Kpriv(SHA-256(header||payload))` (Sección 6.3/14.2). */
class BundleSigner(private val identity: Ed25519Identity) {
    suspend fun sign(header: ByteArray, payload: ByteArray): ByteArray {
        val digest = java.security.MessageDigest.getInstance("SHA-256").digest(header + payload)
        return identity.sign(digest)
    }

    companion object {
        fun verify(publicKey: ByteArray, header: ByteArray, payload: ByteArray, signature: ByteArray): Boolean {
            val digest = java.security.MessageDigest.getInstance("SHA-256").digest(header + payload)
            val kf = KeyFactory.getInstance("Ed25519")
            val spec = java.security.spec.X509EncodedKeySpec(ed25519X509Prefix() + publicKey)
            val pub = kf.generatePublic(spec)
            val sig = Signature.getInstance("Ed25519")
            sig.initVerify(pub)
            sig.update(digest)
            return sig.verify(signature)
        }

        // Prefijo SubjectPublicKeyInfo fijo para Ed25519 (RFC 8410) — antepuesto a
        // los 32 bytes crudos para reconstruir una clave pública X.509 válida.
        private fun ed25519X509Prefix(): ByteArray = byteArrayOf(
            0x30, 0x2a, 0x30, 0x05, 0x06, 0x03, 0x2b, 0x65, 0x70, 0x03, 0x21, 0x00,
        )
    }
}

/** HMAC truncado a 4 bytes para el campo AUTH del beacon (protocol/beacon/BEACON_FORMAT.md). */
object BeaconAuthenticator {
    fun computeAuth(payloadWithoutAuth: ByteArray, sessionKey: ByteArray): ByteArray {
        val mac = javax.crypto.Mac.getInstance("HmacSHA256")
        mac.init(javax.crypto.spec.SecretKeySpec(sessionKey, "HmacSHA256"))
        val full = mac.doFinal(payloadWithoutAuth)
        return full.copyOfRange(0, 4)
    }
}
