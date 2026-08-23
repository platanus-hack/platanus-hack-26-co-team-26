# Guía de audio asistida — voz (ElevenLabs) + tonos de proximidad — diseño y catálogo

**Dueño:** Helmut. **Revisor de vocabulario:** Laura (ver `docs/glossary.md`, aplica igual a guiones de voz que a UI/docs).

**Fundamento:** ver [`PSYCHOLOGICAL-FIRST-AID-EVIDENCE.md`](PSYCHOLOGICAL-FIRST-AID-EVIDENCE.md) para el estado del arte y las referencias reales detrás de este diseño (Primeros Auxilios Psicológicos, respiración pautada, y los límites honestos de lo que no está probado para este escenario específico).

## Por qué esto NO es una llamada en vivo a la API

HELIUS opera durante y después de un evento sísmico, con los teléfonos en modo
avión formando la malla DTN (`core/dtn`). En ese escenario **no hay
conectividad a internet** — una app que dependa de una llamada en tiempo real
a `api.elevenlabs.io` para reproducir guía de voz fallaría exactamente cuando
más se necesita.

Por eso el patrón es el mismo que ya estaba anotado en `docs/ARCHITECTURE.md`
de la app Flutter (`main`): **generar el paquete de audio una sola vez, en
tiempo de desarrollo, con la API de ElevenLabs; empaquetarlo como asset
estático; y en el teléfono solo seleccionar cuál de los audios ya
embebidos reproducir**, según el estado local del dispositivo. Cero llamadas
de red en el momento de uso. Esto además hace el paquete **reutilizable por
cualquiera de las dos apps** (Kotlin o Flutter) — son archivos `.mp3`, no
código, así que no dependen de la decisión de stack.

## Los 6 casos de voz (v1)

El disparador es el estado local del teléfono, no algo que viaje por la malla.
Mapea directo a `PowerMode` (`core/application/ports/SystemPorts.kt`) más un
matiz de movilidad que solo existe en esta capa (no se agregó al protocolo
porque no necesita viajar entre nodos):

| Caso | Disparador | Para quién | Tono |
|---|---|---|---|
| `RESCUER_INSTRUCTIONS` | `PowerMode.RESCUER` | La persona que trae el teléfono y está buscando/asistiendo | Claro, directivo, profesional — sin prometer un resultado |
| `TRAPPED_CALM` | `PowerMode.TRAPPED` + `TrappedMobility.IMMOBILE` | La persona atrapada que no puede moverse | Lento, estable, sin dramatismo — bajar ansiedad, no generarla |
| `TRAPPED_ACTIONABLE` | `PowerMode.TRAPPED` + `TrappedMobility.MOBILE` | La persona atrapada pero que sí puede moverse dentro del espacio | Directivo pero calmado — pasos concretos, no solo contención |
| `MOBILITY_CHECK` | `PowerMode.TRAPPED` + `TrappedMobility.UNKNOWN` | La persona atrapada, antes de saber si puede moverse | Suave, sin presión — pide un movimiento pequeño y prudente |
| `PPG_FINGER_PLACEMENT` | Inicio de una sesión de captura PPG (cualquier `PowerMode`) | Quien va a iniciar la lectura de pulso, sea rescatista o la propia persona atrapada | Instructivo, paso a paso |
| `GYRO_SOS_PATTERN` | Recordatorio periódico durante `PowerMode.TRAPPED` + `TrappedMobility.MOBILE` | La persona atrapada que puede moverse, cada cierto tiempo mientras espera | Corto, directo, repetible |

`TrappedMobility` ya no es una casilla manual en la UI — empieza en `UNKNOWN`
y **`MOBILITY_CHECK` es lo que la resuelve**: en vez de quedarse en silencio
por no saber si la persona puede moverse (lo que hacía v1 de este documento),
le pide un movimiento pequeño y prudente. Si `MotionPort` capta evidencia de
movimiento después de eso, pasa a `MOBILE`; si no, a `IMMOBILE` (esa lógica de
umbral/tiempo de espera es del adaptador Android, pendiente, no de
`VoiceGuidanceSelector`, que sigue siendo puro). Ver
`VoiceGuidanceSelector.select()` y `.reminder()` en
`core/domain/voice/VoiceGuidance.kt`.

