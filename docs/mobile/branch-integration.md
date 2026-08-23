# Integración por capacidad

La entrega final se trabaja en la rama local `develop`, alineada con `origin/develop`.
`main` y `backup/pre-reset-main` permanecen excluidas y no se modifican.

| Capacidad | Fuente elegida | Decisión |
|---|---|---|
| Shell/UI y modos | `origin/develop` + trabajo reutilizado de `integration/helios-complete` | Combinar; shell español, navegación centralizada y máquina de estados |
| Ubicación | `gps` + `develop` | Combinar contratos, adaptador Android y análisis puro |
| Movimiento | `develop` (`motion-evidence`) | Mantener dominio avanzado; compatibilidad simple en shell |
| PPG | `develop` + `offline-triage-ppg`/`gps` | Combinar CameraX avanzada con verificación DFT local |
| Alertas | `develop-alert-ingestor` | Mantener backend; Android aún parcial |
| API/transporte | `develop` + `develop-api` | Mantener contratos y DTN; Nearby Connections añadido al shell, cliente backend pendiente |
| Comparación vital/ubicación | `vitals-localization-comparison` | Referencia de investigación, no ruta de producción |

La historia de ramas no debe aparecer en la arquitectura final; los paquetes se organizan por dominio y se conservan namespaces técnicos existentes cuando no hay necesidad de migrarlos.

La auditoría funcional distingue tres capas: API backend (Internet), Nearby/BLE
para proximidad y DTN/store-and-forward. Nearby ya soporta advertising + discovery
multi-peer, reenvío, deduplicación y ACK técnico de recepción; la cola de paquetes
pendientes se conserva localmente. Ningún ACK técnico se interpreta como rescate.

