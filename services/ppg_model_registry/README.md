# services/ppg_model_registry

**Propósito:** registro opcional de modelos `.tflite` aprobados para el
clasificador AIB/PPG (`ppg_tiny_tcn_int8.tflite`). **Nunca** es parte de la ruta
de medición urgente — `core/signal/ppg` siempre funciona con
`SafetyFirstClassifier`/`HeuristicFallback` sin depender de este servicio.

Distribuye manifiestos con hash SHA-256 verificado por
`core/signal/ppg/SignalModelRunner.kt::ModelArtifactVerifier`. Un modelo solo se
sirve si existe el archivo `APPROVED` (creado por el proceso de gobernanza de
modelos, nunca automáticamente al exportar) — ver `docs/ppg/VALIDATION.md`.

**Dueño:** Alex (gobernanza de modelos). **Revisor obligatorio:** Miguel (despliegue backend).

**Etiqueta de madurez:** `ENGINEERING` (esqueleto + lógica real integrada).
