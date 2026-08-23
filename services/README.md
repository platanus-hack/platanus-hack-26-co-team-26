# services/ — backend Python (FastAPI, hexagonal)

**Stack:** Python 3.12 + FastAPI, PostgreSQL 16 + PostGIS, Redis (colas/caché),
S3-compatible (MinIO en desarrollo). Ver Sección 2.4 del spec original: el backend
no es CRUD — contiene *factor graph* para localización, ajuste del modelo de
propagación RF y evaluación del modelo AIB.

**Patrón:** un hexágono por servicio. `shared/` es el kernel común (dominio,
puertos, criptografía, geo, telemetría) que todos importan; cada servicio expone
solo sus propios adaptadores.

| Servicio | Responsabilidad | Dueño |
|---|---|---|
| `shared/src/api` | REST + WebSocket, auth, autorización por rol, agregaciones por vista | Miguel |
| `alert_ingestor` | Polling/suscripción a fuentes (SGC/CAP/USGS), normalización a CAP interno, dedupe, decisión de activación | Miguel |
| `bundle_ingestor` | Verificación de firmas, dedupe por `bundle_id`, reconstrucción de causalidad, fan-out | Miguel |
| `localization` | Factor graph, zonas candidatas, heatmaps, recálculo incremental | Miguel |
| `notifier` | FCM, canales de alerta, reintentos | Miguel |
| `analytics` | Métricas operativas, exportes, datasets de investigación | Miguel |

**Regla de PII (Sección 12.3):** todo endpoint que devuelva PII escribe en
`audit_log` **antes** de responder.

**Etiqueta de madurez:** `ENGINEERING` (esqueleto generado).
