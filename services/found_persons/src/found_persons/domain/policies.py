"""Minimización y decisión de divulgación — el corazón del cumplimiento.

Todo el servicio converge aquí: no hay un solo camino por el que un dato salga de
este proceso sin haber pasado por `decide()`. La API HTTP, la cápsula de malla y el
listado usan la misma función, así que no puede haber un endpoint "olvidado" con
reglas más laxas.

Dueño: Miguel. Revisor obligatorio: Laura (interés superior del NNA) + Helmut (malla).
"""

from __future__ import annotations

from dataclasses import dataclass, field

from found_persons.domain.habeas_data import (
    DataCategory,
    DisclosureScope,
    LegalBasis,
    Purpose,
)
from found_persons.domain.records import FoundPersonRecord, display_initials
from found_persons.domain.vocabulary import (
    MIN_LEVEL_FOR_FAMILY_DISCLOSURE,
    RecordLifecycle,
    SituationStatus,
    VerificationLevel,
    at_least,
)

#: Techo por ámbito (ADR-0007). Es un **máximo**, no un permiso: lo que realmente
#: se entrega es esta fila intersecada con lo que el Titular autorizó y con lo que
#: el registro contiene. Ampliar una fila de esta tabla exige ADR.
SCOPE_CEILING: dict[DisclosureScope, frozenset[DataCategory]] = {
    DisclosureScope.PUBLIC: frozenset(),
    DisclosureScope.FAMILY: frozenset(
        {DataCategory.IDENTITY, DataCategory.PLACEMENT, DataCategory.CONTACT}
    ),
    DisclosureScope.RESPONDER: frozenset(
        {
            DataCategory.IDENTITY,
            DataCategory.PLACEMENT,
            DataCategory.CONTACT,
            DataCategory.HEALTH_RELATED,
            DataCategory.MINOR,
        }
    ),
    DisclosureScope.AUTHORITY: frozenset(DataCategory),
}

#: Vigencia de una cápsula divulgada por malla, por ámbito. Cuanto más sensible es
#: lo que lleva, menos tiempo puede quedarse en un teléfono ajeno (art. 4 lit. c).
CAPSULE_TTL_MS: dict[DisclosureScope, int] = {
    DisclosureScope.PUBLIC: 24 * 3_600_000,
    DisclosureScope.FAMILY: 12 * 3_600_000,
    DisclosureScope.RESPONDER: 6 * 3_600_000,
    DisclosureScope.AUTHORITY: 6 * 3_600_000,
}

#: Retención operativa por defecto (30 días), según `docs/security/THREAT-MODEL.md`.
DEFAULT_RETENTION_MS = 30 * 24 * 3_600_000

#: Bases legales que habilitan contarle a la familia el hallazgo de un NNA. La
#: verificación por autoridad es la vía alterna cuando no hay representante legal
#: localizable, que es el caso frecuente en un desastre.
BASES_FOR_MINOR_FAMILY_DISCLOSURE: frozenset[LegalBasis] = frozenset(
    {LegalBasis.LEGAL_GUARDIAN_CONSENT, LegalBasis.PUBLIC_AUTHORITY_DUTY}
)

#: Consultas por dispositivo y hora. Un teléfono legítimo pregunta por la gente que
#: conoce; el que pregunta cien veces está recolectando.
DEVICE_HOURLY_QUOTA = 60


@dataclass(frozen=True, slots=True)
class DisclosureDecision:
    """Resultado de evaluar una divulgación. Se audita tanto si concede como si niega."""

    granted: bool
    categories: frozenset[DataCategory]
    scope: DisclosureScope
    purpose: Purpose
    withheld: frozenset[DataCategory] = frozenset()
    """Categorías que el registro contiene y que esta decisión no entrega."""

    reasons: tuple[str, ...] = ()
    """Motivos legibles. Si `granted` es falso, esto es lo que se le responde."""

    @property
    def outcome(self) -> str:
        """Lo que se escribe en `audit_log`. `partial` significa que hubo recorte,
        no que la entrega fuera incompleta por error."""
        if not self.granted:
            return "denied"
        return "partial" if self.withheld else "granted"


