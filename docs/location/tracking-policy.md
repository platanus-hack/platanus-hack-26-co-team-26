# Adaptive tracking policy

| Profile | Starting interval | Typical use |
|---|---:|---|
| PASSIVE | 5 min | stationary or low-battery background preparation |
| NORMAL | 60 s | ordinary movement |
| ACTIVE | 15 s | rapid movement or critical-battery emergency fallback |
| EMERGENCY | 5 s | active emergency when battery permits |

Policy considers emergency state first, then critical battery, then movement and low battery. These are centralized defaults, not guarantees: Android may batch updates. The latest usable location, SOS, movement evidence, battery, and transport capacity take priority.

