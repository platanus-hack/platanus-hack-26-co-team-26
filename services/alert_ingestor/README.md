# services/alert_ingestor

**Propósito:** Polling/suscripción a fuentes externas (SGC/CAP/USGS), normalización a CAP interno, dedupe, decisión de activación del evento (Sección 12.4).

**Dueño:** Miguel.

**Etiqueta de madurez:** `ENGINEERING` (esqueleto generado).

Importa el kernel común de `services/shared/src/api/{domain,application}` — no
duplica entidades ni puertos.
