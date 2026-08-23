# SismoMesh Design System

SismoMesh communicates emergency evidence with Scandinavian restraint, operational density, and explicit uncertainty. The chosen direction is **Hybrid Adaptive**: calm light surfaces for public and preparation experiences; graphite dark mode for incident operations where map overlays must dominate.

## Design exploration

| Direction | Readability | Operations | Accessibility | Premium restraint | Total / 20 |
|---|---:|---:|---:|---:|---:|
| Nordic Operations | 5 | 3 | 5 | 4 | 17 |
| Dark Rescue Intelligence | 4 | 5 | 4 | 4 | 17 |
| Hybrid Adaptive | 5 | 5 | 5 | 4 | **19** |

Hybrid Adaptive wins because the public experience benefits from warm, approachable daylight surfaces while incident maps gain clarity from dark neutral chrome. This is one semantic system with two modes, not two products.

## Tokens

| Role | Light | Dark |
|---|---|---|
| Canvas | `#F4F2EC` | `#0D1518` |
| Surface | `#FBFAF7` | `#141E22` |
| Elevated | `#FFFFFF` | `#1B272B` |
| Border | `#D8DAD6` | `#2E3B3F` |
| Primary text | `#182226` | `#EDF1ED` |
| Secondary text | `#59686C` | `#AEB9B6` |
| Rescue teal | `#397F79` | `#58A69E` |
| Signal blue | `#557691` | `#7494AF` |
| Safe | `#557A63` | `#72A184` |
| Warning | `#B17B3D` | `#C89A58` |
| Critical | `#B94F4D` | `#D26A66` |
| Estimated | `#766D84` | `#9A8EAA` |

Use neutral surfaces for 80–90% of a screen. Teal identifies the product and current GPS. Red is reserved for SOS and confirmed critical system states; movement is amber/neutral evidence, never green.

## Typography and layout

Use Inter, Geist, or the system sans stack. Use JetBrains Mono/Consolas only for coordinates, timestamps, identifiers, RSSI, accuracy, and latency. Spacing follows `4, 8, 12, 16, 24, 32, 48, 64`. Controls use 8–10 px radii, panels 10–14 px. Minimum touch target is 44×44 px on mobile.

## Evidence semantics

- Current GPS: teal, solid circle, label “Current GPS”.
- Last known: signal blue, solid circle, always paired with age.
- Historical estimate: muted violet, visually distinct, always says “Historical estimate”.
- Relay observation: neutral slate with network and hop metadata.
- SOS: critical red with an explicit `SOS` label; never conveyed by color alone.
- Movement copy: “Recent device movement detected.” Never “alive”. Absence of movement never implies death.
- Freshness: `LIVE ≤30 s`, `RECENT ≤2 min`, `AGING ≤30 min`, otherwise `STALE`.

## Maps and charts

Basemaps are low saturation. Stable layer identifiers are defined in `docs/design/map-semantics.md`. 2D is the default overview; 3D uses pitch, terrain, and building extrusion only where source data exists. Rendered heights are context, not certified structural measurements. Charts answer a single operational question, include units and an accessible text summary, and avoid decorative gradients or fake 3D.

## Motion and effects

Micro interactions last 120–180 ms; panels 180–260 ms; map perspective 250–400 ms. Use at most one atmospheric effect and two animated interaction groups per screen. Respect `prefers-reduced-motion`. SOS, destructive actions, forms, and medical values remain visually stable.

## Accessibility and privacy

Target WCAG 2.1 AA, visible keyboard focus, semantic controls, screen-reader labels, responsive 320 px through ultrawide layouts, and text/icon/shape in addition to color. Public screens never contain identities, precise coordinates, history, movement traces, device identifiers, or physiology. Authorized views identify their role and show evidence provenance.

## Forbidden patterns

No emojis, neon/cyberpunk styling, generic card grids, excessive pills, uncontrolled colors, decorative red, glassmorphism everywhere, strong map gradients, continuous pulsing, or claims that movement proves life or experimental physiology is diagnostic.

