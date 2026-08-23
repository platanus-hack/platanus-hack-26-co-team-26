# ADR-0009: Localización probabilística extendida a 3D (profundidad/piso)

**Estado:** aceptada
**Fecha:** 2026-08-22
**Dueño:** Helmut (mediciones RF/UWB) + Miguel (factor graph)

## Contexto

El diseño original estima una zona candidata 2D (lat/lon, radios de confianza
68%/95%) a partir de un factor graph sobre observaciones RSSI (Sección 9). Eso
es razonable para "en qué punto del mapa buscar", pero en un colapso la
pregunta operativa más costosa suele ser **"en qué piso o a qué profundidad"**,
no solo el punto en planta. RSSI solo no alcanza para eso: la variabilidad de
pérdida por material (`docs/validation/VALIDATION.md`) ya es alta en el plano
horizontal, y en el eje vertical (atravesar losas) es peor.

## Decisión

Se añade un tercer eje al modelo de localización, alimentado por fuentes que
**sí** aportan información vertical real, nunca inferido de RSSI puro:

| Fuente | Qué aporta | Confiabilidad |
|---|---|---|
| UWB (`elevation_deg`, `distance_m`) | Ángulo/distancia de corto alcance entre dos nodos | Alta si hay línea de vista parcial; degrada en NLOS extremo |
| Barómetro (`barometric_pressure_hpa`) | Diferencial de presión → altura relativa | Requiere calibración por edificio (altura de piso varía); útil como *prior* de piso, no de metros exactos |
| GNSS (`altitude_m` con `AltitudeSource.GNSS`) | Referencia absoluta débil en interiores | Solo como *prior* inicial antes de perder señal |

`GeoPoint` (`protocol/proto/helius/v1/status.proto`) gana
`altitude_m`/`altitude_acc_m`/`altitude_source`; `PeerObservation`
(`observation.proto`) gana los campos crudos de UWB y presión barométrica. El
factor graph de `services/localization` (Miguel) los fusiona igual que ya
fusiona RSSI: salida siempre con incertidumbre, nunca un punto/piso exacto.

Salida esperada (ejemplo, mismo formato que la Sección 9.3 pero en 3D):

```
Zona candidata
Centro: 4.65123, -74.08291, piso estimado 2 (±1)
Confianza: 68% dentro de 11 m (horizontal) / ±1 piso (vertical)
Basado en: 7 observaciones RSSI · 2 con UWB · 1 con barómetro
```

## Consecuencias

- Nuevo trabajo de calibración: la altura de piso no es universal (varía por
  edificio/país); se registra como parámetro `ASSUMED` por escenario, igual que
  `n` en el modelo log-distance — nunca una constante fija en código.
- `docs/validation/VALIDATION.md` gana una métrica nueva: error vertical
  (piso/profundidad) además de `Median/P95 Position Error`.
- El dashboard (`web/`, Miguel) puede mostrar corte por piso en el mapa de
  operaciones; **nunca** se etiqueta como "profundidad exacta" sin dato UWB/barométrico
  real detrás — si solo hay RSSI, el sistema no reporta eje vertical.
- No requiere hardware adicional: UWB y barómetro ya están en el teléfono en
  los modelos donde estén disponibles (UWB: Android 12+, hardware limitado — ver
  catálogo de madurez en el `README.md` raíz, `UWB ranging` = `PROVEN/dependiente
  de hardware`).
