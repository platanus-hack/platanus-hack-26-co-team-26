# Plan de integración final de HELIOS

## Objetivo

Reaplicar sobre `origin/develop` la máquina de tres modos y la experiencia Android de `integration/helios-complete`, conservando los contratos actuales de movimiento, PPG, ubicación, protocolo y BLE. La integración debe ser verificable, honesta y preparada para una prueba física de tres dispositivos.

## Decisiones

- `origin/develop` es la fuente funcional para protocolos, backend, sensores, PPG y BLE.
- La máquina `Normal → apoyo → asistencia requerida` se toma de `integration/helios-complete`, corrigiendo paquetes y conectándola al shell actual.
- Nearby Connections se usa como descubrimiento/transporte local visible; la cola DTN sigue siendo la fuente de verdad para conservar/retransmitir paquetes.
- No se presenta una alerta sísmica como real en Android hasta que exista un puente de ingesta; el botón de demostración usa el mismo controlador de emergencia.
- No se renombrarán paquetes técnicos ni se tocarán `main` o `backup/pre-reset-main`.

## Cortes verticales

### Fase 1: estado y máquina operativa — COMPLETADA

- [x] Integrar `OperationalModes.kt` y sus pruebas en el `core` vigente.
- [x] Rehacer `MobileShell` sin imports obsoletos, manteniendo el movimiento y PPG actuales.
- [x] Verificar `:core:testDebugUnitTest` y `:android:app:assembleDebug`.

### Fase 2: red cercana y evidencia — COMPLETADA CON LÍMITES DOCUMENTADOS

- [x] Integrar Nearby Connections, permisos y estados de radio sin llamadas inseguras.
- [x] Mantener descubrimiento/advertising simultáneo y múltiples pares.
- [x] Conectar el modo de asistencia al transporte local; una evidencia no disponible no bloquea el SOS.
- [x] Añadir laboratorio DEBUG con métricas reales del transporte, sin inventar rutas ni ACKs.

### Fase 3: documentación y validación — COMPLETADA

- [x] Documentar arquitectura, navegación, modos, red, offline y madurez.
- [x] Ejecutar `projects`, `test`, `lintDebug` y `assembleDebug`.
- [x] Instalar la APK resultante en el dispositivo ADB autorizado; la prueba física multi-dispositivo queda pendiente.

## Riesgos y mitigaciones

| Riesgo | Mitigación |
|---|---|
| Permisos o radios no disponibles | Estado explícito y degradación; no activar radios silenciosamente |
| DTN real aún no conectado al shell | Mantener la cola/transportes separados y etiquetar el paquete de prueba |
| API sin cliente Android | No inventar sincronización; documentar backend disponible y pendiente |
| Cambios de ramas divergentes | Aplicar por capacidad, no hacer merge ciego |
