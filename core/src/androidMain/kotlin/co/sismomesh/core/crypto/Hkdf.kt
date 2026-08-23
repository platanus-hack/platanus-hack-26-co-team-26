package co.sismomesh.core.crypto

import javax.crypto.Mac
import javax.crypto.spec.SecretKeySpec

/**
 * HKDF (RFC 5869) sobre HMAC-SHA256. JVM-only (javax.crypto) — vive en
 * androidMain junto al resto de core/crypto. Sin dependencias externas.
 */
internal object Hkdf {
    private const val ALGO = "HmacSHA256"
    private const val HASH_LEN = 32

    fun extract(salt: ByteArray, ikm: ByteArray): ByteArray {
        val mac = Mac.getInstance(ALGO)
        mac.init(SecretKeySpec(salt.ifEmpty { ByteArray(HASH_LEN) }, ALGO))
        return mac.doFinal(ikm)
    }

    fun expand(prk: ByteArray, info: ByteArray, length: Int): ByteArray {
        val mac = Mac.getInstance(ALGO)
        mac.init(SecretKeySpec(prk, ALGO))
        val out = ByteArray(length)
        var t = ByteArray(0)
        var pos = 0
        var counter = 1
        while (pos < length) {
            mac.reset()
            mac.update(t)
            mac.update(info)
            mac.update(counter.toByte())
            t = mac.doFinal()
            val toCopy = minOf(t.size, length - pos)
            t.copyInto(out, pos, 0, toCopy)
            pos += toCopy
            counter++
        }
        return out
    }

    /** Atajo extract+expand, como usan la mayoría de los consumidores del proyecto. */
    fun deriveKey(ikm: ByteArray, salt: ByteArray, info: ByteArray, length: Int): ByteArray =
        expand(extract(salt, ikm), info, length)
}
