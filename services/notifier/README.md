# services/notifier

**Propósito:** Push a dispositivos (FCM), canales de alerta, reintentos. FCM no está diseñado para alertas críticas — ver docs/security/THREAT-MODEL.md.

**Dueño:** Miguel.

**Etiqueta de madurez:** `ENGINEERING` (esqueleto generado).

Importa el kernel común de `services/shared/src/api/{domain,application}` — no
duplica entidades ni puertos.