`GYRO_SOS_PATTERN` es un recordatorio corto y repetible del mismo patrón "3-3"
que `TRAPPED_ACTIONABLE` ya menciona una vez dentro de un guion más largo — la
idea es refrescar la evidencia de movimiento cada cierto tiempo sin tener que
reproducir el guion completo de nuevo. `MotionPatternDetector`
(`core/signal/motion/`) es exactamente lo que reconoce ese patrón en el lado
del sensor.

`PowerMode.READY` y `PowerMode.ALERT` no tienen audio en v1 — no hay
suficiente certeza del caso todavía. Se puede agregar un cuarto guion de
orientación inicial para `ALERT` más adelante si el equipo lo pide; no se
construyó ahora para no adivinar alcance de más.

## Reglas de vocabulario (obligatorias, ver `docs/glossary.md`)

- Nunca prometer que se va a encontrar/rescatar a alguien — la regla de oro
  del proyecto es "no prometemos encontrar a nadie".
- Nunca lenguaje clínico/diagnóstico (nada de "signos vitales", "herida",
  "gravedad").
- `RESCUER_INSTRUCTIONS` debe decir "zona candidata con confianza", nunca
  "ubicación exacta" — la localización siempre es probabilística
  (`GeoPoint.acc_m`, ADR-0009).

## Guiones v1 (español, ~100-150 palabras cada uno)

### `RESCUER_INSTRUCTIONS`

> Estás recibiendo evidencia de un nodo cercano. Esta es una zona candidata
> con nivel de confianza, no una ubicación exacta — acércate con cautela y
> confirma visualmente antes de actuar. Revisa la app: el nivel de batería y
> la última evidencia recibida te dicen qué tan reciente es la señal. Si el
> nodo reporta un patrón de movimiento de tres golpes, pausa, tres golpes,
> hay alguien que puede responder — intenta el mismo patrón para confirmar
> contacto. Evalúa la estabilidad de la estructura antes de acercarte más.
> Mantén tu propio teléfono anunciando: cada segundo que estés en la zona,
> también estás retransmitiendo evidencia de otros nodos hacia la malla. Si
> pierdes la señal, no te alejes de inmediato — la conexión BLE es
> intermitente por diseño, espera unos segundos antes de asumir que no hay
> nadie.

### `TRAPPED_CALM`

> Estoy aquí contigo. Vas a escuchar mi voz mientras esto dure. Respira
> despacio: inhala contando hasta cuatro... sostén... exhala contando hasta
> seis. Otra vez. Tu teléfono sigue funcionando, aunque no tenga señal —
> está guardando y compartiendo tu información apenas otro dispositivo pase
> cerca, sin que tengas que hacer nada. No necesitas moverte ni forzar
> nada. Si tienes espacio para golpear algo suave con calma, hazlo en
> grupos de tres, con una pausa entre cada grupo — eso es todo lo que hace
> falta, no tienes que gritar ni agotarte. Cuida tu energía. Vamos a
> repetir la respiración las veces que necesites: inhala... sostén...
> exhala. Estoy aquí.

### `TRAPPED_ACTIONABLE`

> Puedes moverte, así que vamos paso a paso. Primero, revisa lo que tienes
> alrededor antes de moverte más — busca bordes filosos, objetos
> inestables o que puedan caer. Si hay polvo en el aire, cúbrete nariz y
> boca con tela, aunque sea tu ropa. Busca la posición más estable posible
> y quédate ahí un momento antes de seguir explorando. Si puedes golpear
> una superficie dura, hazlo en grupos de tres golpes, pausa, tres golpes
> — tu teléfono puede reconocer ese patrón y lo va a compartir apenas
> encuentre otro dispositivo cerca. Baja el brillo de la pantalla para
> cuidar la batería. No fuerces aberturas ni escombros inestables. Revisa
> tu teléfono cada tanto, no todo el tiempo — también hay que cuidar la
> energía de quien está ahí contigo, tú mismo.

