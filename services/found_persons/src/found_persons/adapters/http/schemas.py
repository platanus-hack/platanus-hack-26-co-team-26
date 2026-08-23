"""DTOs de entrada y salida. Pydantic no baja del adaptador HTTP.

Los DTO no son las entidades: el registro del dominio tiene `lookup_token`, y el
DTO de salida no, porque quien recibe la respuesta no debe poder reconstruir el
token de otra persona. Esa asimetría es la razón de que estas clases existan en vez
de serializar las dataclasses directamente.
"""

from __future__ import annotations

from typing import Annotated, Any

from pydantic import BaseModel, ConfigDict, Field

from found_persons.domain.habeas_data import (
    DataCategory,
    DisclosureScope,
    LegalBasis,
    Purpose,
    TombstoneReason,
)
from found_persons.domain.vocabulary import SituationStatus, VerificationLevel

Justification = Annotated[
    str,
    Field(
        min_length=10,
        max_length=500,
        description=(
            "Por qué se accede. Se guarda literal en audit_log y el Titular puede "
            "leerla (Ley 1581 art. 4 lit. e). Diez caracteres es el mínimo para que "
            "no se rellene con un punto."
        ),
    ),
]


class Base(BaseModel):
    model_config = ConfigDict(extra="forbid")
    """`extra=forbid`: un campo mal escrito en una petición que trae datos personales
    debe fallar, no ignorarse en silencio."""


# --------------------------------------------------------------------------- #
# Habeas data                                                                  #
# --------------------------------------------------------------------------- #


class ConsentProofIn(Base):
    channel: str = Field(
        description="app | verbal_responder | paper_form | authority_act"
    )
    captured_by: str
    captured_at: int | None = Field(
        default=None, description="Epoch ms. Si se omite, se usa el momento actual."
    )
    evidence_sha256: str | None = None
    evidence_uri: str | None = None
    justification: str = Field(
        default="",
        description=(
            "Obligatoria para las causales excepcionales (interés vital, urgencia "
            "sanitaria, función legal). Es lo que se le muestra a la SIC."
        ),
    )


class ConsentIn(Base):
    legal_basis: LegalBasis
    purposes: list[Purpose] = Field(min_length=1)
    categories: list[DataCategory] = Field(min_length=1)
    scopes: list[DisclosureScope] = Field(min_length=1)
    proof: ConsentProofIn
    expires_at: int | None = Field(
        default=None,
        description="Caducidad de la causal. Obligatoria si es excepcional.",
    )


class ControllerIn(Base):
    name: str
    legal_id: str
    contact_email: str
    rnbd_registration: str | None = None
    privacy_notice_version: str = "1.0"


class RetentionIn(Base):
    erase_after_ms: int | None = Field(
        default=None, description="Si se omite, 30 días desde la creación."
    )
    legal_hold: bool = False
    legal_hold_reason: str | None = None


# --------------------------------------------------------------------------- #
# Registro                                                                     #
# --------------------------------------------------------------------------- #


class PlacementIn(Base):
    site_name: str
    site_type: str = Field(
        description="assembly_point | shelter | care_facility | field_position | home"
    )
    municipality: str
    address: str | None = None
    lat: float | None = Field(default=None, ge=-90, le=90)
    lon: float | None = Field(default=None, ge=-180, le=180)


class ContactIn(Base):
    kind: str = Field(description="phone | email | radio | responder_relay")
    value: str
    belongs_to: str = Field(description="subject | next_of_kin | responder")


class RecordIn(Base):
    """Cuerpo de POST y de PUT. La misma forma: un PUT es un reemplazo completo."""

    incident_id: str
    document_type: str = Field(description="CC | TI | CE | PPT | PA | NUIP | SIN_DOC")
    document_number: str
    status: SituationStatus
    verification: VerificationLevel
    found_at: int = Field(description="Epoch ms del hallazgo, no del registro.")
    consent: ConsentIn
    controller: ControllerIn
    full_name: str | None = None
    approximate_age: int | None = Field(default=None, ge=0, le=130)
    is_minor: bool = False
    placement: PlacementIn | None = None
    contacts: list[ContactIn] = Field(default_factory=list)
    care_notes: str | None = Field(
        default=None,
        description=(
            "Necesidades de atención en lenguaje llano ('requiere agua', 'no puede "
            "caminar sin apoyo'). Dato sensible de salud. Este servicio no evalúa "
            "clínicamente a nadie — ver docs/glossary.md."
        ),
    )
    biometric_ref: str | None = Field(
        default=None, description="URI de la fotografía de reconocimiento. Dato sensible."
    )
    retention: RetentionIn | None = None
    notes: str = ""


class RecordOut(Base):
    """Vista minimizada. Los campos ausentes lo están porque no correspondían."""

    record_id: str
    incident_id: str
    status: SituationStatus
    verification: VerificationLevel
    found_at: int
    updated_at: int
    version: int
    scope: DisclosureScope
    categories_disclosed: list[str]
    withheld_categories: list[str] = Field(
        default_factory=list,
        description=(
            "Categorías que el registro contiene y no se entregaron. Se declara para "
            "que el solicitante sepa que hay más y que no le corresponde."
        ),
    )
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
    contacts: list[dict[str, str]] = Field(default_factory=list)
    care_notes: str | None = None
    biometric_ref: str | None = None


