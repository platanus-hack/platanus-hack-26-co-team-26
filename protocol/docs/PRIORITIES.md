# Pesos de priorización de reenvío

`ForwardingScorer` (core/dtn) calcula:

```
score = w1*severity + w2*age + w3*battery_risk
      + w4*delivery_probability + w5*ttl_urgency - w6*replication_count
```

Los pesos son **configurables por incidente** — el cloud los envía por DTN inversa
(`IncidentConfig.priority_weights_json`, Sección 8.6) al ganar conectividad el
gateway del rescatista.

## Valores por defecto (a calibrar con datos reales, ver `docs/validation/`)

| Escenario | w1 severity | w6 replication_count | Notas |
|---|---|---|---|
| `HELP` + batería < 3% | alto | bajo | replicación agresiva |
| `SAFE` + batería > 85% | bajo | alto | prioridad baja, se replica poco |

Estos valores son `ASSUMED` (ver taxonomía de trazabilidad del `README.md` raíz,
sección C.0) hasta que se calibren con el banco RF/DTN de `docs/validation/`.

**Dueño:** Helmut (motor + canal de configuración por incidente).
