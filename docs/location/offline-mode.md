# Offline and degraded modes

Android collection, motion classification, history analysis, snapshots, and packet queues are local. Rendering degrades from online vector tiles to cached regions and finally to radar mode showing bearing, distance, evidence type, packet age, and device state. Tile, DEM, and geocoder failure must not stop tracking.

The web retains the last authorized incident projection and announces realtime disconnection; stale thresholds continue advancing locally. Simulation mode is explicitly labeled and never mixed with production events.

