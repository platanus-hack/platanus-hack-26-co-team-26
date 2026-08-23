# Vectores dorados

Pendiente de generar (Anexo A, punto 9 del spec original): al menos 5 bundles
dorados (uno por tipo de payload: `status`, `motion`, `biomarker`, `observation`,
`raw`) en `bundles/*.json` + `bundles/*.bin`, un beacon de ejemplo en
`beacons/*.hex`, y una firma de ejemplo en `signatures/*.json`.

**Regla:** un bundle serializado en Kotlin debe coincidir byte a byte con el vector
generado en Python (`protocol-ci.yml`). Sin excepciones — es la prueba que elimina
la clase de bug más cara del proyecto ("mi lado del contrato funciona en mi máquina").

**Dueño:** Helmut.
