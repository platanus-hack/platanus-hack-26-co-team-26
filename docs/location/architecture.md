# Location intelligence architecture

Location intelligence follows the repository's hexagonal boundary. `:core` owns geo models, Haversine/bearing calculations, freshness, adaptive tracking, stay points, frequent places, historical estimates, and emergency snapshots. `android:sensing` adapts Android location and sensor APIs. Renderers consume domain state but never start or stop GPS themselves.

```text
Android permissions → LocationSource ─┐
Sensors → MotionSensorSource ─────────┼→ local core → encrypted history
Battery/emergency state ──────────────┘      │
                                             ├→ emergency snapshot → DTN/API
                                             └→ map/radar presentation
Backend authorized projection → realtime events → stable web GeoJSON sources
```

Raw history is local by default. Only a compact, consented emergency snapshot crosses a trust boundary. Domain objects are richer than constrained BLE/Wi-Fi wire packets.

