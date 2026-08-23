# División del trabajo (5 desarrolladores)

Cuatro frentes claros, cada uno con dueño primario y frontera de contrato explícita
con los demás. Se sincroniza a diario (ver `CONTRIBUTING.md`).

## Asignación

### Helmut — Transporte, DTN, protocolo y criptografía ("el corazón de la malla")

- `:android:transport`: BLE (advertising, scan, GATT), Wi-Fi Aware, Wi-Fi Direct, Nearby, UWB oportunista.
- `core/dtn` (100% Kotlin puro, testeable en JVM sin ningún teléfono): `BundleStore`, `InventoryBloom`, `ForwardingScorer`, `EncounterStateMachine`, `PriorityQueue`, `DyingGasp`.
- `core/crypto`: identidad Ed25519, handshake X25519+HKDF, cifrado de payload, firma de bundles, break-glass.
- `protocol/`: contratos `.proto`, formato del beacon BLE, vectores dorados, versionado.
- `:android:storage` (SQLDelight + SQLCipher) y `:android:power` (modos de energía, Doze).

**Misión:** dos teléfonos en modo avión intercambian un bundle T0 en menos de 4
segundos y lo retransmiten a un tercero, con el servicio sobreviviendo en
background al menos 4 fabricantes distintos.

### Miguel — Backend, localización, dashboard y landing ("todo lo que corre en la nube")

- `services/shared/src/api`: REST + WebSocket, auth, autorización por rol.
- `services/alert_ingestor`, `services/bundle_ingestor`, `services/notifier`, `services/analytics`.
- `services/localization`: factor graph, modelo de propagación RF, heatmaps, zonas candidatas.
- `web/`: landing pública, dashboard (`/mapa`, `/familia`, `/ops`), deck.gl + MapLibre.
- `simulators/`, integración final, CI/release, observabilidad.

**Misión:** tres observadores caminando alrededor de un colapso producen una zona
candidata con confianza calibrada, visible en el dashboard en tiempo real.

### Laura + Jorge — App Android (diseño y desarrollo) + captura AIB

- `:android:app`: Compose, navegación, DI, `EmergencyForegroundService`.
- UI de emergencia (atrapado), preparación (contactos, puntos de encuentro), rescatista, design system — diseño **y** desarrollo conjunto de toda la experiencia móvil.
- `:android:ppg`: CameraX, bloqueo de exposición/ISO/WB, detección de contacto, ROI, extracción de la serie RGB 1D.
- Sesiones AIB: almacenamiento, resumen T1, forma de onda T2.
- Alternativas de activación para personas lesionadas (pulsación larga, combinación de botones, patrón de sacudida, disparador por voz).

**Misión:** un teléfono con el dedo sobre la cámara produce una estimación de
pulso con confianza calibrada, y ese resultado viaja como bundle firmado.

### Alex — Modelo AIB (ML) + motor de evidencia de actividad

- `ml/ppg/`: dataset propio, preprocesado, entrenamiento, cuantización int8, exportación a LiteRT.
- `core/signal` (Kotlin puro, testeable con grabaciones, sin teléfono): DSP de PPG (FFT/PSD, detección de picos, SQI) y de movimiento (RMS, energía, ZCR, entropía espectral, patrón intencional).
- `:android:inference`: carga del modelo LiteRT, delegados NNAPI/GPU, `HeuristicFallback` obligatorio.
- `AttentionLevelPolicy` en `core/domain/policy` — combinación de evidencia, sin vocabulario clínico.

**Misión:** modelo < 300 KB, < 30 ms de latencia, con confianza calibrada y
métricas publicadas por subgrupo (tono de piel, modelo de dispositivo, movimiento).

## Fronteras de contrato explícitas

| Frontera | Quién | Qué se congela desde la semana 1 |
|---|---|---|
| `BiomarkerInferencePort` + formato del tensor de entrada | Laura/Jorge ↔ Alex | Laura/Jorge son dueños de la captura e integración en la app; Alex es dueño del modelo, el DSP y su validación. |
| `protocol/proto/**` | Helmut ↔ todos | Cualquier cambio de wire format requiere ADR aprobado por Helmut. |
| `core/domain` | Helmut ↔ Alex | Cambios revisados por Alex (consumidor vía policies). |
| Vocabulario clínico / claims | Laura+Jorge (UI) | Revisor obligatorio: Alex — ver `docs/glossary.md`. |
| Privacidad y exposición de PII | Miguel (backend/vistas) | Revisor obligatorio: Helmut (cifrado, break-glass). |
| Consumo de batería | Helmut (motor DTN) | Revisor obligatorio: Laura/Jorge (impacto en experiencia de app). |

## Responsabilidades compartidas

| Área | Dueño | Revisor obligatorio |
|---|---|---|
| Cambios en `protocol/` | Helmut | Miguel + Laura/Jorge |
| Cambios en `core/domain` | Helmut | Alex |
| Vocabulario clínico/claims | Laura/Jorge | Alex |
| Privacidad y exposición de PII | Miguel | Helmut |
| Consumo de batería | Helmut | Laura/Jorge |
| Preparación para iOS (§ ADR-0002/0003) | Helmut | — (revisar que nada de Android se filtre a `commonMain`) |

## Estrategia de ramas

```
main                 siempre desplegable, protegida
develop              integración continua (esta rama)
release/vX.Y         estabilización

feat/android-app     Laura, Jorge
feat/aib-capture     Laura
feat/aib-model       Alex
feat/motion-engine   Alex
feat/core-signal     Alex
feat/transport-ble   Helmut
feat/core-dtn        Helmut
feat/protocol        Helmut
feat/core-crypto     Helmut
feat/backend-api     Miguel
feat/alert-ingest    Miguel
feat/localization    Miguel
feat/web-dashboard   Miguel
feat/simulators      Miguel
```

**Convenciones:** Conventional Commits (`feat(transport): ...`), plantilla de PR,
mínimo 1 aprobación, CI verde obligatoria, `CODEOWNERS` por carpeta. Cambios en
`protocol/` o en `core/domain` requieren ADR (`docs/architecture/ADR/`).

## Ritmo de trabajo

- **Sincronización diaria de 15 minutos** con un único punto: *qué bloquea el
  Vertical Slice actual* — ver `docs/roadmap/VERTICAL-SLICES.md`.
- **Demo obligatoria cada 48 horas**, aunque sea fea. Si no hay demo, hay un
  problema arquitectónico oculto.
- **Congelación de contratos los lunes**; cambios de protocolo solo en ventana acordada.

Ver también `docs/onboarding/FIRST-72-HOURS.md` para el arranque concreto.
