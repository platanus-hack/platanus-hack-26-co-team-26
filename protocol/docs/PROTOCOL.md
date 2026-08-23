# Protocolo SismoMesh — resumen normativo

**Fuente única de verdad:** `protocol/proto/sismomesh/v1/*.proto`. Kotlin, Python y
TypeScript se **generan**, nunca se escriben a mano (`make proto`, ver
`protocol/codegen/`).

## Formato de wire

- **Descubrimiento (BLE advertising):** binario compacto a medida, ver `protocol/beacon/BEACON_FORMAT.md`.
- **Bundles:** Protocol Buffers (proto3), compresión opcional. CBOR permitido solo para `raw` tier-2.
- **JSON:** únicamente en la API HTTP (`protocol/openapi/`) y en los vectores de test legibles.

## Tiers de tamaño

| Tier | Contenido | Presupuesto | Cuándo |
|---|---|---|---|
| T0 | estado, última ubicación, batería, flags | 40–120 B | Siempre, incluso solo por BLE. |
| T1 | features de movimiento, resumen de biomarcadores, observaciones de pares | 1–20 KB | Enlace estable ≥ 3 s. |
| T2 | RAW acelerómetro/giroscopio, onda PPG, diagnósticos | 0.1–10 MB | Solo Wi-Fi Aware / Direct / Internet. |

Orden estricto **T0 → T1 → T2**, con interrupción segura en cualquier punto.

## Versionado

Los campos nunca se reutilizan; solo se añaden. Un nodo con `VER` mayor debe poder
hablar con `VER-1` (negociación en el handshake). Un cambio incompatible requiere
ADR aprobado por el dueño de protocolo (Helmut) — ver `docs/architecture/ADR/`.

Ver también `protocol/docs/VERSIONING.md` y `protocol/docs/PRIORITIES.md`.

**Dueño:** Helmut. **Revisor obligatorio:** Miguel (consumidor backend) + Laura/Jorge (payload de biomarcadores).
