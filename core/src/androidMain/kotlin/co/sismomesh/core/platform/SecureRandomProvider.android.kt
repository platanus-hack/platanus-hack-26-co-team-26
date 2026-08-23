package co.sismomesh.core.platform

import java.security.SecureRandom

actual fun secureRandomBytes(n: Int): ByteArray {
    val bytes = ByteArray(n)
    SecureRandom().nextBytes(bytes)
    return bytes
}
