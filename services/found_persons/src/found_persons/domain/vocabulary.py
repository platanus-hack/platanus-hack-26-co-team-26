"""Vocabulario del hallazgo — enums cerrados, alineados con `docs/glossary.md`.

Este servicio registra un hecho **verificado por una persona**: alguien que estaba
reportado como no localizado fue ubicado. No es una inferencia del motor de
localización (eso vive en `services/localization` y siempre habla de "zona candidata
con confianza"). Por eso aquí sí puede haber una dirección concreta: es el sitio
donde la persona está ahora, reportado por quien la vio.

Dueño: Miguel. Revisor obligatorio: Laura (vocabulario y claims).
"""

from enum import StrEnum


class SituationStatus(StrEnum):
    """Situación de una persona ya localizada.

    Enum cerrado. NUNCA agregar ALIVE/DEAD/INJURED ni equivalentes en español: el
    sistema no declara el estado vital de nadie (restricción no negociable 6 de
    `docs/glossary.md`, misma regla que `ResponseState` en :core:domain).
    """

    LOCATED_NO_CONTACT = "located_no_contact"
    """Ubicada por un tercero, sin contacto directo todavía (p. ej. tras escombro)."""

    LOCATED_CONTACT_ESTABLISHED = "located_contact_established"
    """Un respondiente estableció contacto directo con la persona."""

    AT_ASSEMBLY_POINT = "at_assembly_point"
    """Se encuentra en un punto de encuentro o albergue del incidente."""

    IN_TRANSFER = "in_transfer"
    """En traslado hacia otro punto. El destino puede ser un dato de salud."""

    AT_CARE_FACILITY = "at_care_facility"
    """En un centro asistencial. Implica dato sensible de salud (Ley 1581 art. 5)."""

    REUNIFIED = "reunified"
    """Entregada o reunificada con su núcleo familiar. Estado terminal esperado."""


#: Estados cuya sola divulgación revela un dato de salud (Ley 1581 art. 5) y que por
#: tanto exigen base legal habilitante para datos sensibles.
HEALTH_REVEALING_STATUSES: frozenset[SituationStatus] = frozenset(
    {SituationStatus.AT_CARE_FACILITY, SituationStatus.IN_TRANSFER}
)


class VerificationLevel(StrEnum):
    """Quién respalda el hallazgo. Ordenado de menor a mayor respaldo."""

    SELF_REPORTED = "self_reported"
    """La propia persona se reportó a través de la app."""

    THIRD_PARTY_REPORTED = "third_party_reported"
    """Un civil o familiar lo reporta. Sin verificar."""

    RESPONDER_VERIFIED = "responder_verified"
    """Un respondiente acreditado confirma haber visto a la persona."""

    AUTHORITY_VERIFIED = "authority_verified"
    """Una entidad pública lo consigna en ejercicio de sus funciones legales."""


#: Nivel mínimo para que un registro pueda salir del ámbito RESPONDER hacia la
#: familia. Un `third_party_reported` sin corroborar no se le comunica a una familia:
#: una falsa noticia de hallazgo hace más daño que la ausencia de noticia.
MIN_LEVEL_FOR_FAMILY_DISCLOSURE = VerificationLevel.RESPONDER_VERIFIED

_VERIFICATION_ORDER: dict[VerificationLevel, int] = {
    VerificationLevel.SELF_REPORTED: 1,
    VerificationLevel.THIRD_PARTY_REPORTED: 0,
    VerificationLevel.RESPONDER_VERIFIED: 2,
    VerificationLevel.AUTHORITY_VERIFIED: 3,
}


def at_least(level: VerificationLevel, minimum: VerificationLevel) -> bool:
    """`True` si `level` respalda tanto o más que `minimum`."""
    return _VERIFICATION_ORDER[level] >= _VERIFICATION_ORDER[minimum]


class RecordLifecycle(StrEnum):
    """Ciclo de vida del registro, independiente de la situación de la persona."""

    ACTIVE = "active"
    ERASED = "erased"
    """Supresión ejercida (art. 8 lit. e). Queda la lápida, no el dato personal."""
    ANONYMIZED = "anonymized"
    """Venció la retención: se conserva el agregado sin identificar a nadie."""
