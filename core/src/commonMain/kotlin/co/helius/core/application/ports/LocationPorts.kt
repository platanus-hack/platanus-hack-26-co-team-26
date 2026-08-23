package co.helius.core.application.ports

import co.helius.core.location.LocationSample
import co.helius.core.location.LocationTrackingProfile
import co.helius.core.location.MotionState
import kotlinx.coroutines.flow.Flow

enum class LocationAccuracy { APPROXIMATE, PRECISE }

sealed interface LocationPermissionState {
    data object NotRequested : LocationPermissionState
    data object Approximate : LocationPermissionState
    data object Precise : LocationPermissionState
    data object Denied : LocationPermissionState
    data object PermanentlyDenied : LocationPermissionState
}

interface LocationSource {
    suspend fun getCurrentLocation(accuracy: LocationAccuracy): LocationSample?
    fun observeLocation(profile: LocationTrackingProfile): Flow<LocationSample>
    fun stopTracking()
}

data class MotionSample(
    val accelerationRms: Double,
    val accelerationVariance: Double,
    val angularVelocityRads: Double?,
    val timestampNanos: Long,
    val state: MotionState,
)

interface MotionSensorSource {
    fun observeMotion(): Flow<MotionSample>
}
