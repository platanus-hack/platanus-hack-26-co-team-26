"""Modelo de habeas data — Constitución art. 15, Ley 1581 de 2012, Decreto 1074 de 2015.

Este módulo es la parte del dominio que hace que el resto sea legal. Todo lo que
aquí se declara es exigible: no hay registro sin base legal, no hay divulgación sin
ámbito, y no hay dato sensible sin una causal del art. 6.

Glosario legal → código:

| Ley 1581           | Aquí                                    |
|--------------------|-----------------------------------------|
| Titular            | `FoundPersonRecord.subject`             |
| Responsable        | operador del incidente (`Controller`)   |
| Encargado          | este servicio                           |
| Autorización       | `Consent`                               |
| Finalidad          | `Purpose`                               |
| Dato sensible      | `DataCategory.is_sensitive`             |
| Supresión          | `RecordLifecycle.ERASED` + `Tombstone`  |

Dueño: Miguel. Revisor obligatorio: Helmut (cifrado break-glass del ámbito familiar).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum


class LegalBasis(StrEnum):
    """Causal que habilita el Tratamiento. Todo registro declara exactamente una.

    La autorización del Titular es la regla (art. 9); las demás son excepciones
    tasadas y se interpretan de forma restrictiva. En un desastre la excepción es
    frecuente, pero sigue siendo excepción: hay que poder justificarla ante la SIC.
    """

    SUBJECT_CONSENT = "subject_consent"
    """Art. 9: autorización previa, expresa e informada del Titular."""

    LEGAL_GUARDIAN_CONSENT = "legal_guardian_consent"
    """Art. 6 par.: la otorga el representante legal cuando el Titular no puede."""

    VITAL_INTEREST_INCAPACITY = "vital_interest_incapacity"
    """Art. 6 lit. b: interés vital del Titular física o jurídicamente incapacitado.

    Única causal pensada para el caso central de este servicio: la persona está
    atrapada o inconsciente y no puede autorizar nada. Exige justificación escrita
    y caduca — ver `Consent.expires_at`.
    """

    HEALTH_EMERGENCY = "health_emergency"
    """Art. 10 lit. c: urgencia médica o sanitaria. No requiere autorización."""

    PUBLIC_AUTHORITY_DUTY = "public_authority_duty"
    """Art. 10 lit. a: entidad pública en ejercicio de sus funciones legales."""


#: Causales que, por el art. 6, sí habilitan tratar datos sensibles (salud,
#: biométricos). Cualquier otra combinación se rechaza en el dominio.
BASES_ALLOWING_SENSITIVE_DATA: frozenset[LegalBasis] = frozenset(
    {
        LegalBasis.SUBJECT_CONSENT,
        LegalBasis.LEGAL_GUARDIAN_CONSENT,
        LegalBasis.VITAL_INTEREST_INCAPACITY,
        LegalBasis.HEALTH_EMERGENCY,
    }
)

#: Causales que no nacen de una manifestación de voluntad del Titular. Son las que
#: exigen justificación escrita en el registro y revisión posterior.
EXCEPTIONAL_BASES: frozenset[LegalBasis] = frozenset(
    {
        LegalBasis.VITAL_INTEREST_INCAPACITY,
        LegalBasis.HEALTH_EMERGENCY,
        LegalBasis.PUBLIC_AUTHORITY_DUTY,
    }
)


class Purpose(StrEnum):
    """Finalidad del Tratamiento (art. 4 lit. b, principio de finalidad).

    El dato recogido para reunificar familias no se puede reutilizar para otra cosa.
    Cada consulta declara su finalidad y el dominio la contrasta contra las
    autorizadas en el registro.
    """

    FAMILY_REUNIFICATION = "family_reunification"
    RESPONSE_COORDINATION = "response_coordination"
    AUTHORITY_NOTIFICATION = "authority_notification"
    ANONYMIZED_STATISTICS = "anonymized_statistics"


class DataCategory(StrEnum):
    """Categorías de dato del registro, para minimizar por ámbito (art. 4 lit. f)."""

    IDENTITY = "identity"
    """Nombre y documento."""

    CONTACT = "contact"
    """Teléfono, correo, contacto de la familia."""

    PLACEMENT = "placement"
    """Dónde está la persona ahora: albergue, punto de encuentro, dirección."""

    HEALTH_RELATED = "health_related"
    """Sensible (art. 5): centro asistencial, necesidades de atención, traslado."""

    BIOMETRIC = "biometric"
    """Sensible (art. 5): fotografía de reconocimiento, rasgos, huella."""

    MINOR = "minor"
    """Art. 7 + Sent. C-748/2011: prevalece el interés superior del NNA."""

    @property
    def is_sensitive(self) -> bool:
        """Dato sensible en los términos del art. 5."""
        return self in _SENSITIVE_CATEGORIES


_SENSITIVE_CATEGORIES: frozenset[DataCategory] = frozenset(
    {DataCategory.HEALTH_RELATED, DataCategory.BIOMETRIC}
)


class DisclosureScope(StrEnum):
    """Nivel de exposición. Espeja ADR-0007 (tres vistas) y le suma AUTHORITY.

    El orden importa: `PUBLIC < FAMILY < RESPONDER < AUTHORITY`. Un principal nunca
    recibe más de lo que su ámbito permite, aunque el registro tenga más.
    """

    PUBLIC = "public"
    """Cero PII. Solo conteos y la existencia de novedad. Sin autenticación."""

    FAMILY = "family"
    """Vínculo familiar verificado y consentido por el Titular."""

    RESPONDER = "responder"
    """Respondiente acreditado por la autoridad del incidente."""

    AUTHORITY = "authority"
    """Entidad pública en ejercicio de funciones legales (art. 10 lit. a)."""


_SCOPE_ORDER: dict[DisclosureScope, int] = {
    DisclosureScope.PUBLIC: 0,
    DisclosureScope.FAMILY: 1,
    DisclosureScope.RESPONDER: 2,
    DisclosureScope.AUTHORITY: 3,
}


def scope_covers(granted: DisclosureScope, required: DisclosureScope) -> bool:
    """`True` si un principal con ámbito `granted` alcanza a `required`."""
    return _SCOPE_ORDER[granted] >= _SCOPE_ORDER[required]


@dataclass(frozen=True, slots=True)
class ConsentProof:
    """Prueba de la autorización — el Titular puede exigirla (art. 8 lit. b).

    No guardamos el documento firmado aquí: guardamos su huella y dónde está, para
    no duplicar PII en una base que se replica por malla.
    """

    channel: str
    """`app`, `verbal_responder`, `paper_form`, `authority_act`."""

    captured_at: int
    """Epoch ms en que se recogió la autorización o se invocó la excepción."""

    captured_by: str
    """Actor que la recogió. Para las causales del art. 10 es quien las invoca."""

    evidence_sha256: str | None = None
    """Huella del soporte (audio, PDF, acta). `None` para causales sin soporte."""

    evidence_uri: str | None = None
    """Dónde vive ese soporte (MinIO/S3). Nunca el contenido."""

    justification: str = ""
    """Obligatoria para `EXCEPTIONAL_BASES`. Es lo que se le muestra a la SIC."""


@dataclass(frozen=True, slots=True)
class Consent:
    """Autorización vigente sobre un registro (art. 9), granular y revocable.

    Granular porque el modelo de amenazas lo exige: ubicación, salud y compartición
    familiar se consienten por separado y se revocan por separado.
    """

    legal_basis: LegalBasis
    purposes: frozenset[Purpose]
    categories: frozenset[DataCategory]
    """Categorías que el Titular (o la causal) habilita a tratar."""
    scopes: frozenset[DisclosureScope]
    """Ámbitos a los que se puede divulgar. `PUBLIC` casi nunca está aquí."""
    proof: ConsentProof
    expires_at: int | None = None
    """Caducidad de la causal. Las excepcionales siempre deberían tenerla."""
    revoked_at: int | None = None
    """Revocación (art. 8 lit. e). Una vez puesto, no se vuelve a quitar."""
    revocation_reason: str | None = None

    def is_active(self, now_ms: int) -> bool:
        """Vigente: ni revocada ni caducada."""
        if self.revoked_at is not None and self.revoked_at <= now_ms:
            return False
        return not (self.expires_at is not None and self.expires_at <= now_ms)

    def allows(
        self, *, purpose: Purpose, scope: DisclosureScope, now_ms: int
    ) -> bool:
        """`True` si esta autorización cubre esa finalidad en ese ámbito."""
        return (
            self.is_active(now_ms)
            and purpose in self.purposes
            and scope in self.scopes
        )

    def revoked(self, *, at_ms: int, reason: str) -> Consent:
        """Copia revocada. El dominio es inmutable; revocar produce otro objeto."""
        from dataclasses import replace

        return replace(self, revoked_at=at_ms, revocation_reason=reason)


@dataclass(frozen=True, slots=True)
class Controller:
    """Responsable del Tratamiento — hay que poder nombrarlo (art. 17 lit. a y art. 12).

    Es el dato que el aviso de privacidad debe exponer y ante quien el Titular
    ejerce sus derechos. Sin esto, el registro no cumple el deber de informar.
    """

    name: str
    legal_id: str
    """NIT o identificación de la entidad responsable del incidente."""
    contact_email: str
    rnbd_registration: str | None = None
    """Radicado del Registro Nacional de Bases de Datos (art. 25), si aplica."""
    privacy_notice_version: str = "1.0"


@dataclass(frozen=True, slots=True)
class Retention:
    """Temporalidad del dato (art. 4 lit. c y d; Decreto 1074 art. 2.2.2.25.2.9).

    El dato operativo caduca; después solo sobrevive el agregado anonimizado. El
    modelo de amenazas fija 30 días operativos como referencia por defecto.
    """

    erase_after_ms: int
    """Epoch ms tras el cual el registro se anonimiza de forma irreversible."""

    legal_hold: bool = False
    """Retención legal: bloquea la supresión mientras esté activa."""

    legal_hold_reason: str | None = None
    """Obligatoria si `legal_hold`. Es la respuesta que recibe el Titular."""

    def blocks_erasure(self) -> bool:
        """La supresión no procede si hay deber legal de conservar.

        Decreto 1074 art. 2.2.2.25.2.5: la supresión no aplica cuando el Titular
        tiene un deber legal o contractual de permanecer en la base, o cuando
        eliminar el dato obstruye una actuación judicial o administrativa.
        """
        return self.legal_hold

    def expired(self, now_ms: int) -> bool:
        return now_ms >= self.erase_after_ms


@dataclass(frozen=True, slots=True)
class AuditEntry:
    """Asiento de `audit_log`. Se escribe ANTES de responder (§12.3 y ADR-0007).

    Cumple dos cosas a la vez: el deber del Responsable de llevar trazabilidad
    (art. 17) y el derecho del Titular a saber quién usó su dato (art. 4 lit. e).
    """

    id: str
    occurred_at: int
    actor: str
    """Quién consultó: `user:...`, `device:...`, `service:...`."""
    actor_scope: DisclosureScope
    subject_ref: str
    """Referencia al Titular. Nunca el nombre: el id del registro."""
    action: str
    """`create`, `read`, `list`, `update`, `erase`, `mesh_disclose`, `revoke`, ..."""
    purpose: Purpose
    justification: str
    legal_basis: LegalBasis
    categories_disclosed: frozenset[DataCategory] = field(default_factory=frozenset)
    outcome: str = "granted"
    """`granted` | `denied` | `partial`. Los `denied` también se auditan."""
    channel: str = "http"
    """`http` para la API, `mesh` para divulgación entre dispositivos."""


class TombstoneReason(StrEnum):
    """Motivos por los que una lápida puede existir. Enum cerrado a propósito.

    La lápida viaja por la malla y la leen dispositivos que no son de confianza. Si
    el motivo fuera texto libre, tarde o temprano alguien escribiría ahí el nombre de
    la persona o el porqué de su solicitud, y estaríamos propagando por la red
    exactamente el dato que la supresión pretendía eliminar. El texto libre que sí
    aporta contexto vive en `audit_log`, que no sale del servidor.
    """

    ERASURE_REQUESTED = "erasure_requested"
    """Ley 1581 art. 8 lit. e — el Titular pidió la supresión."""
    CONSENT_REVOKED = "consent_revoked"
    """Ley 1581 art. 8 lit. e — revocó la autorización."""
    RETENTION_EXPIRED = "retention_expired"
    """Ley 1581 art. 4 lit. c — venció la retención operativa."""
    RECTIFIED = "rectified"
    """Ley 1581 art. 8 lit. a — el dato cambió; las copias quedaron obsoletas."""


@dataclass(frozen=True, slots=True)
class Tombstone:
    """Lápida de supresión, propagable por la malla.

    Sin esto, la supresión sería mentira: el dato ya viajó a teléfonos que pueden
    estar sin conectividad. La lápida es lo único que puede alcanzarlos y decirles
    que borren. Va firmada para que un relay no pueda fabricarla ni suprimirla.
    """

    record_id: str
    incident_id: str
    issued_at: int
    reason: TombstoneReason
    """Motivo, del enum cerrado. Nunca texto libre: esto se propaga por la malla."""
    sequence: int
    """Monótono por incidente. Permite a un dispositivo pedir solo lo nuevo."""
    signature: str = ""
    """Ed25519 del servicio sobre la forma canónica. Se rellena al emitir."""