### `MOBILITY_CHECK`

> Necesito saber si puedes moverte un poco. No hagas ningún esfuerzo grande,
> ni te pongas en riesgo. Intenta algo pequeño: mover los dedos de una mano,
> girar la muñeca, o levantar el teléfono unos centímetros si lo tienes
> cerca. Tómate el tiempo que necesites. El teléfono va a sentir ese
> movimiento con sus sensores, y con eso vamos a saber cómo ayudarte mejor a
> partir de ahora. Si no puedes moverte, o moverte te causa dolor o te pone
> en riesgo, no te fuerces — quédate quieto, eso también es información
> válida. Voy a esperar.

### `PPG_FINGER_PLACEMENT`

> Vamos a intentar medir tu pulso con la cámara del teléfono. Cubre
> completamente la cámara trasera y la luz junto a ella con la yema de tu
> dedo índice, sin apretar fuerte, solo apoyarlo. Mantén el dedo quieto ahí,
> sin moverlo, durante unos quince segundos. Si ves que la luz se enciende,
> es normal, es parte de la medición. Si el teléfono te pide repetir la
> lectura, no es un error, es solo para confirmar el resultado. Esto no es
> un diagnóstico médico, es una señal más que se suma a lo que ya sabemos de
> ti.

### `GYRO_SOS_PATTERN`

> Si puedes, mueve o golpea el teléfono suavemente: tres veces, una pausa,
> tres veces más. Ese patrón es el que el teléfono reconoce como una señal
> tuya, consciente y deliberada, no un golpe accidental. Puedes repetirlo
> cada tanto mientras esperas. No necesitas hacerlo fuerte ni rápido, solo
> con ese ritmo de tres y tres.

## Ajustes de voz sugeridos (ElevenLabs, `model_id: eleven_multilingual_v2`)

| Caso | `stability` | `similarity_boost` | `style` | Por qué |
|---|---|---|---|---|
| `RESCUER_INSTRUCTIONS` | 0.5 | 0.75 | 0.3 | Natural pero directivo, sin monotonía que reste urgencia |
| `TRAPPED_CALM` | 0.85 | 0.8 | 0.1 | Máxima estabilidad = mínima variación tonal = efecto calmante |
| `TRAPPED_ACTIONABLE` | 0.6 | 0.75 | 0.25 | Claridad de instrucción sin sonar ansioso |
| `MOBILITY_CHECK` | 0.75 | 0.8 | 0.15 | Suave como `TRAPPED_CALM` pero con una petición concreta detrás |
| `PPG_FINGER_PLACEMENT` | 0.6 | 0.75 | 0.25 | Igual de instructivo que `TRAPPED_ACTIONABLE`, sin urgencia de riesgo |
| `GYRO_SOS_PATTERN` | 0.55 | 0.75 | 0.3 | Corto y claro — se va a repetir, no puede cansar ni sonar ansioso |

Elegir el `voice_id` queda a criterio del equipo (plan Creator incluye acceso
a toda la librería de voces de ElevenLabs) — no se fijó ninguna voz específica
en el catálogo, se pasa por variable de entorno o flag. Buscar una voz cálida,
en español, categoría "narración"/"calm" en la librería suele dar mejor
resultado que una voz de conversación genérica para `TRAPPED_CALM`.

## Cómo generar el paquete

Ver `tools/voice_pack/README.md`. Resumen: `catalog.py` es la fuente única
de verdad (igual patrón que `protocol/proto/` para el protocolo) —
`generate_voice_pack.py` la lee y llama a la API una vez por caso, guarda el
`.mp3` en `assets/voice/es/` y un `manifest.json` con checksum SHA-256 de
cada archivo para que la app pueda **validar integridad del paquete embebido
en modo avión** antes de confiar en él (criterio ya mencionado en los docs de
`main`: "validado en modo avión").

