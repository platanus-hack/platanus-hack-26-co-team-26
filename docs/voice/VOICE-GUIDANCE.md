# Guía de voz asistida (ElevenLabs) — diseño y catálogo

**Dueño:** Helmut. **Revisor de vocabulario:** Laura (ver `docs/glossary.md`, aplica igual a guiones de voz que a UI/docs).

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

## Los 3 casos (v1)

El disparador es el estado local del teléfono, no algo que viaje por la malla.
Mapea directo a `PowerMode` (`core/application/ports/SystemPorts.kt`) más un
matiz de movilidad que solo existe en esta capa (no se agregó al protocolo
porque no necesita viajar entre nodos):

| Caso | Disparador | Para quién | Tono |
|---|---|---|---|
| `RESCUER_INSTRUCTIONS` | `PowerMode.RESCUER` | La persona que trae el teléfono y está buscando/asistiendo | Claro, directivo, profesional — sin prometer un resultado |
| `TRAPPED_CALM` | `PowerMode.TRAPPED` + `TrappedMobility.IMMOBILE` | La persona atrapada que no puede moverse | Lento, estable, sin dramatismo — bajar ansiedad, no generarla |
| `TRAPPED_ACTIONABLE` | `PowerMode.TRAPPED` + `TrappedMobility.MOBILE` | La persona atrapada pero que sí puede moverse dentro del espacio | Directivo pero calmado — pasos concretos, no solo contención |

`TrappedMobility` no viene de un sensor todavía — hoy es una entrada manual
(la persona o quien la asiste la selecciona en la UI) o queda en `UNKNOWN`, en
cuyo caso no se reproduce ningún audio (ver `VoiceGuidanceSelector.kt`, nunca
asume MOBILE por defecto — asumir mal aquí es peor que no sonar nada).

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

## Ajustes de voz sugeridos (ElevenLabs, `model_id: eleven_multilingual_v2`)

| Caso | `stability` | `similarity_boost` | `style` | Por qué |
|---|---|---|---|---|
| `RESCUER_INSTRUCTIONS` | 0.5 | 0.75 | 0.3 | Natural pero directivo, sin monotonía que reste urgencia |
| `TRAPPED_CALM` | 0.85 | 0.8 | 0.1 | Máxima estabilidad = mínima variación tonal = efecto calmante |
| `TRAPPED_ACTIONABLE` | 0.6 | 0.75 | 0.25 | Claridad de instrucción sin sonar ansioso |

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
