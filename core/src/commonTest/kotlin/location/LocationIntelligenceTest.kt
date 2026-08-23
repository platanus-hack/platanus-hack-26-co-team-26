package co.helius.core.location

import kotlin.test.Test
import kotlin.test.assertEquals
import kotlin.test.assertTrue

class LocationIntelligenceTest {
    private val now = 1_800_000_000_000L

    @Test
    fun `freshness never presents stale evidence as current`() {
        assertEquals(FreshnessState.LIVE, freshnessAt(now - 20_000, now))
        assertEquals(FreshnessState.RECENT, freshnessAt(now - 90_000, now))
        assertEquals(FreshnessState.AGING, freshnessAt(now - 8 * 60_000, now))
        assertEquals(FreshnessState.STALE, freshnessAt(now - 31 * 60_000, now))
    }

    @Test
    fun `haversine and bearing are geographically meaningful`() {
        val bogota = LocalGeoPoint(4.7110, -74.0721)
        val medellin = LocalGeoPoint(6.2442, -75.5812)
        val distanceKm = haversineMeters(bogota, medellin) / 1_000

        assertTrue(distanceKm in 235.0..255.0)
        assertTrue(initialBearingDegrees(bogota, medellin) in 305.0..325.0)
    }

    @Test
    fun `stay point detector requires both dwell and proximity`() {
        val samples = listOf(
            sample("a", 4.71100, -74.07210, now - 40 * 60_000),
            sample("b", 4.71104, -74.07208, now - 20 * 60_000),
            sample("c", 4.71102, -74.07212, now),
        )

        val stays = StayPointDetector().detect(samples)

        assertEquals(1, stays.size)
        assertTrue(stays.single().dwellDurationMillis >= 30 * 60_000)
    }

    @Test
    fun `frequent place ranking favors repeated and recent stays`() {
        val stays = listOf(
            stay("home-1", 4.7110, -74.0721, now - 6 * 86_400_000L, 5 * 3_600_000L),
            stay("home-2", 4.7111, -74.0720, now - 86_400_000L, 7 * 3_600_000L),
            stay("work", 4.7000, -74.0600, now - 2 * 86_400_000L, 4 * 3_600_000L),
        )

        val places = FrequentPlaceAnalyzer().analyze(stays, now)

        assertEquals(2, places.size)
        assertEquals(2, places.first().visitCount)
        assertTrue(places.first().score > places.last().score)
    }

    @Test
    fun `tracking policy preserves emergency updates while respecting critical battery`() {
        val policy = AdaptiveTrackingPolicy()

        assertEquals(LocationTrackingProfile.EMERGENCY, policy.select(true, MotionState.STATIONARY, BatteryState.NORMAL))
        assertEquals(LocationTrackingProfile.ACTIVE, policy.select(true, MotionState.STATIONARY, BatteryState.CRITICAL))
        assertEquals(LocationTrackingProfile.PASSIVE, policy.select(false, MotionState.STATIONARY, BatteryState.LOW))
    }

    private fun sample(id: String, lat: Double, lon: Double, timestamp: Long) = LocationSample(
        id = id,
        point = LocalGeoPoint(lat, lon),
        horizontalAccuracyMeters = 8.0,
        timestampEpochMillis = timestamp,
        provider = LocationProvider.GNSS,
        trackingProfile = LocationTrackingProfile.NORMAL,
        evidenceType = LocationEvidenceType.CURRENT_GPS,
    )

    private fun stay(id: String, lat: Double, lon: Double, arrived: Long, duration: Long) = StayPoint(
        id = id,
        centroid = LocalGeoPoint(lat, lon),
        arrivedAtEpochMillis = arrived,
        departedAtEpochMillis = arrived + duration,
        sampleCount = 4,
    )
}