## Cómo se conecta con la app (Kotlin)

`core/src/commonMain/kotlin/co/helius/core/domain/voice/VoiceGuidance.kt`
define `VoiceGuidanceCase`, `TrappedMobility` y `VoiceGuidanceSelector` — lógica
pura, sin Android, testeada en JVM (`core/src/commonTest/.../VoiceGuidanceSelectorTest.kt`).
El puerto `VoiceGuidancePlaybackPort`
(`core/application/ports/VoicePorts.kt`) es la frontera hexagonal: quien
implemente el adaptador Android (Laura/Jorge, requiere `MediaPlayer` o
`ExoPlayer` y por lo tanto pruebas en dispositivo — **no se implementó aquí**,
ver `docs/validation/PHONE-READINESS.md`, mismo criterio que el resto del
transporte) solo necesita mapear `VoiceGuidanceCase.assetId` al archivo
correspondiente en `assets/voice/es/`.

## Proximidad del rescatista (tonos, NO voz ni ElevenLabs)

Además de los guiones hablados, HELIUS necesita retroalimentación auditiva
tipo "detector de metales" para el rescatista: un beep que suena más rápido a
medida que se acerca al teléfono de alguien atrapado, más un tono único
cuando aparece un peer nuevo en rango de escaneo BLE.

**Esto NO se genera con ElevenLabs, a propósito.** ElevenLabs es
texto-a-voz: produce un archivo fijo a partir de un guion fijo. La distancia
al peer cambia en vivo mientras el rescatista camina — no hay ningún guion
que grabar de antemano para "suena más rápido mientras te acercas", porque el
ritmo depende del RSSI real del momento (`TransportPort.observePeers()`, ya
existente). Tiene que sintetizarse en el dispositivo, en tiempo real, con un
oscilador o `ToneGenerator`, igual que un detector de metales o un contador
Geiger de verdad.

Lo que sí se construyó, en Kotlin puro y testeado en JVM (sin Android):

- `core/domain/proximity/ProximityAudioMapper.kt` — mapea RSSI (dBm) a un
  intervalo de beep en milisegundos: más cerca (RSSI más alto, más cerca de
  -40 dBm), beep más rápido; más lejos (hacia -95 dBm), más lento. Nunca por
  fuera de un rango perceptible por oído humano (120ms-1500ms). También
  define `OPERATIVE_RANGE_DBM`, el umbral a partir del cual vale la pena
  buscar visualmente en vez de seguir caminando guiado por el sonido.
  **RSSI no es distancia** (`docs/glossary.md`, restricción 7) — esto es
  ingeniería de producto (útil aunque impreciso), no una medición calibrada.
- `ProximityAlertReducer` — recibe cada avistamiento (`PeerId` + RSSI) y
  produce la lista de alertas a disparar: como mucho un chime de "peer
  nuevo" (solo la primera vez que se ve ese `PeerId` en la sesión de
  búsqueda — un peer BLE anuncia cada pocos segundos, no una sola vez) más
  siempre un beep con el ritmo correspondiente.
- `ProximityAudioPort` (`core/application/ports/ProximityPorts.kt`) — la
  frontera hacia el adaptador Android real (`ToneGenerator`/oscilador,
  pendiente, requiere dispositivo — mismo criterio que el resto de esta
  tabla).

Quien implemente el adaptador Android alimenta `ProximityAlertReducer` desde
`TransportPort.observePeers()` (ya filtrado a los peers relevantes, p. ej.
solo los que reportan `PowerMode.TRAPPED` en su beacon) y traduce cada
`ProximityAlert` al puerto: `Beep(intervalMs)` → `startBeeping`/`updateInterval`,
`NewPeerChime` → `playPeerDetectedChime`.
