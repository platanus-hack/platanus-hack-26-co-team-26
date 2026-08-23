# Validación, métricas y simulación

## Métricas de red

`P_discover(d, m)` (probabilidad de descubrimiento según distancia y material) ·
TTFC (Time To First Contact) · BDR (Bundle Delivery Ratio) · RCR (Relay
Completion Rate) · Bytes/Joule · Hop count · Delivery latency (P50/P95).

## Métricas de localización

Median Position Error, P95 Position Error, y **calibración de confianza** (¿el
68% declarado contiene realmente al 68% de los casos?), desglosado por LOS,
NLOS, hormigón, hormigón armado y escombro mixto.

## Matriz experimental de RF (con mediciones propias — plantilla)

| Material | Grosor | Distancia | BLE detect | Wi-Fi detect | RSSI medio | Entrega |
|---|---|---|---|---|---|---|
| Aire | — | 5 m | | | | |
| Ladrillo | | 5 m | | | | |
| Hormigón | | 5 m | | | | |
| Hormigón | | 10 m | | | | |
| Hormigón armado | | 5 m | | | | |
| HA × 2 capas | | | | | | |
| Metal | | | | | | |
| Escombro húmedo | | | | | | |
| Escombro mixto | | | | | | |

De aquí sale **nuestro propio modelo** de `n` y `L_material` — vale mucho más que
citar "BLE alcanza 100 metros".

## Matriz de dispositivos Android (crítica en Android-only)

| Fabricante | Modelo | API | Wi-Fi Aware | Wi-Fi Direct | UWB | BLE adv. | Background OK | RSSI offset |
|---|---|---|---|---|---|---|---|---|
| Samsung | | | | | | | | |
| Xiaomi | | | | | | | | |
| Motorola | | | | | | | | |
| Oppo/Realme | | | | | | | | |
| Huawei | | | | | | | | |
| Tecno/Infinix | | | | | | | | |

Mínimo **6 dispositivos reales** de gamas y fabricantes distintos. La columna
*Background OK* documenta si el fabricante mata el foreground service y bajo qué
condiciones. La columna *RSSI offset* calibra las diferencias de radio entre
modelos, necesarias para la localización.

## Métricas de batería

Consumo en %/hora medido en: `READY`, emergencia en reposo, beacon de emergencia,
relay activo, modo rescatista, sesión AIB. Uno de los mayores diferenciales de
investigación del proyecto.

## Simulador

`simulators/mesh_sim/` — eventos discretos con N nodos, posiciones aleatorias,
atenuación por escombros, probabilidad de contacto, batería, movilidad de
rescatistas. Permite demostrar, con números propios (nunca inventados):

```
Entrega directa (solo quien alcanza al rescatista): X % de nodos recuperados
Store-carry-forward:                                Y % de nodos recuperados
```

`simulators/fake_devices/` levanta nodos JVM que corren el `core` real y hablan
el protocolo real contra el backend real — la prueba de integración más valiosa
del proyecto, sin necesidad de teléfonos.

## Estrategia de pruebas

| Nivel | Qué | Herramienta |
|---|---|---|
| Unitario dominio | invariantes, políticas, prioridades | `kotlin.test` en JVM, `pytest` |
| DTN | escenarios A→B→C→R completos | `commonTest` con fakes, sin hardware |
| Contrato | Kotlin ↔ Python contra vectores dorados | CI `protocol-ci.yml` |
| Propiedad | serialización, orden de prioridad, Bloom filter | `kotest-property`, `hypothesis` |
| Instrumentado | BLE real, sensores, cámara | Android instrumented tests + dispositivos reales |
| Integración | nodos JVM + gateway + API real | `docker-compose` |
| E2E de campo | dos teléfonos en modo avión | checklist manual en `docs/validation/` |
| Carga | 10 000 bundles/min en ingest | `locust` |
| Caos | pérdida de enlace a mitad de transferencia, relojes desfasados, firmas inválidas | *toolkit* propio |
