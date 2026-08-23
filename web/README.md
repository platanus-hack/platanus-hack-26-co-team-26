# web/ — landing + dashboard (React + Vite + TypeScript)

**Rutas y niveles de acceso (Sección 13.1) — code-splitting por ruta:**

| Vista | Ruta | Auth | Contenido |
|---|---|---|---|
| **Pública** | `/mapa` | no | Área afectada, conteos agregados, solicitudes agregadas. **Cero PII.** |
| **Familiar** | `/familia` | sí, por vínculo consentido | Estado del familiar con granularidad consentida. |
| **Respondiente** | `/ops` | sí, rol + organización | Identidad, observaciones exactas, evidencia de movimiento/biomarcadores, datos crudos. |
| **Landing** | `/` | no | Qué es / qué NO es, cómo prepararse, privacidad, descarga, "Disponible en Android. iOS en desarrollo." |

**Decisión explícita (Sección 13.1):** no se publica nombre, coordenada exacta,
condición ni pulso en la vista pública — ver `docs/security/THREAT-MODEL.md` § 14.3.

**Capas del mapa (deck.gl sobre MapLibre GL):** `ScatterplotLayer` (nodos),
`HeatmapLayer`/`ContourLayer` (verosimilitud), `ArcLayer` (grafo de encuentros con
RSSI como grosor), `TripsLayer` (recorrido de rescatistas), `PolygonLayer` (zonas).

**Dueño:** Miguel.

**Etiqueta de madurez:** `ENGINEERING` (esqueleto generado).
