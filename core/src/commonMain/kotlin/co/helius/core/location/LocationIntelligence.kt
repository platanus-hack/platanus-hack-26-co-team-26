package co.helius.core.location

import kotlin.math.PI
import kotlin.math.atan2
import kotlin.math.cos
import kotlin.math.exp
import kotlin.math.sin
import kotlin.math.sqrt

private const val EARTH_RADIUS_METERS = 6_371_000.0

fun haversineMeters(from: LocalGeoPoint, to: LocalGeoPoint): Double {
    val lat1 = from.latitude.toRadians()
    val lat2 = to.latitude.toRadians()
    val deltaLat = (to.latitude - from.latitude).toRadians()
    val deltaLon = (to.longitude - from.longitude).toRadians()
    val a = sin(deltaLat / 2) * sin(deltaLat / 2) +
        cos(lat1) * cos(lat2) * sin(deltaLon / 2) * sin(deltaLon / 2)
    return EARTH_RADIUS_METERS * 2 * atan2(sqrt(a), sqrt(1 - a))
}

fun initialBearingDegrees(from: LocalGeoPoint, to: LocalGeoPoint): Double {
    val fromLat = from.latitude.toRadians()
    val toLat = to.latitude.toRadians()
    val deltaLon = (to.longitude - from.longitude).toRadians()
    val y = sin(deltaLon) * cos(toLat)
    val x = cos(fromLat) * sin(toLat) - sin(fromLat) * cos(toLat) * cos(deltaLon)
    return (atan2(y, x) * 180 / PI + 360) % 360
}

fun freshnessAt(timestampEpochMillis: Long, nowEpochMillis: Long): FreshnessState {
    val age = (nowEpochMillis - timestampEpochMillis).coerceAtLeast(0)
    return when {
        age <= 30_000 -> FreshnessState.LIVE
        age <= 2 * 60_000 -> FreshnessState.RECENT
        age <= 30 * 60_000 -> FreshnessState.AGING
        else -> FreshnessState.STALE
    }
}

class AdaptiveTrackingPolicy {
    fun select(isEmergency: Boolean, motion: MotionState, battery: BatteryState): LocationTrackingProfile = when {
        isEmergency && battery != BatteryState.CRITICAL -> LocationTrackingProfile.EMERGENCY
        isEmergency -> LocationTrackingProfile.ACTIVE
        battery == BatteryState.CRITICAL -> LocationTrackingProfile.PASSIVE
        motion == MotionState.RAPID_MOVEMENT -> LocationTrackingProfile.ACTIVE
        motion == MotionState.MOVING -> LocationTrackingProfile.NORMAL
        battery == BatteryState.LOW -> LocationTrackingProfile.PASSIVE
        else -> LocationTrackingProfile.NORMAL
    }
}

class StayPointDetector(
    private val radiusMeters: Double = 100.0,
    private val minimumDwellMillis: Long = 20 * 60_000,
) {
    fun detect(samples: List<LocationSample>): List<StayPoint> {
        val ordered = samples.sortedBy { it.timestampEpochMillis }
        val result = mutableListOf<StayPoint>()
        var start = 0
        while (start < ordered.lastIndex) {
            var end = start + 1
            while (end < ordered.size && haversineMeters(ordered[start].point, ordered[end].point) <= radiusMeters) end++
            val lastInside = end - 1
            val dwell = ordered[lastInside].timestampEpochMillis - ordered[start].timestampEpochMillis
            if (lastInside > start && dwell >= minimumDwellMillis) {
                val window = ordered.subList(start, end)
                result += StayPoint(
                    id = "stay-${ordered[start].id}-${ordered[lastInside].id}",
                    centroid = window.map { it.point }.centroid(),
                    arrivedAtEpochMillis = ordered[start].timestampEpochMillis,
                    departedAtEpochMillis = ordered[lastInside].timestampEpochMillis,
                    sampleCount = window.size,
                )
                start = end
            } else start++
        }
        return result
    }
}

class FrequentPlaceAnalyzer(private val clusterRadiusMeters: Double = 150.0) {
    fun analyze(stays: List<StayPoint>, nowEpochMillis: Long): List<FrequentPlace> {
        val clusters = mutableListOf<MutableList<StayPoint>>()
        stays.sortedByDescending { it.departedAtEpochMillis }.forEach { stay ->
            val cluster = clusters.firstOrNull { haversineMeters(it.map { point -> point.centroid }.centroid(), stay.centroid) <= clusterRadiusMeters }
            if (cluster == null) clusters += mutableListOf(stay) else cluster += stay
        }
        return clusters.mapIndexed { index, cluster ->
            val dwell = cluster.sumOf { it.dwellDurationMillis }
            val lastVisit = cluster.maxOf { it.departedAtEpochMillis }
            val recency = exp(-((nowEpochMillis - lastVisit).coerceAtLeast(0) / 86_400_000.0) / 14.0)
            val score = cluster.size * 0.5 + (dwell / 3_600_000.0) * 0.03 + recency * 0.3
            FrequentPlace("place-$index", cluster.map { it.centroid }.centroid(), cluster.size, dwell, lastVisit, score)
        }.sortedByDescending { it.score }
    }
}

class LocationEstimationService {
    fun rank(places: List<FrequentPlace>): List<LikelyLocation> {
        val total = places.sumOf { it.score }.takeIf { it > 0 } ?: return emptyList()
        return places.sortedByDescending { it.score }.map { LikelyLocation(it, (it.score / total).coerceIn(0.0, 1.0)) }
    }
}

private fun List<LocalGeoPoint>.centroid(): LocalGeoPoint = LocalGeoPoint(
    latitude = sumOf { it.latitude } / size,
    longitude = sumOf { it.longitude } / size,
)

private fun Double.toRadians(): Double = this * PI / 180
