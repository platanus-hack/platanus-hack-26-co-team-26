# SismoMesh — API

Base local: `http://127.0.0.1:8000` · Levantar: `make api` · Dashboard: `/`

Todos los cuerpos son JSON. Sin autenticación en el núcleo, salvo la
exportación (ver abajo).

---

## Ingesta (la usa el gateway)

### `POST /bundles/batch`

Sube un lote de bundles. **Idempotente**: reintentar con la misma
`Idempotency-Key` devuelve la respuesta original sin reprocesar.

```bash
curl -X POST localhost:8000/bundles/batch \
  -H 'Content-Type: application/json' -H 'Idempotency-Key: gw-001' \
  -d '{"bundles":[ ... ]}'
```

```json
{"received":3,"accepted":1,"duplicates":1,"rejected":1,"results":[...]}
```

Cada bundle pasa por tres filtros, en orden:

1. `signer_key_id` debe ser el hash de `signer_pubkey_b64` → si no, **suplantación**.
2. `payload_hash` debe coincidir con SHA-256 de los bytes recibidos → si no, **manipulación**.
3. Firma Ed25519 válida sobre esos mismos bytes.

Un rechazo **se registra** en la tabla `rejections`, no se descarta. Que la
malla detecte el ataque es parte de lo que hay que poder mostrar.

---

## Consulta (la usa el dashboard)

| Endpoint | Devuelve |
|---|---|
| `GET /incidents` | Incidentes con conteo de bundles |
| `GET /incidents/{id}/nodes` | Último estado por nodo (sólo verificados) |
| `GET /incidents/{id}/bundles?since=&limit=` | Timeline; `since` = cursor de la llamada anterior |
| `GET /incidents/{id}/rejections` | Intentos rechazados y su motivo |
| `GET /health` | Conteos y nombre de la DB |
| `POST /admin/reset` | Vacía todo. Para ensayos |

---

## Exportación para organismos de socorro

Pensada para Cruz Roja, Defensa Civil y equipos de búsqueda: un listado
priorizado, consumible con herramientas que ya usan.

| Endpoint | Formato | Para qué |
|---|---|---|
| `GET /incidents/{id}/triage` | JSON | Integración con sistemas propios |
| `GET /incidents/{id}/triage.csv` | CSV | Planilla, radio, impresión |
| `GET /incidents/{id}/triage.geojson` | GeoJSON | QGIS, Google Earth, uMap |

Parámetro `max_rank` filtra por urgencia: `?max_rank=1` devuelve sólo críticos.

```bash
curl 'localhost:8000/incidents/demo-bogota-01/triage.csv?max_rank=2' -o criticos.csv
```

### Cómo se prioriza

| `triage` | rank | Origen |
|---|---|---|
| `CRITICO` | 1 | Reportó `TRAPPED` |
| `ALTO` | 2 | Reportó `HELP` |
| `POR_CONFIRMAR` | 3 | `UNCONFIRMED` |
| `ESTABLE` | 4 | Reportó `SAFE` |

**La prioridad sale únicamente del estado autorreportado.** La antigüedad del
dato y la batería baja se informan como banderas (`dato_vigente`,
`observaciones`) pero **no degradan el rank**, por dos razones: alguien que
reportó `TRAPPED` hace cinco horas sigue atrapado, y una batería agonizante
significa que dejará de reportar — razón para llegar antes, no después.

### Reglas de calidad en el borde de salida

- **`fc_bpm` sólo se exporta si `fc_sqi >= 0.5`.** Bajo ese umbral el campo sale
  en `null` y se anota *"PPG descartado por señal insuficiente"*. El HR malo no
  se filtra sólo en la app: se filtra también aquí.
- **Celda vacía = sin dato.** Nunca cero, nunca un valor por defecto.
- Todas las respuestas incluyen `advertencia`: los datos son autorreportados y
  derivados de sensores de teléfono, **no** constituyen diagnóstico clínico ni
  confirmación de ubicación exacta.
- Sin PII: los nodos se identifican por seudónimo derivado de su clave pública.

### Autenticación

Opcional y desactivada por defecto, para que el demo no tenga fricción:

```bash
export SISMOMESH_EXPORT_KEY=una-clave-larga
curl -H 'X-API-Key: una-clave-larga' localhost:8000/incidents/demo-bogota-01/triage
```

Si la variable no está definida, los endpoints de exportación son abiertos. En
cualquier despliegue real hay que definirla.
