"""Fuente única de verdad de los guiones de voz. Dueño: Helmut.

Mismo patrón que protocol/proto/: un solo lugar de donde se generan los
artefactos (aquí, audio; allá, código). No editar los .mp3 generados a mano,
editar este catálogo y volver a correr generate_voice_pack.py.

Vocabulario: ver docs/glossary.md — ningún texto de aquí puede prometer
encontrar/rescatar a alguien ni usar lenguaje clínico/diagnóstico.
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
    voice_settings=VoiceSettings(stability=0.5, similarity_boost=0.75, style=0.3),
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
    voice_settings=VoiceSettings(stability=0.85, similarity_boost=0.8, style=0.1),
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
    voice_settings=VoiceSettings(stability=0.6, similarity_boost=0.75, style=0.25),
)

CATALOG: list[VoiceEntry] = [RESCUER_INSTRUCTIONS, TRAPPED_CALM, TRAPPED_ACTIONABLE]
