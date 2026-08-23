package co.helius.core.location

data class LocalGeoPoint(val latitude: Double, val longitude: Double) {
    init {
        require(latitude in -90.0..90.0) { "Latitude must be between -90 and 90" }
        require(longitude in -180.0..180.0) { "Longitude must be between -180 and 180" }
    }
}

enum class LocationProvider { GNSS, NETWORK, FUSED, MANUAL, ESTIMATED }
enum class MotionState { UNKNOWN, STATIONARY, MOVING, RAPID_MOVEMENT }
enum class LocationTrackingProfile { PASSIVE, NORMAL, ACTIVE, EMERGENCY }
enum class LocationEvidenceType { CURRENT_GPS, LAST_KNOWN, HISTORICAL_ESTIMATE, MANUAL, RELAY_OBSERVATION }
enum class FreshnessState { LIVE, RECENT, AGING, STALE }
enum class BatteryState { NORMAL, LOW, CRITICAL }

data class LocationSample(
    val id: String,
    val point: LocalGeoPoint,
    val altitudeMeters: Double? = null,
    val horizontalAccuracyMeters: Double? = null,
    val verticalAccuracyMeters: Double? = null,
    val speedMetersPerSecond: Double? = null,
    val bearingDegrees: Double? = null,
    val timestampEpochMillis: Long,
    val provider: LocationProvider,
    val motionState: MotionState = MotionState.UNKNOWN,
    val trackingProfile: LocationTrackingProfile,
    val evidenceType: LocationEvidenceType,
)

data class StayPoint(
    val id: String,
    val centroid: LocalGeoPoint,
    val arrivedAtEpochMillis: Long,
    val departedAtEpochMillis: Long,
    val sampleCount: Int,
) {
    val dwellDurationMillis: Long get() = departedAtEpochMillis - arrivedAtEpochMillis
}

data class FrequentPlace(
    val id: String,
    val centroid: LocalGeoPoint,
    val visitCount: Int,
    val totalDwellMillis: Long,
    val lastVisitEpochMillis: Long,
    val score: Double,
)

data class LikelyLocation(
    val place: FrequentPlace,
    val confidence: Double,
    val evidenceType: LocationEvidenceType = LocationEvidenceType.HISTORICAL_ESTIMATE,
)

data class EmergencyLocationSnapshot(
    val deviceId: String,
    val point: LocalGeoPoint?,
    val altitudeMeters: Double?,
    val accuracyMeters: Double?,
    val evidenceType: LocationEvidenceType,
    val locationTimestampEpochMillis: Long?,
    val recentMovementDetected: Boolean,
    val lastMovementTimestampEpochMillis: Long?,
    val motionConfidence: Double?,
    val batteryPercent: Int?,
    val sourceDeviceTimestampEpochMillis: Long,
)

