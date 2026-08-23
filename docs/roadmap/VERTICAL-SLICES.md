# Roadmap por vertical slices

> **Regla:** no se empieza por PPG, ni por ML, ni por UI bonita. Se empieza por el
> circuito que demuestra la innovación central.

## Slice 0 — El corazón (máxima prioridad)

```
Teléfono A (modo avión) —"NECESITO AYUDA"→ Teléfono B (modo avión)
B se desplaza → Teléfono C recibe A+B
C obtiene Internet → el dashboard muestra a A
```

**Criterio de aceptación:** bundle firmado, verificado en backend, visible en
`/ops` con marca temporal y cadena de relevo completa. **Si esto funciona, ya
existe el producto.** Dueño: Helmut (transporte/DTN) + Miguel (backend/dashboard).

## Slice 1 — Evidencia de movimiento

`movimiento intencional → bundle → relevo → dashboard`, con métricas de falsos
positivos ante vibración. Dueño: Alex.

## Slice 2 — AIB

`PPG → pulso + SQI → bundle → dashboard`, primero con `HeuristicFallback`, luego
con el modelo LiteRT. Dueño: Laura/Jorge (captura) + Alex (modelo).

## Slice 3 — Localización probabilística

Tres rescatistas detectan al nodo A; el dashboard publica zona candidata con
radios de 68% y 95%. Dueño: Miguel.

**Extensión 3D (ADR-0009, después de que 2D funcione):** sumar piso/profundidad
estimado a partir de elevación UWB y barómetro, con su propia incertidumbre.
No bloquea el Slice 3 base — es una mejora de precisión, dueño Helmut (mediciones) + Miguel (factor graph).

## Slice 4 — Demo extremo a extremo

`evento sísmico simulado → activación → UI de emergencia → caída de red → DTN →
gateway → nube → dashboard público y de operaciones`. Dueño: todos.

## Slice 5 — Endurecimiento

Modos degradados, matriz de fabricantes, seguridad, batería, accesibilidad,
carga, caos, documentación de validación, publicación en Play Store. Dueño: todos.

## Orden de inversión intelectual (si hay que recortar)

1. DTN + comunicación offline real entre Android.
2. Gateway del rescatista.
3. Última ubicación conocida + grafo RF + localización probabilística.
4. Movimiento intencional / evidencia de actividad.
5. AIB: pulso con SQI.
6. Dashboard operacional.
7. Alerta / activación de evento.
8. Optimizaciones y modalidades experimentales (acústico, UWB).

Los cuatro primeros forman una tecnología coherente **aunque desaparezca todo lo
demás**.

## Fuera del MVP (no quemar tiempo)

Reconocimiento facial · ML gigante · LLM en el dispositivo · "diagnóstico médico
por IA" · blockchain · predicción sísmica · SpO2 clínico · mapa 3D de ruinas ·
enrutamiento IP ad-hoc verdadero · soporte mágico para teléfonos sin la app · iOS
(ver `docs/architecture/ADR/0002-android-only-kotlin.md`).

## Plan de entrada de iOS (fase 2)

Se documenta ahora para que las decisiones de hoy no lo bloqueen. **Disparador:**
Slice 4 demostrado, o alianza institucional que lo exija.

**Precondiciones que deben cumplirse durante la fase 1** (verificadas en cada PR
por `arch-guard`):

1. `core/commonMain` sin un solo import de Android.
2. `iosMain` declarado en Gradle pero vacío y comentado.
3. Todos los `expect` documentados con la nota de cómo se implementarían en iOS.
4. Solicitud de entitlement de Wi-Fi Aware y de Critical Alerts iniciada con antelación (el proceso es lento).
5. El protocolo no asume capacidades exclusivas de Android en el handshake.

**Trabajo estimado en fase 2:** implementar `actual` para transporte
(CoreBluetooth + Network.framework + Wi-Fi Aware), sensores (CoreMotion), cámara
(AVFoundation), almacén seguro (Keychain + Secure Enclave), y una UI SwiftUI. El
motor DTN, la criptografía, el DSP y el dominio **no se reescriben**.

**Nota realista:** la ejecución en background de iOS impondrá un modo degradado.
Se documentará con honestidad en lugar de disimularse.
