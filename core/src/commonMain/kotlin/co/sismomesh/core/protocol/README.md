# core/protocol

**Propósito:** tipos Kotlin generados desde `protocol/proto/sismomesh/v1/*.proto`
(codegen — nunca se escriben a mano, ver `protocol/codegen/gen_kotlin.sh`) más las
declaraciones `expect` de codificación/decodificación de wire que necesitan
`actual` por plataforma.

**Dueño:** Helmut (consumidor principal vía `core/dtn`). **Revisor obligatorio:** Alex (payload de biomarcadores) + Miguel (consumidor desde el backend).

**Etiqueta de madurez:** `REFERENCE` — es la fuente única de verdad del formato de datos; cualquier cambio requiere ADR (ver `docs/architecture/ADR/`).

Este directorio se regenera con `make proto`. No commitear ediciones manuales.
