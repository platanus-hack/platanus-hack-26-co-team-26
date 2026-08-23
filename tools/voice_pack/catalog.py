"""Fuente única de verdad de los guiones de voz. Dueño: Helmut.

Mismo patrón que protocol/proto/: un solo lugar de donde se generan los
artefactos (aquí, audio; allá, código). No editar los .mp3 generados a mano,
editar este catálogo y volver a correr generate_voice_pack.py.

Vocabulario: ver docs/glossary.md — ningún texto de aquí puede prometer
encontrar/rescatar a alguien ni usar lenguaje clínico/diagnóstico.

Voz elegida por el equipo (escuchando muestras reales, no por la descripción
de catálogo): Daniela, ElevenLabs voice_id "tOyBjc1xwZQ2wFR7GLaO" — español
latinoamericano. Los `stability`/`style` de cada entrada abajo se calibraron
sobre esa voz específica; si el equipo cambia de voz, hay que reescuchar y
recalibrar, no asumir que los mismos números suenan igual en otra voz.
"""

from dataclasses import dataclass, field


@dataclass(frozen=True)
class VoiceSettings:
    stability: float
    similarity_boost: float
    style: float
    use_speaker_boost: bool = True


@dataclass(frozen=True)
class VoiceEntry:
    case_id: str
    """Debe coincidir exactamente con VoiceGuidanceCase.assetId en
    core/src/commonMain/kotlin/co/helius/core/domain/voice/VoiceGuidance.kt."""
    text: str
    voice_settings: VoiceSettings
    locale: str = "es"


RESCUER_INSTRUCTIONS = VoiceEntry(
    case_id="rescuer_instructions",
    text=(
        "Estás recibiendo evidencia de un nodo cercano. Esta es una zona "
        "candidata con nivel de confianza, no una ubicación exacta — "
        "acércate con cautela y confirma visualmente antes de actuar. "
        "Revisa la app: el nivel de batería y la última evidencia recibida "
        "te dicen qué tan reciente es la señal. Si el nodo reporta un "
        "patrón de movimiento de tres golpes, pausa, tres golpes, hay "
        "alguien que puede responder — intenta el mismo patrón para "
        "confirmar contacto. Evalúa la estabilidad de la estructura antes "
        "de acercarte más. Mantén tu propio teléfono anunciando: cada "
        "segundo que estés en la zona, también estás retransmitiendo "
        "evidencia de otros nodos hacia la malla. Si pierdes la señal, no "
        "te alejes de inmediato — la conexión BLE es intermitente por "
        "diseño, espera unos segundos antes de asumir que no hay nadie."
    ),
    voice_settings=VoiceSettings(stability=0.45, similarity_boost=0.78, style=0.3),
)

TRAPPED_CALM = VoiceEntry(
    case_id="trapped_calm",
    text=(
        "Estoy aquí contigo. Vas a escuchar mi voz mientras esto dure. "
        "Respira despacio: inhala contando hasta cuatro... sostén... "
        "exhala contando hasta seis. Otra vez. Tu teléfono sigue "
        "funcionando, aunque no tenga señal — está guardando y "
        "compartiendo tu información apenas otro dispositivo pase cerca, "
        "sin que tengas que hacer nada. No necesitas moverte ni forzar "
        "nada. Si tienes espacio para golpear algo suave con calma, "
        "hazlo en grupos de tres, con una pausa entre cada grupo — eso es "
        "todo lo que hace falta, no tienes que gritar ni agotarte. Cuida "
        "tu energía. Vamos a repetir la respiración las veces que "
        "necesites: inhala... sostén... exhala. Estoy aquí."
    ),
    voice_settings=VoiceSettings(stability=0.42, similarity_boost=0.78, style=0.35),
)

TRAPPED_ACTIONABLE = VoiceEntry(
    case_id="trapped_actionable",
    text=(
        "Puedes moverte, así que vamos paso a paso. Primero, revisa lo "
        "que tienes alrededor antes de moverte más — busca bordes "
        "filosos, objetos inestables o que puedan caer. Si hay polvo en "
        "el aire, cúbrete nariz y boca con tela, aunque sea tu ropa. "
        "Busca la posición más estable posible y quédate ahí un momento "
        "antes de seguir explorando. Si puedes golpear una superficie "
        "dura, hazlo en grupos de tres golpes, pausa, tres golpes — tu "
        "teléfono puede reconocer ese patrón y lo va a compartir apenas "
        "encuentre otro dispositivo cerca. Baja el brillo de la pantalla "
        "para cuidar la batería. No fuerces aberturas ni escombros "
        "inestables. Revisa tu teléfono cada tanto, no todo el tiempo — "
        "también hay que cuidar la energía de quien está ahí contigo, tú "
        "mismo."
    ),
    voice_settings=VoiceSettings(stability=0.45, similarity_boost=0.78, style=0.32),
)

MOBILITY_CHECK = VoiceEntry(
    case_id="mobility_check",
    text=(
        "Necesito saber si puedes moverte un poco. No hagas ningún esfuerzo "
        "grande, ni te pongas en riesgo. Intenta algo pequeño: mover los "
        "dedos de una mano, girar la muñeca, o levantar el teléfono unos "
        "centímetros si lo tienes cerca. Tómate el tiempo que necesites. El "
        "teléfono va a sentir ese movimiento con sus sensores, y con eso "
        "vamos a saber cómo ayudarte mejor a partir de ahora. Si no puedes "
        "moverte, o moverte te causa dolor o te pone en riesgo, no te "
        "fuerces — quédate quieto, eso también es información válida. Voy "
        "a esperar."
    ),
    voice_settings=VoiceSettings(stability=0.42, similarity_boost=0.78, style=0.33),
)

PPG_FINGER_PLACEMENT = VoiceEntry(
    case_id="ppg_finger_placement",
    text=(
        "Vamos a intentar medir tu pulso con la cámara del teléfono. Cubre "
        "completamente la cámara trasera y la luz junto a ella con la yema "
        "de tu dedo índice, sin apretar fuerte, solo apoyarlo. Mantén el "
        "dedo quieto ahí, sin moverlo, durante unos quince segundos. Si ves "
        "que la luz se enciende, es normal, es parte de la medición. Si el "
        "teléfono te pide repetir la lectura, no es un error, es solo para "
        "confirmar el resultado. Esto no es un diagnóstico médico, es una "
        "señal más que se suma a lo que ya sabemos de ti."
    ),
    voice_settings=VoiceSettings(stability=0.48, similarity_boost=0.78, style=0.28),
)

GYRO_SOS_PATTERN = VoiceEntry(
    case_id="gyro_sos_pattern",
    text=(
        "Si puedes, mueve o golpea el teléfono suavemente: tres veces, una "
        "pausa, tres veces más. Ese patrón es el que el teléfono reconoce "
        "como una señal tuya, consciente y deliberada, no un golpe "
        "accidental. Puedes repetirlo cada tanto mientras esperas. No "
        "necesitas hacerlo fuerte ni rápido, solo con ese ritmo de tres y "
        "tres."
    ),
    voice_settings=VoiceSettings(stability=0.42, similarity_boost=0.78, style=0.35),
)

CATALOG: list[VoiceEntry] = [
    RESCUER_INSTRUCTIONS,
    TRAPPED_CALM,
    TRAPPED_ACTIONABLE,
    MOBILITY_CHECK,
    PPG_FINGER_PLACEMENT,
    GYRO_SOS_PATTERN,
]
