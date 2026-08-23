# Sistema visual móvil Helios

## Dirección elegida

**Solar Cartography** combina cartografía, señal, luz y conexión humana. El
torneo interno comparó Solar Cartography, Calm Rescue y Signal Instrument; se
eligió Solar por su mejor equilibrio entre orientación, calma y diferenciación.

## Tokens

La implementación vive en `HeliosDesignSystem.kt`:

| Token | Uso |
|---|---|
| `HELIOS_INK` | fondo operativo |
| `DEEP_OCEAN` | superficie principal |
| `GRAPHITE_BLUE` | superficie elevada/mapa |
| `WARM_CLOUD` | texto principal |
| `HELIOS_SOLAR` | identidad y acciones de énfasis |
| `AQUA_SIGNAL` | red y conectividad |
| `LOCATION_SKY` | ubicación/geografía |
| `SAFE_MINT` | estado seguro |
| `SIGNAL_CORAL` | SOS/asistencia |
| `EVIDENCE_VIOLET` | estimación y fisiología derivada |

## Helios Pulse

`HeliosPulse` es un anillo con núcleo central. Se anima únicamente cuando hay
señal activa, búsqueda, alerta o captura PPG; en cabeceras tranquilas queda
estático. No sustituye texto de estado ni usa color como único indicador.

## Responsive

El shell usa `BoxWithConstraints`: teléfono mantiene una columna cómoda; desde
aproximadamente 720 dp el mapa y el contexto se muestran en paralelo. El sistema
mantiene touch targets de al menos 44 dp, spacing 4/8/12/16/24/32 y superficies
con radios 14–22 dp.

## Modos

- **Normal:** espacial, abierto, con mapa y preparación.
- **Apoyo:** más operativo, con reportes, alertas y personas autorizadas.
- **Asistencia:** señal coral centrada, pocas acciones, sin navegación normal.

## Mapa

El proveedor cartográfico Android aún no está conectado. La vista actual es un
fallback visual honesto: no inventa GPS, mantiene baja saturación y reserva
Solar/Aqua/Coral/Violet para marcadores semánticos cuando existan datos reales.
