# PPG capture

The pipeline is separated into acquisition (`:android:ppg`), processing (`core/signal/PpgPipeline`), and presentation (`:android:app`). The heuristic estimator returns BPM, signal quality, method provenance, and observational pattern enums. It does not claim SpO2, shock, hemorrhage, disease, or diagnosis. Synthetic samples keep UI development unblocked when no camera is available.

## Verification prototype

`PpgPipeline.assess()` treats a low-SQI or unusual value (for example, below 50 BPM) as provisional. The Android screen asks for a second 12-second capture instead of presenting that first value as bradycardia. The two windows are processed independently with a detrended, Hann-windowed DFT and combined with a conservative midpoint when they agree. A repeated low/high pattern is exposed as `REPEATED_ANOMALY` for testing and follow-up only; it is not a diagnosis. Discordant or poor-quality captures remain `INCONCLUSIVE_RECHECK`.
