# services/bundle_ingestor

**Propósito:** Verificación de firmas Ed25519, dedupe por bundle_id, reconstrucción de causalidad vía grafo de encuentros, fan-out a otros servicios.

**Dueño:** Miguel.

**Etiqueta de madurez:** `ENGINEERING` (esqueleto generado).

Importa el kernel común de `services/shared/src/api/{domain,application}` — no
duplica entidades ni puertos.
