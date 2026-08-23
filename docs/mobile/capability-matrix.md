# Matriz de capacidades de Helios

Auditoría final sobre la rama local `develop`, alineada con `origin/develop`.
La navegación normal solo expone capacidades ejecutables localmente. Las
capacidades remotas sin servidor real se mantienen fuera del flujo de producción
y cualquier simulación aparece únicamente en builds DEBUG.

| Capacidad | Estado | Implementación | UI conectada | Prueba |
|---|---|---|---|---|
| Autenticación local | REAL local | `LocalAccountRepository`, hash con salt y sesión persistente | Sí | Build |
| Personas/relaciones remotas | OCULTA | backend de cuentas no disponible en este checkout | No | — |
| Compartición de ubicación remota | OCULTA | requiere endpoint autenticado y consentimiento remoto | No | — |
| GPS actual | REAL local | adaptador Android de ubicación + estado de frescura | Sí | Build |
| Historial/lugares frecuentes | REAL/PARCIAL | inteligencia en `core`; consentimiento backend pendiente | Parcial | Tests core |
| Orientación espacial local | REAL local | superficie 2D honesta + lectura GPS real | Sí | Build |
| Alertas sísmicas | PARCIAL | fuentes EMSC/USGS/SGC en backend; shell demo | Demo | Tests backend existentes |
| Máquina de emergencia | REAL local | `HeliosStateMachine` + `EmergencyController` | Sí | Tests core |
| Reportes/alertas recibidas | OCULTA | requiere backend de incidentes y fuente real | No | — |
| Movimiento | REAL | acelerómetro, giroscopio y clasificador local | Sí | Build |
| PPG | REAL/PARCIAL | CameraX + PpgPipeline + segunda verificación | Sí | Tests core |
| Audio | PARCIAL | activos/contratos; captura Android no conectada | No | Build |
| BLE/GATT | REAL/PARCIAL | cliente/servidor y protocolo existentes | Indirecta | Build |
| Nearby multi-peer | REAL local | advertising + discovery + `P2P_CLUSTER` | Sí | Instalación; físico pendiente |
| Wi‑Fi Aware/Direct | NO IMPLEMENTADO | no expuesto por el shell | No | — |
| Internet/API móvil | PARCIAL | FastAPI y contratos; cliente Android pendiente | No | Build |
| DTN persistente | PARCIAL | motor y `BundleStore` en `core`; storage Android pendiente | Laboratorio | Tests core |
| Store-and-forward Nearby | REAL local | cola persistente local + reenvío multi-peer | Laboratorio | Físico pendiente |
| Deduplicación | REAL local | hash SHA-256 persistido durante la sesión | Laboratorio | Build |
| ACK técnico de aplicación | REAL local | ACK de recepción técnica; no es confirmación de rescate | Laboratorio | Físico pendiente |
| Offline | PARCIAL | sensores, PPG y red local sin Internet | Sí | Tests/build |
| Sincronización backend | PENDIENTE | requiere cliente y endpoint configurado | No | — |

La entrega de un payload Nearby no es una confirmación de rescate. La prueba de
relay A→B→C debe hacerse con tres dispositivos y registrar la misma identidad de
paquete en cada salto.