@dataclass(frozen=True, slots=True)
class DisclosureView:
    """Proyección minimizada de un registro. Es lo único que sale del hexágono.

    Cada campo opcional es `None` cuando su categoría no fue concedida — no se
    inventa un placeholder, porque la ausencia también es información honesta.
    """

    record_id: str
    incident_id: str
    status: SituationStatus
    verification: VerificationLevel
    found_at: int
    updated_at: int
    version: int
    scope: DisclosureScope
    categories: frozenset[DataCategory]
    display_name: str | None = None
    initials: str | None = None
    document_type: str | None = None
    document_number: str | None = None
    is_minor: bool = False
    site_name: str | None = None
    site_type: str | None = None
    municipality: str | None = None
    address: str | None = None
    lat: float | None = None
    lon: float | None = None
    contacts: tuple[dict[str, str], ...] = ()
    care_notes: str | None = None
    biometric_ref: str | None = None
    withheld: tuple[str, ...] = field(default_factory=tuple)
    """Categorías presentes en el registro que no se entregaron. Se declara en la
    respuesta: el solicitante debe saber que hay más y que no le corresponde."""


def decide(
    record: FoundPersonRecord,
    *,
    scope: DisclosureScope,
    purpose: Purpose,
    now_ms: int,
) -> DisclosureDecision:
    """¿Puede este ámbito ver este registro para esta finalidad, y qué parte?

    El orden de las comprobaciones es deliberado: primero lo que niega del todo,
    después lo que recorta. Así el motivo que se devuelve es siempre el más
    específico posible.
    """
    reasons: list[str] = []

    if record.lifecycle is RecordLifecycle.ERASED:
        return DisclosureDecision(
            granted=False,
            categories=frozenset(),
            scope=scope,
            purpose=purpose,
            reasons=(
                (
                    "El Titular ejerció su derecho de supresión (Ley 1581 art. 8 lit. e). "
                    "Cualquier copia local debe eliminarse."
                ),
            ),
        )

    if record.lifecycle is RecordLifecycle.ANONYMIZED:
        return DisclosureDecision(
            granted=False,
            categories=frozenset(),
            scope=scope,
            purpose=purpose,
            reasons=(
                (
                    "Venció la retención del dato operativo; solo sobrevive el agregado "
                    "anonimizado (Ley 1581 art. 4 lit. c)."
                ),
            ),
        )

    if not record.consent.is_active(now_ms):
        detail = (
            "revocada por el Titular"
            if record.consent.revoked_at is not None
            else "caducada"
        )
        return DisclosureDecision(
            granted=False,
            categories=frozenset(),
            scope=scope,
            purpose=purpose,
            reasons=(
                (
                    f"La base legal '{record.consent.legal_basis.value}' está {detail} "
                    "(Ley 1581 art. 8 lit. e y art. 9)."
                ),
            ),
        )

    if purpose not in record.consent.purposes:
        return DisclosureDecision(
            granted=False,
            categories=frozenset(),
            scope=scope,
            purpose=purpose,
            reasons=(
                (
                    f"La finalidad '{purpose.value}' no está entre las autorizadas "
                    f"({', '.join(sorted(p.value for p in record.consent.purposes))}). "
                    "Principio de finalidad, Ley 1581 art. 4 lit. b."
                ),
            ),
        )

    if scope not in record.consent.scopes:
        return DisclosureDecision(
            granted=False,
            categories=frozenset(),
            scope=scope,
            purpose=purpose,
            reasons=(
                (
                    f"El ámbito '{scope.value}' no fue consentido para este registro "
                    "(ADR-0007, principio de acceso restringido, art. 4 lit. f)."
                ),
            ),
        )

    if scope is DisclosureScope.FAMILY and not at_least(
        record.verification, MIN_LEVEL_FOR_FAMILY_DISCLOSURE
    ):
        return DisclosureDecision(
            granted=False,
            categories=frozenset(),
            scope=scope,
            purpose=purpose,
            reasons=(
                (
                    "El hallazgo aún no está verificado por un respondiente acreditado. "
                    "Una noticia de hallazgo sin confirmar hace más daño que la espera "
                    "(principio de veracidad, Ley 1581 art. 4 lit. d)."
                ),
            ),
        )

    if (
        record.subject.is_minor
        and scope is DisclosureScope.FAMILY
        and record.consent.legal_basis not in BASES_FOR_MINOR_FAMILY_DISCLOSURE
        and record.verification is not VerificationLevel.AUTHORITY_VERIFIED
    ):
        return DisclosureDecision(
            granted=False,
            categories=frozenset(),
            scope=scope,
            purpose=purpose,
            reasons=(
                (
                    "Se trata de un NNA: entregar su ubicación a quien dice ser familia "
                    "exige autorización del representante legal o que el hallazgo lo "
                    "respalde la autoridad. Entregarlo a la persona equivocada es "
                    "precisamente el riesgo que el art. 7 busca evitar "
                    "(Ley 1581 art. 7 y Sent. C-748/2011)."
                ),
            ),
        )

    present = record.categories_present()
    allowed = SCOPE_CEILING[scope] & record.consent.categories & present

    if purpose is Purpose.ANONYMIZED_STATISTICS:
        allowed = frozenset()
        reasons.append(
            "Finalidad estadística: se responde sin datos que identifiquen al Titular "
            "(Ley 1581 art. 6 lit. e)."
        )
    elif DataCategory.MINOR in present:
        # El marcador de NNA viaja siempre que haya divulgación. No es un dato que se
        # entregue "de más": es lo que le dice a quien recibe la ficha que está
        # tratando con un menor y que debe extremar el cuidado. Ocultarlo por
        # minimización protegería el dato y desprotegería a la persona.
        allowed = allowed | {DataCategory.MINOR}

    withheld = present - allowed
    if withheld:
        reasons.append(
            "No se entregan las categorías "
            + ", ".join(sorted(c.value for c in withheld))
            + " por minimización (Ley 1581 art. 4 lit. f)."
        )

    return DisclosureDecision(
        granted=True,
        categories=allowed,
        withheld=withheld,
        scope=scope,
        purpose=purpose,
        reasons=tuple(reasons),
    )


