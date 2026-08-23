package co.helius.auth

/** Development-only local auth. Replace with a backend repository before release. */
class DevAuthRepository {
    fun login(username: String, password: String): Boolean = username.trim() == "usuario" && password == "123456"
    fun register(username: String, password: String): Boolean = username.trim().isNotEmpty() && password.length >= 6
}
