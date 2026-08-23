# Contexto del proyecto HELIOS

HELIOS es una plataforma Android de evidencia para emergencias. Separa la evidencia del dispositivo de las conclusiones médicas: GPS, movimiento, calidad PPG, batería y metadatos de retransmisión solo se recopilan o comparten con consentimiento. El movimiento nunca significa “persona viva”; el PPG de cámara no es ECG ni diagnóstico.

## Modules

- `:core`: Kotlin Multiplatform domain, ports, geo intelligence, DTN and signal processing. No Android dependencies in common code.
- `:android:app`: Compose shell, cuenta local offline persistente, onboarding, permisos, inicio, orientación GPS, emergencia/movimiento/PPG/diagnósticos y privacidad.
- `:android:sensing`: Android `LocationSource` and `MotionSensorSource` adapters.
- `:android:ppg`: CameraX frame acquisition; processing remains in `:core`.
- `:android:transport`, `:android:storage`, `:android:power`, `:android:inference`: platform seams for future integrations.
- `web`: simulación React/Vite para operadores y vista cartográfica.
- `services`: shells Python/FastAPI y contratos compartidos.

## Hito actual

El estado actual es una aplicación local offline verificable, con adaptadores
reales de acelerómetro, giroscopio, ubicación y CameraX. La UI usa una máquina
de estados única para alerta, apoyo y asistencia requerida. Nearby Connections
anuncia y descubre en paralelo, mantiene varios peers, retransmite cargas nuevas,
deduplica por hash, emite ACK técnicos y conserva la cola local. La cuenta local
no pretende sustituir autenticación cloud; personas, alertas remotas y
sincronización solo aparecen cuando exista un backend operativo.

## Local development rules

Lee `DESIGN.md` antes de modificar UI. No subas credenciales. `usuario` / `123456`
solo se siembra en builds DEBUG; las cuentas locales usan hash con salt y sesión
persistente. No solicites todos los permisos al abrir. No guardes PPG crudo ni
ubicación remota por defecto. Conserva los paquetes técnicos existentes; la marca
visible HELIOS no justifica una migración masiva de namespaces.

