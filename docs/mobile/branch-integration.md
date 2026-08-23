# Integración por capacidad

La rama temporal `integration/helios-complete` se creó desde `origin/develop` para auditar capacidades sin modificar `main` ni `backup/pre-reset-main`.

| Capacidad | Fuente elegida | Decisión |
|---|---|---|
| Shell/UI | `develop` + `gps` | Combinar; shell local navegable y marca HELIOS |
| Ubicación | `gps` + `develop` | Combinar contratos, adaptador Android y análisis puro |
| Movimiento | `develop` (`motion-evidence`) | Mantener dominio avanzado; compatibilidad simple en shell |
| PPG | `develop` + `offline-triage-ppg`/`gps` | Combinar CameraX avanzada con verificación DFT local |
| Alertas | `develop-alert-ingestor` | Mantener backend; Android aún parcial |
| API/transporte | `develop` + `develop-api` | Mantener contratos y DTN; cliente Android pendiente |
| Comparación vital/ubicación | `vitals-localization-comparison` | Referencia de investigación, no ruta de producción |

La historia de ramas no debe aparecer en la arquitectura final; los paquetes se organizan por dominio y se conservan namespaces técnicos existentes cuando no hay necesidad de migrarlos.

