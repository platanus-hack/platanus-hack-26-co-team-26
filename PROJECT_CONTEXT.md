# SismoMesh project context

SismoMesh is an Android-first emergency evidence platform. The product separates device evidence from medical conclusions: GPS, motion, PPG signal quality, battery, and relay metadata may be collected and shared only according to consent and authorization. Movement never means “alive”; phone-camera PPG is not ECG and is not a diagnosis.

## Modules

- `:core`: Kotlin Multiplatform domain, ports, geo intelligence, DTN and signal processing. No Android dependencies in common code.
- `:android:app`: Compose shell, local development auth, onboarding, permission entry points, home, emergency/motion/PPG/diagnostics/privacy surfaces.
- `:android:sensing`: Android `LocationSource` and `MotionSensorSource` adapters.
- `:android:ppg`: CameraX frame acquisition; processing remains in `:core`.
- `:android:transport`, `:android:storage`, `:android:power`, `:android:inference`: platform seams for future integrations.
- `web`: React/Vite responder simulation and MapLibre operations view.
- `services`: Python/FastAPI backend shells and shared contracts.

## Current milestone

Mobile Foundation Milestone 1 is a navigable, offline-capable frontend with fake/local development sources and real accelerometer/gyroscope/CameraX seams. Backend authentication, encrypted persistence, BLE relay, and production synchronization are later milestones.

## Local development rules

Read `DESIGN.md` before UI changes. Never commit credentials. The `usuario` / `123456` account is a local demo-only credential and must be replaced by a real hashed backend authentication flow before release. Do not request all permissions at launch. Do not store raw PPG or location remotely by default.

