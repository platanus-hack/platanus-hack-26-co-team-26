# Arquitectura móvil Helios

**Estado: IMPLEMENTADO en modo demo/local; integración de producción PARCIAL.**

La aplicación conserva el namespace técnico `co.helius` y separa UI, dominio y hardware:

```text
android/app (Compose, rutas y permisos)
        ↓
core (EmergencyController, modos, PPG/movimiento, contratos DTN)
        ↓
android/sensing · android/ppg · android/transport
        ↓
SensorManager · CameraX · Nearby Connections · BLE/GATT
```

`HeliosOperationalMode` es la única máquina de estados visible para NORMAL,
APOYO DE EMERGENCIA, ALERTA/ESPERA y ASISTENCIA REQUERIDA. SOS manual y alerta
simulada entran por el mismo `EmergencyController`.

`NearbyConnectionsTransport` anuncia y descubre simultáneamente con
`Strategy.P2P_CLUSTER`, mantiene varios peers, deduplica cargas por SHA-256 y
retransmite a los peers restantes. La cola actual es **en memoria por sesión**;
los ACK de aplicación y la persistencia Android de bundles siguen pendientes.

El backend/API, la proximidad de dispositivos y el motor DTN son capas distintas:
Nearby no sustituye la API y una retransmisión local no equivale a entrega confirmada.

