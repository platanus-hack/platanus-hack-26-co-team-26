# Formato del beacon BLE (descubrimiento)

Presupuesto: **≤ 26 bytes** de payload de servicio (compatible con Legacy
Advertising, el denominador común de chipsets). Binario compacto a medida —
**nunca protobuf ni JSON** en el anuncio (Sección 6.1/6.2).

| Campo | Bytes | Notas |
|---|---|---|
| `MAGIC` | 2 | `0x5A 0x4D` |
| `VER` | 1 | versión de protocolo |
| `SESSION` | 2 | hash corto del `disaster_id` |
| `EPH_NODE_ID` | 8 | pseudónimo efímero por desastre |
| `FLAGS` | 1 | `HELP,SAFE,TRAPPED,RELAY,GATEWAY,PPG_OK,MOTION` (bitmask) |
| `BATTERY` | 1 | 0–100 |
| `STATUS` | 1 | enum `ResponseState` |
| `SEQ` | 2 | contador monótono |
| `HOPS` | 1 | saltos del bundle más antiguo pendiente |
| `AUTH` | 4 | HMAC truncado sobre lo anterior |

**Total: 23 bytes** (dentro del presupuesto de 26 B).

**Prohibido en broadcast:** nombre, cédula, dirección, condición médica, coordenadas
exactas. Ver `docs/security/THREAT-MODEL.md` § 14.3 (privacidad y cumplimiento).

Dueño: Helmut (formato + implementación en `:android:transport`).
