# Contexto del proyecto HELIOS

HELIOS es una plataforma Android de evidencia para emergencias. Separa la evidencia del dispositivo de las conclusiones médicas: GPS, movimiento, calidad PPG, batería y metadatos de retransmisión solo se recopilan o comparten con consentimiento. El movimiento nunca significa “persona viva”; el PPG de cámara no es ECG ni diagnóstico.

## Modules

- `:core`: Kotlin Multiplatform domain, ports, geo intelligence, DTN and signal processing. No Android dependencies in common code.
- `:android:app`: Compose shell, local development auth, onboarding, permission entry points, home, emergency/motion/PPG/diagnostics/privacy surfaces.
- `:android:sensing`: Android `LocationSource` and `MotionSensorSource` adapters.
- `:android:ppg`: CameraX frame acquisition; processing remains in `:core`.
- `:android:transport`, `:android:storage`, `:android:power`, `:android:inference`: platform seams for future integrations.
- `web`: simulación React/Vite para operadores y vista cartográfica.
- `services`: shells Python/FastAPI y contratos compartidos.

## Current milestone

El estado actual es una base navegable y parcialmente offline, con fuentes locales de desarrollo y adaptadores reales de acelerómetro, giroscopio, ubicación y CameraX. La autenticación backend, persistencia cifrada, retransmisión BLE y sincronización de producción siguen parciales.

## Local development rules

Lee `DESIGN.md` antes de modificar UI. No subas credenciales. `usuario` / `123456` es una cuenta local de demo y debe sustituirse por autenticación backend con hash antes de publicar. No solicites todos los permisos al abrir. No guardes PPG crudo ni ubicación remota por defecto. Conserva los paquetes técnicos existentes; la marca visible HELIOS no justifica una migración masiva de namespaces.

