package co.helius.android.sensing

import android.Manifest
import android.annotation.SuppressLint
import android.content.Context
import android.content.pm.PackageManager
import android.location.Location
import android.location.LocationListener
import android.location.LocationManager
import android.os.CancellationSignal
import co.helius.core.application.ports.LocationAccuracy
import co.helius.core.application.ports.LocationSource
import co.helius.core.location.LocalGeoPoint
import co.helius.core.location.LocationEvidenceType
import co.helius.core.location.LocationProvider
import co.helius.core.location.LocationSample
import co.helius.core.location.LocationTrackingProfile
import kotlinx.coroutines.channels.awaitClose
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.callbackFlow
import kotlinx.coroutines.suspendCancellableCoroutine
import kotlin.coroutines.resume

class AndroidLocationSource(context: Context) : LocationSource {
    private val appContext = context.applicationContext
    private val manager = appContext.getSystemService(LocationManager::class.java)
    private val listeners = mutableSetOf<LocationListener>()

    @SuppressLint("MissingPermission")
    override suspend fun getCurrentLocation(accuracy: LocationAccuracy): LocationSample? {
        if (!hasPermission(accuracy)) return null
        val provider = providerFor(accuracy) ?: return null
        return suspendCancellableCoroutine { continuation ->
            val cancellation = CancellationSignal()
            continuation.invokeOnCancellation { cancellation.cancel() }
            manager.getCurrentLocation(provider, cancellation, appContext.mainExecutor) { location ->
                continuation.resume(location?.toSample(LocationTrackingProfile.NORMAL))
            }
        }
    }

    @SuppressLint("MissingPermission")
    override fun observeLocation(profile: LocationTrackingProfile): Flow<LocationSample> = callbackFlow {
        if (!hasPermission(LocationAccuracy.APPROXIMATE)) { close(); return@callbackFlow }
        val provider = providerFor(if (hasPermission(LocationAccuracy.PRECISE)) LocationAccuracy.PRECISE else LocationAccuracy.APPROXIMATE)
            ?: run { close(); return@callbackFlow }
        val interval = when (profile) {
            LocationTrackingProfile.PASSIVE -> 5 * 60_000L
            LocationTrackingProfile.NORMAL -> 60_000L
            LocationTrackingProfile.ACTIVE -> 15_000L
            LocationTrackingProfile.EMERGENCY -> 5_000L
        }
        val listener = LocationListener { trySend(it.toSample(profile)) }
        listeners += listener
        manager.requestLocationUpdates(provider, interval, 0f, listener)
        awaitClose { manager.removeUpdates(listener); listeners -= listener }
    }

    override fun stopTracking() {
        listeners.toList().forEach(manager::removeUpdates)
        listeners.clear()
    }

    private fun hasPermission(accuracy: LocationAccuracy): Boolean {
        val permission = if (accuracy == LocationAccuracy.PRECISE) Manifest.permission.ACCESS_FINE_LOCATION else Manifest.permission.ACCESS_COARSE_LOCATION
        return appContext.checkSelfPermission(permission) == PackageManager.PERMISSION_GRANTED
    }

    private fun providerFor(accuracy: LocationAccuracy): String? = when {
        accuracy == LocationAccuracy.PRECISE && manager.isProviderEnabled(LocationManager.GPS_PROVIDER) -> LocationManager.GPS_PROVIDER
        manager.isProviderEnabled(LocationManager.NETWORK_PROVIDER) -> LocationManager.NETWORK_PROVIDER
        else -> null
    }
}

private fun Location.toSample(profile: LocationTrackingProfile) = LocationSample(
    id = "location-$elapsedRealtimeNanos",
    point = LocalGeoPoint(latitude, longitude),
    altitudeMeters = if (hasAltitude()) altitude else null,
    horizontalAccuracyMeters = if (hasAccuracy()) accuracy.toDouble() else null,
    verticalAccuracyMeters = if (android.os.Build.VERSION.SDK_INT >= 26 && hasVerticalAccuracy()) verticalAccuracyMeters.toDouble() else null,
    speedMetersPerSecond = if (hasSpeed()) speed.toDouble() else null,
    bearingDegrees = if (hasBearing()) bearing.toDouble() else null,
    timestampEpochMillis = time,
    provider = when (provider) { LocationManager.GPS_PROVIDER -> LocationProvider.GNSS; LocationManager.NETWORK_PROVIDER -> LocationProvider.NETWORK; else -> LocationProvider.FUSED },
    trackingProfile = profile,
    evidenceType = LocationEvidenceType.CURRENT_GPS,
)
