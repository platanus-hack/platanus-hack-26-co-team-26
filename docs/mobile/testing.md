# Mobile testing

Pure tests cover PPG frequency detection, short/noisy rejection, location calculations, freshness, stay points, frequent places, and adaptive tracking. On a real device validate permission denial, missing gyroscope, missing accelerometer, camera permission denial, torch failure, capture shorter than eight seconds, battery saver, and no network.

For PPG specifically, test a normal synthetic signal, a low-frequency signal that requests a second verification, two coherent anomalous windows (`REPEATED_ANOMALY`), and two disagreeing windows (`INCONCLUSIVE_RECHECK`). Never interpret the repeated pattern as a clinical diagnosis.
