# Location testing

Core tests cover freshness thresholds, Haversine distance, bearing, stay-point dwell/proximity, frequent-place ranking, and adaptive tracking. Web tests independently assert the same freshness thresholds and that historical estimates are never labeled GPS.

Required hardware checks include approximate/precise/denied/permanently-denied permission paths; GPS disabled; accelerometer without gyroscope; no sensors; background batching; critical battery; no Internet; tile and DEM failure. Web visual checks target 320, 768, 1024, and 1440 px, keyboard navigation, reduced motion, 2D/3D, 100+ points, and stale/SOS differentiation.