def project(record: FoundPersonRecord, decision: DisclosureDecision) -> DisclosureView:
    """Construye la vista minimizada. No consulta permisos: confía en `decision`.

    Separar decidir de proyectar es intencional — así el test de política no
    necesita construir vistas, y el test de proyección no necesita razonar sobre la
    ley. Y no hay forma de proyectar de más: solo se copia lo que `decision` lista.
    """
    if not decision.granted:
        raise ValueError("No se proyecta un registro cuya divulgación fue negada.")

    cats = decision.categories
    view = DisclosureView(
        record_id=record.id,
        incident_id=record.incident_id,
        status=record.status,
        verification=record.verification,
        found_at=record.found_at,
        updated_at=record.updated_at,
        version=record.version,
        scope=decision.scope,
        categories=cats,
        is_minor=record.subject.is_minor,
        withheld=tuple(
            sorted(c.value for c in record.categories_present() - cats)
        ),
    )

    updates: dict[str, object] = {}

    if DataCategory.IDENTITY in cats:
        updates["display_name"] = record.subject.full_name
        updates["initials"] = (
            display_initials(record.subject.full_name)
            if record.subject.full_name
            else None
        )
        if decision.scope in (DisclosureScope.RESPONDER, DisclosureScope.AUTHORITY):
            updates["document_type"] = record.subject.document_type
            updates["document_number"] = record.subject.document_number
    elif record.subject.full_name:
        # Sin categoría de identidad la familia todavía puede reconocer una
        # coincidencia por iniciales, sin que el servicio publique el nombre.
        updates["initials"] = display_initials(record.subject.full_name)

    if DataCategory.PLACEMENT in cats and record.placement is not None:
        placement = record.placement
        if decision.scope is DisclosureScope.FAMILY:
            placement = placement.coarse()
        updates["site_name"] = placement.site_name or None
        updates["site_type"] = placement.site_type
        updates["municipality"] = placement.municipality
        updates["address"] = placement.address
        updates["lat"] = placement.lat
        updates["lon"] = placement.lon

    if DataCategory.CONTACT in cats and record.contacts:
        updates["contacts"] = tuple(
            {"kind": c.kind, "value": c.value, "belongs_to": c.belongs_to}
            for c in record.contacts
        )

    if DataCategory.HEALTH_RELATED in cats:
        updates["care_notes"] = record.care_notes

    if DataCategory.BIOMETRIC in cats:
        updates["biometric_ref"] = record.biometric_ref

    from dataclasses import replace

    return replace(view, **updates)  # type: ignore[arg-type]


def default_retention_deadline(now_ms: int) -> int:
    """Vencimiento operativo por defecto para un registro creado ahora."""
    return now_ms + DEFAULT_RETENTION_MS


def capsule_expiry(scope: DisclosureScope, now_ms: int) -> int:
    """Hasta cuándo puede vivir en un teléfono ajeno lo que se divulga por malla."""
    return now_ms + CAPSULE_TTL_MS[scope]