class PageOut(Base):
    items: list[RecordOut]
    total: int
    limit: int
    offset: int
    withheld_records: int = Field(
        description="Cuántos registros de esta página ocultó la política."
    )


class CreatedOut(Base):
    record_id: str
    version: int
    lifecycle: str
    retention_until: int
    legal_basis: LegalBasis
    audit_notice: str = (
        "Este acceso quedó registrado en audit_log. El Titular puede consultarlo en "
        "GET /v1/hallazgos/{id}/accesos (Ley 1581 art. 4 lit. e)."
    )


class ErasedOut(Base):
    record_id: str
    lifecycle: str
    erased_at: int
    tombstone_emitted: bool
    notice: str


# --------------------------------------------------------------------------- #
# Malla                                                                        #
# --------------------------------------------------------------------------- #


class DeviceRegistrationIn(Base):
    device_id: str
    incident_id: str
    signing_public_key: str = Field(description="Ed25519 en base64url sin relleno.")
    scope: DisclosureScope
    kex_public_key: str | None = Field(
        default=None,
        description=(
            "X25519 en base64url. Sin ella la cápsula viaja en claro y se prohíbe su "
            "reenvío por la malla."
        ),
    )
    organization: str | None = None
    holder_ref: str | None = None
    expires_at: int | None = None


class DeviceOut(Base):
    device_id: str
    incident_id: str
    scope: DisclosureScope
    organization: str | None
    accredited_by: str
    accredited_at: int
    expires_at: int | None
    revoked_at: int | None
    sealed_delivery: bool = Field(
        description="True si publicó clave X25519 y la cápsula viajará cifrada."
    )


class DeviceQueryIn(Base):
    """Consulta firmada por el dispositivo.

    La firma cubre la forma canónica de todos los campos menos ella misma. Un
    dispositivo que solo firmara el token podría ver su consulta reutilizada con
    otra finalidad por quien la interceptara.
    """

    device_id: str
    incident_id: str
    lookup_token: str = Field(
        min_length=32,
        max_length=32,
        description=(
            "HMAC-SHA256(clave_del_incidente, documento_normalizado), 32 hex. "
            "Se pregunta por quien ya se conoce: no hay búsqueda por nombre."
        ),
    )
    purpose: Purpose
    justification: Justification
    nonce: str = Field(min_length=8, max_length=64)
    issued_at: int
    expires_at: int
    signature: str = Field(description="Ed25519 en base64url sobre la forma canónica.")


class CapsuleOut(Base):
    capsule_id: str
    incident_id: str
    audience_device_id: str
    scope: DisclosureScope
    purpose: Purpose
    outcome: str = Field(description="granted | denied | not_found | erased | no_disclosure")
    issued_at: int
    expires_at: int
    payload: str
    payload_encrypted: bool
    record_id: str | None = None
    record_version: int | None = None
    reasons: list[str] = Field(default_factory=list)
    audit_id: str = ""
    max_hops: int
    retransmit_allowed: bool
    signature: str


class CapsuleVerifyIn(Base):
    capsule: CapsuleOut


class CapsuleVerdictOut(Base):
    signature_valid: bool
    fresh: bool
    superseded: bool
    must_delete: bool
    reasons: list[str]
    current_tombstone_sequence: int


class TombstoneOut(Base):
    record_id: str
    incident_id: str
    issued_at: int
    reason: TombstoneReason = Field(
        description=(
            "Motivo, de un enum cerrado. Nunca texto libre: la lápida se propaga por "
            "la malla y no puede transportar datos personales."
        )
    )
    sequence: int
    signature: str


class TombstonePageOut(Base):
    items: list[TombstoneOut]
    next_sequence: int
    service_public_key: str = Field(
        description="Clave Ed25519 del servicio, para verificar las lápidas sin conexión."
    )


# --------------------------------------------------------------------------- #
# Derechos del Titular                                                         #
# --------------------------------------------------------------------------- #


class AuditEntryOut(Base):
    id: str
    occurred_at: int
    actor: str
    actor_scope: DisclosureScope
    action: str
    purpose: Purpose
    justification: str
    legal_basis: LegalBasis
    categories_disclosed: list[str]
    outcome: str
    channel: str


class ConsentProofOut(Base):
    record_id: str
    legal_basis: LegalBasis
    legal_basis_explained: str
    granted_by: str
    granted_at: int
    channel: str
    purposes: list[str]
    categories: list[str]
    scopes: list[str]
    justification: str
    evidence_sha256: str | None
    evidence_uri: str | None
    expires_at: int | None
    revoked_at: int | None
    controller: dict[str, Any]


class RevocationIn(Base):
    reason: str = Field(
        min_length=5,
        description="Motivo de la revocación. Queda en audit_log, no en la lápida.",
    )


class ClaimIn(Base):
    kind: str = Field(description="query (consulta, art. 14) | claim (reclamo, art. 15)")
    subject_matter: str = Field(
        description="access | update | rectification | erasure | revocation | proof_of_consent"
    )
    body: str = Field(min_length=10)
    filed_by: str
    record_id: str | None = None
    channel: str = "web"


class ClaimOut(Base):
    id: str
    kind: str
    record_id: str | None
    subject_matter: str
    filed_by: str
    filed_at: int
    due_at: int
    due_at_explained: str
    status: str
    extended_until: int | None
    resolution: str | None
    resolved_at: int | None


class ErrorOut(Base):
    code: str
    message: str
    details: list[str] = Field(default_factory=list)
    legal_reference: str | None = None
