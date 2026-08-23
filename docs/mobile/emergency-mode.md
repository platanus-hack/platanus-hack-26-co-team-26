# Modo de emergencia

**Estado local:** la máquina de estados y la UI son canónicas; las alertas
sísmicas reales y la sincronización cloud quedan fuera de producción mientras no
exista un proveedor/configuración verificable. La simulación está disponible solo
en DEBUG.

El estado canónico previsto es:

```text
alerta real | alerta demo | SOS manual
        -> EmergencyController
        -> EmergencyState
        -> ubicación, movimiento, red, fisiología
```

Los sensores aportan evidencia; no determinan por sí solos vida, lesión o diagnóstico.

Al entrar en un modo no normal, Helios inicia Nearby automáticamente **solo si
los permisos ya fueron concedidos**. Si faltan, la pantalla Red cercana pide los
permisos oficiales de Android. La aplicación no puede encender Wi‑Fi en silencio.
Una cámara, GPS o red no disponibles no cancelan por sí solos el estado de ayuda.

El laboratorio DEBUG informa peers, paquetes creados/recibidos/retransmitidos,
deduplicación, ACK técnicos y pendientes persistentes. Un ACK técnico solo prueba
recepción del paquete; nunca confirma rescate.

