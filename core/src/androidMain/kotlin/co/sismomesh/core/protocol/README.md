# core/protocol (androidMain)

**Código 100% generado** desde `protocol/proto/sismomesh/v1/*.proto` con
`protocol/codegen/gen_kotlin.sh` (`protoc --java_out=... --kotlin_out=...`).
**No editar a mano** — cualquier cambio se pierde en la próxima regeneración.

**Por qué vive en `androidMain` y no en `commonMain`:** el runtime de
`protobuf-java`/`protobuf-kotlin` es JVM-only, no multiplatform. Con solo
`androidMain` activo (ver `core/src/iosMain/README.md`) esto es seguro; antes
de activar el target iOS (Fase 2) este código deberá quedar detrás de un puerto
de (de)serialización con `expect`/`actual`, o `iosMain` usará `SwiftProtobuf`
directamente — ver `docs/roadmap/VERTICAL-SLICES.md` § 19bis.

- `../../../java/co/sismomesh/core/protocol/v1/` — clases Java generadas (`--java_out`).
- Este directorio (`kotlin/co/sismomesh/core/protocol/v1/`) — extensiones DSL de Kotlin (`--kotlin_out`), p. ej. `bundle { header = ...; status = emergencyStatus { ... } }`.

**Dueño:** Helmut (consumidor principal vía `core/dtn`). **Revisor obligatorio:**
Alex (payload de biomarcadores) + Miguel (consumidor desde el backend).

**Etiqueta de madurez:** `REFERENCE` — es la fuente única de verdad del formato
de datos; cualquier cambio a los `.proto` requiere ADR
(`docs/architecture/ADR/0004-protobuf-wire-format.md`).
