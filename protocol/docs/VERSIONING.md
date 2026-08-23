# Versionado del protocolo

- Los campos de un mensaje `proto3` **nunca se reutilizan** (no reciclar números de campo).
- Solo se **añaden** campos nuevos; los campos viejos se marcan `deprecated` en un comentario, nunca se borran del `.proto` mientras haya nodos viejos en la malla.
- `BundleHeader.version` permite negociación: un nodo con `VER` mayor debe poder interoperar con `VER-1` durante el handshake (Sección 6.5 del spec original).
- Un cambio **incompatible** (romper el layout de bytes del beacon, o el significado de un enum existente) requiere un ADR aprobado por el dueño de protocolo (Helmut) — plantilla en `docs/architecture/ADR/`.
- CI (`protocol-ci.yml`) regenera el código desde `.proto` en cada PR y falla si hay *drift* entre lo generado y lo commiteado.
