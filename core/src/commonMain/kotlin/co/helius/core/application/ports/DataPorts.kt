package co.helius.core.application.ports

import co.helius.core.domain.model.Bundle
import co.helius.core.domain.vo.BundleId
import kotlinx.coroutines.flow.Flow

/** Persistencia local de bundles. Dueño: Helmut. Adaptadores: SqlDelightStore, InMemoryStore. */
interface BundleStorePort {
    suspend fun save(bundle: Bundle)
    suspend fun get(id: BundleId): Bundle?
    suspend fun outbox(): Flow<Bundle>
    suspend fun evict(id: BundleId)
}

/** GNSS + cambios significativos. Dueño: Miguel (localización). Adaptadores: FusedLocationAdapter, ScriptedFake. */
interface LocationPort {
    fun observeLocation(): Flow<Any /* TODO: LocationSample */>
}

/** Ventanas de acelerómetro/giroscopio. Dueño: Alex. Adaptadores: SensorManagerAdapter, ReplayFake. */
interface MotionPort {
    fun observeMotionWindows(): Flow<Any /* TODO: MotionWindow, ver core/signal */>
}
