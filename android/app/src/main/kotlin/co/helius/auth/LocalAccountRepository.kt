package co.helius.auth

import android.content.Context
import android.content.pm.ApplicationInfo
import java.security.MessageDigest
import java.security.SecureRandom

/** Cuenta local persistente para operar sin red; no sustituye autenticación cloud. */
class LocalAccountRepository(context: Context) {
    private val preferences = context.applicationContext.getSharedPreferences(PREFERENCES, Context.MODE_PRIVATE)
    private val random = SecureRandom()

    init {
        val debugBuild = (context.applicationInfo.flags and ApplicationInfo.FLAG_DEBUGGABLE) != 0
        if (debugBuild && !preferences.getBoolean(DEMO_SEEDED, false)) {
            register(DEMO_USERNAME, DEMO_PASSWORD)
            preferences.edit().putBoolean(DEMO_SEEDED, true).apply()
        }
    }

    fun login(username: String, password: String): Boolean {
        val normalized = normalize(username)
        val stored = preferences.getString(accountKey(normalized), null) ?: return false
        val parts = stored.split(DELIMITER, limit = 2)
        return parts.size == 2 && secureEquals(parts[1], digest(password, parts[0]))
    }

    fun register(username: String, password: String): Boolean {
        val normalized = normalize(username)
        if (!USERNAME_PATTERN.matches(normalized) || password.length < 6) return false
        val key = accountKey(normalized)
        if (preferences.contains(key)) return false
        val salt = ByteArray(16).also(random::nextBytes).toHex()
        preferences.edit().putString(key, "$salt$DELIMITER${digest(password, salt)}").apply()
        return true
    }

    fun startSession(username: String) {
        preferences.edit().putString(SESSION_USER, normalize(username)).apply()
    }

    fun currentSession(): String? = preferences.getString(SESSION_USER, null)

    fun signOut() {
        preferences.edit().remove(SESSION_USER).apply()
    }

    private fun normalize(username: String): String = username.trim().lowercase()
    private fun accountKey(username: String): String = "account.$username"
    private fun digest(password: String, salt: String): String = MessageDigest.getInstance("SHA-256")
        .digest("$salt:$password".encodeToByteArray()).toHex()
    private fun secureEquals(left: String, right: String): Boolean = MessageDigest.isEqual(left.encodeToByteArray(), right.encodeToByteArray())
    private fun ByteArray.toHex(): String = joinToString("") { "%02x".format(it) }

    companion object {
        const val DEMO_USERNAME = "usuario"
        const val DEMO_PASSWORD = "123456"
        private const val PREFERENCES = "helios.local.account"
        private const val SESSION_USER = "session.user"
        private const val DEMO_SEEDED = "demo.seeded"
        private const val DELIMITER = ":"
        private val USERNAME_PATTERN = Regex("[a-z0-9._-]{3,32}")
    }
}
