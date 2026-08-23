# Sistema visual HELIOS — Solar Cartography

HELIOS comunica evidencia de emergencia con claridad operativa, sobriedad y una incertidumbre explícita. La dirección elegida es **Solar Cartography**: cartografía de baja saturación, señales cálidas y una red humana visible sin estética cyberpunk.

## Design tournament

| Dirección | Lectura | Operación | Accesibilidad | Calma premium | Total / 20 |
|---|---:|---:|---:|---:|---:|
| Solar Cartography | 5 | 5 | 5 | 5 | **20** |
| Calm Rescue | 5 | 4 | 5 | 4 | 18 |
| Signal Instrument | 4 | 5 | 4 | 4 | 17 |

Solar Cartography gana porque une orientación espacial, señal y calidez sin saturar la interfaz. Calm Rescue aporta el lenguaje de reassurance para asistencia; Signal Instrument aporta la lectura de métricas en diagnóstico. Es un solo sistema semántico, no tres productos.

## Tokens semánticos

| Rol | Token | Valor |
|---|---|---|
| Fondo operativo | `HELIOS_INK` | `#07161E` |
| Superficie | `DEEP_OCEAN` | `#0D252D` |
| Elevada | `GRAPHITE_BLUE` | `#173741` |
| Texto cálido | `WARM_CLOUD` | `#F4F1E9` |
| Producto | `HELIOS_SOLAR` | `#F4B44A` |
| Red activa | `AQUA_SIGNAL` | `#35C4B2` |
| Ubicación | `LOCATION_SKY` | `#65C4E4` |
| Seguro | `SAFE_MINT` | `#69BA8E` |
| Asistencia | `SIGNAL_CORAL` | `#ED625E` |
| Estimación | `EVIDENCE_VIOLET` | `#9A86C8` |

Usa superficies neutrales en 80–90% de cada pantalla. Solar identifica el producto; aqua, la red; azul cielo, la geografía; coral, SOS; violeta, estimaciones. El movimiento es evidencia ámbar/neutral, nunca “vida”.

## Tipografía, layout y responsive

Usa la sans del sistema con jerarquía fuerte; mono solo para coordenadas,
timestamps, identificadores, RSSI, precisión y latencia. Spacing: `4, 8, 12,
16, 24, 32, 48, 64`. Controles de 14–16 dp, paneles de 18–22 dp y touch target
mínimo de 44×44 dp. En tablet, usa dos columnas para mapa/contexto cuando el
ancho disponible supera aproximadamente 720 dp.

## Helios Pulse y motion

`HeliosPulse` es el elemento de marca circular. Solo pulsa cuando comunica una
señal activa, búsqueda, alerta o captura; puede quedar estático para identidad y
estado tranquilo. Motion estándar dura 120–180 ms; cambios de panel 180–260 ms;
alertas y asistencia usan transiciones expresivas, pero no bloquean acciones.
No se anima todo al mismo tiempo.

## Evidence semantics

- Current GPS: teal, solid circle, label “Current GPS”.
- Last known: signal blue, solid circle, always paired with age.
- Historical estimate: muted violet, visually distinct, always says “Historical estimate”.
- Relay observation: neutral slate with network and hop metadata.
- SOS: critical red with an explicit `SOS` label; never conveyed by color alone.
- Movement copy: “Recent device movement detected.” Never “alive”. Absence of movement never implies death.
- Freshness: `LIVE ≤30 s`, `RECENT ≤2 min`, `AGING ≤30 min`, otherwise `STALE`.

## Mapa y marcadores

El shell Android usa una superficie de orientación local porque no hay
MapLibre/Google Maps ni teselas configuradas en este checkout. La superficie no
simula calles: solo muestra la lectura GPS real, su precisión y frescura. Cuando se
configure un proveedor autorizado, mantén 2D como vista principal, agua en Deep
Ocean, edificios Graphite Blue, carreteras azul grisáceo y labels Warm Cloud.
Marcadores: tú Solar, personas Aqua, SOS Coral, estimación histórica Violet.

## Identidad de aplicación

El launcher, el splash de Android y las superficies de autenticación usan el logo
oficial suministrado para HELIOS (`android/app/src/main/res/drawable/helios_logo.png`)
mediante icono adaptativo y fallback legacy. El nombre visible es `HELIOS`.

## Motion and effects

Micro interactions last 120–180 ms; panels 180–260 ms; map perspective 250–400 ms. Use at most one atmospheric effect and two animated interaction groups per screen. Respect `prefers-reduced-motion`. SOS, destructive actions, forms, and medical values remain visually stable.

## Accessibility and privacy

Target WCAG 2.1 AA, visible keyboard focus, semantic controls, screen-reader labels, responsive 320 px through ultrawide layouts, and text/icon/shape in addition to color. Public screens never contain identities, precise coordinates, history, movement traces, device identifiers, or physiology. Authorized views identify their role and show evidence provenance.

## Forbidden patterns

No emojis, neon/cyberpunk styling, generic card grids, excessive pills, uncontrolled colors, decorative red, glassmorphism everywhere, strong map gradients, continuous pulsing, or claims that movement proves life or experimental physiology is diagnostic.

