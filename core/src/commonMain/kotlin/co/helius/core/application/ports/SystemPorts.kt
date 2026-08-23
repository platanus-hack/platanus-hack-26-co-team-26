package co.helius.core.application.ports

/** Claves Ed25519/X25519. Dueño: Helmut (protocolo + criptografía). Adaptadores: KeystoreAdapter, MemoryFake. */
interface IdentityPort {
    suspend fun ed25519PublicKey(): ByteArray
    suspend fun sign(data: ByteArray): ByteArray
}

/** Modos de energía y ciclo de trabajo (Sección 7.4-7.5). Dueño: Helmut. Adaptadores: AndroidPowerAdapter, FixedPolicyFake. */
interface PowerPolicyPort {
    fun currentMode(): Any /* READY | ALERT | TRAPPED | RESCUER */
    fun batteryPercent(): Int
}

/** Subida cuando hay red. Dueño: Miguel (backend). Adaptadores: KtorSyncAdapter, OfflineFake. */
interface CloudSyncPort {
    suspend fun sync(): Boolean
}

/** Recepción de alertas sísmicas (CAP/SGC/USGS). Dueño: Miguel. Adaptadores: FcmAdapter, LocalTriggerAdapter. */
interface AlertReceiverPort {
    fun observeAlerts(): kotlinx.coroutines.flow.Flow<Any>
}

/** Tiempo y monotonía — testeable. Dueño: compartido. Adaptadores: SystemClock, FrozenClock. */
interface ClockPort {
    fun nowMs(): Long
    fun monotonicMs(): Long
}
