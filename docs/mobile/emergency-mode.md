# Modo de emergencia

**Estado: PARCIAL / DEMO.** La UI tiene la ruta de modo de emergencia y acciones `NECESITO AYUDA` / `ESTOY A SALVO`. El envío remoto y la recepción de alertas reales no están conectados en el shell local.

El estado canónico previsto es:

```text
alerta real | alerta demo | SOS manual
        -> EmergencyController
        -> EmergencyState
        -> ubicación, movimiento, red, fisiología
```

Los sensores aportan evidencia; no determinan por sí solos vida, lesión o diagnóstico.

