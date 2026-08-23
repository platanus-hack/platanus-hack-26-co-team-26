package co.sismomesh.core.crypto

import kotlin.test.Test
import kotlin.test.assertContentEquals
import kotlin.test.assertFalse
import kotlin.test.assertTrue

/**
 * Corre en la JVM local (androidUnitTest, sin Robolectric ni teléfono) — ver
 * ADR-0001. Valida las primitivas reales de core/crypto, no mocks.
 */
class CryptoRoundTripTest {

    // Vector oficial RFC 5869 § A.1 (Test Case 1) — valida Hkdf byte a byte
    // contra una implementación de referencia externa, no solo contra sí misma.
    @Test
    fun `HKDF coincide con el vector oficial RFC 5869 caso 1`() {
        val ikm = ByteArray(22) { 0x0b }
        val salt = hex("000102030405060708090a0b0c")
        val info = hex("f0f1f2f3f4f5f6f7f8f9")
        val expectedPrk = hex("077709362c2e32df0ddc3f0dc47bba6390b6c73bb50f9c3122ec844ad7c2b3e")
        val expectedOkm = hex("3cb25f25faacd57a90434f64d0362f2a2d2d0a90cf1a5a4c5db02d56ecc4c5bf34007208d5b887185865")

        val prk = Hkdf.extract(salt, ikm)
        assertContentEquals(expectedPrk, prk)

        val okm = Hkdf.expand(prk, info, 42)
        assertContentEquals(expectedOkm, okm)
    }

    @Test
    fun `Ed25519 firma y verifica, y rechaza payload alterado`() {
        val identity = Ed25519Identity.generate()
        val header = "header".encodeToByteArray()
        val payload = "payload".encodeToByteArray()
        val signer = BundleSigner(identity)

        val signature = kotlinx.coroutines.runBlocking { signer.sign(header, payload) }
        val publicKey = kotlinx.coroutines.runBlocking { identity.ed25519PublicKey() }

        assertTrue(BundleSigner.verify(publicKey, header, payload, signature))
        assertFalse(BundleSigner.verify(publicKey, header, "payload-alterado".encodeToByteArray(), signature))
    }

    @Test
    fun `X25519 handshake deriva la misma clave de sesion en ambos lados`() {
        val alice = X25519Handshake()
        val bob = X25519Handshake()

        val bobEphemeral = bob.generateEphemeralKeyPair()
        val bobPublicRaw = bob.rawPublicKey(bobEphemeral.public)

        val (alicePublicRaw, aliceSessionKey) = alice.performReturningOwnPublic(bobPublicRaw)

        val alicePublic = bob.publicKeyFromRaw(alicePublicRaw)
        val bobSecret = bob.sharedSecret(bobEphemeral.private, alicePublic)
        val bobSessionKey = bob.deriveSessionKey(bobSecret, alicePublicRaw + bobPublicRaw)

        assertContentEquals(aliceSessionKey, bobSessionKey)
    }

    @Test
    fun `ChaCha20-Poly1305 cifra y descifra, y rechaza AAD incorrecto`() {
        val key = ByteArray(32) { it.toByte() }
        val cipher = PayloadCipher()
        val plaintext = "NECESITO AYUDA - S-134".encodeToByteArray()
        val aad = "bundle-header-v1".encodeToByteArray()

        val ciphertext = cipher.encrypt(plaintext, key, aad)
        val decrypted = cipher.decrypt(ciphertext, key, aad)
        assertContentEquals(plaintext, decrypted)

        assertTrue(runCatching { cipher.decrypt(ciphertext, key, "aad-incorrecto".encodeToByteArray()) }.isFailure)
    }

    @Test
    fun `pseudonimo cambia por desastre y por epoca`() {
        val seed = ByteArray(32) { 7 }
        val a = PseudonymDeriver.derive(seed, "sismo-2026-08-22", 1)
        val b = PseudonymDeriver.derive(seed, "sismo-2026-08-22", 2)
        val c = PseudonymDeriver.derive(seed, "otro-desastre", 1)
        assertTrue(!a.contentEquals(b))
        assertTrue(!a.contentEquals(c))
    }

    private fun hex(s: String): ByteArray = ByteArray(s.length / 2) {
        s.substring(it * 2, it * 2 + 2).toInt(16).toByte()
    }
}
