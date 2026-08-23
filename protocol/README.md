# protocol/ — fuente única de verdad

Kotlin, Python y TypeScript **se generan** desde `proto/helius/v1/*.proto`
(`make proto`); nunca se escriben a mano. Ver `docs/PROTOCOL.md`.

- `proto/` — definiciones `.proto3` (Bundle, Status, Motion, Biomarker, Observation,
  Inventory, Incident, Identity). `Identity` (break-glass, ADR-0008) viaja
  fuera del `Bundle` — sync directo nodo→backend, nunca hop-by-hop por la malla.
- `beacon/BEACON_FORMAT.md` — layout de bytes del anuncio BLE (no es protobuf).
- `openapi/` — contrato REST del backend.
- `asyncapi/` — contrato del canal WebSocket en tiempo real.
- `test-vectors/` — al menos 5 bundles dorados (uno por tipo de payload) en JSON +
  binario, con test de *round-trip* Kotlin↔Python en CI (`protocol-ci.yml`). Un
  bundle serializado en Kotlin que no coincida byte a byte con el vector de Python
  hace fallar el CI — elimina la clase de bug más cara del proyecto.
- `codegen/` — scripts que regeneran el código en los tres lenguajes.

**Dueño:** Helmut. **Cambios aquí requieren revisión de Helmut (Transporte/DTN) y
Miguel (web/backend consumidor).**
