"""La entidad central: el registro de una persona localizada.

Un `FoundPersonRecord` no es una ficha de una persona. Es la afirmación, hecha por
alguien concreto en un momento concreto, de que una persona reportada como no
localizada fue ubicada — con la base legal que habilita conservar esa afirmación.

Dueño: Miguel.
"""

from __future__ import annotations

import hashlib
import hmac
import re
import unicodedata
from dataclasses import dataclass, field, replace

from found_persons.domain.habeas_data import (
    BASES_ALLOWING_SENSITIVE_DATA,
    EXCEPTIONAL_BASES,
    Consent,
    Controller,
    DataCategory,
    DisclosureScope,
    Retention,
)
from found_persons.domain.vocabulary import (
    HEALTH_REVEALING_STATUSES,
    RecordLifecycle,
    SituationStatus,
    VerificationLevel,
)

_WHITESPACE = re.compile(r"\s+")


def normalize_document(document_type: str, document_number: str) -> str:
    """Forma canónica del documento, para que dos capturas del mismo documento coincidan.

    En campo el mismo documento se digita de diez maneras: con puntos, con espacios,
    con `CC` o `cc`. Sin normalizar, el token ciego de abajo no serviría de nada.
    """
    doc_type = _WHITESPACE.sub("", document_type).upper()
    digits = re.sub(r"[^0-9A-Za-z]", "", document_number).upper()
    return f"{doc_type}:{digits}"


def blinded_lookup_token(
    *, incident_key: bytes, document_type: str, document_number: str
) -> str:
    """Token ciego de búsqueda: `HMAC-SHA256(clave_del_incidente, documento)`.

    Es la pieza que hace que la búsqueda entre dispositivos sea compatible con el
    principio de acceso restringido (art. 4 lit. f). Un dispositivo solo puede
    preguntar por alguien **cuyo documento ya conoce**: no puede recorrer la base ni
    pescar nombres. Y la clave es por incidente, así que el token no sirve para
    correlacionar a la misma persona entre dos desastres distintos.

    La clave del incidente no vive en los teléfonos completa: se entrega derivada al
    respondiente acreditado, igual que la clave de sesión del beacon.
    """
    material = normalize_document(document_type, document_number).encode("utf-8")
    return hmac.new(incident_key, material, hashlib.sha256).hexdigest()[:32]


def _strip_accents(value: str) -> str:
    decomposed = unicodedata.normalize("NFD", value)
    return "".join(ch for ch in decomposed if unicodedata.category(ch) != "Mn")


def display_initials(full_name: str) -> str:
    """Iniciales para el ámbito familiar cuando el nombre completo no está consentido.

    `"María Fernanda Rojas Peña"` → `"M.F.R.P."`. Permite a una familia reconocer una
    coincidencia probable sin que el servicio publique el nombre de nadie.
    """
    parts = [p for p in _WHITESPACE.split(_strip_accents(full_name).strip()) if p]
    return "".join(f"{p[0].upper()}." for p in parts)


@dataclass(frozen=True, slots=True)
class PersonReference:
    """Identificación del Titular. Es el bloque con más PII de todo el registro."""

    lookup_token: str
    """Token ciego. Es la clave de búsqueda; el documento en claro es opcional."""

    full_name: str | None = None
    document_type: str | None = None
    document_number: str | None = None
    approximate_age: int | None = None
    is_minor: bool = False
    """Art. 7: si es NNA, prevalece su interés superior sobre la conveniencia operativa."""

    def redacted(self) -> PersonReference:
        """Todo fuera salvo el token. Lo que queda tras ejercer la supresión."""
        return PersonReference(lookup_token=self.lookup_token, is_minor=self.is_minor)


@dataclass(frozen=True, slots=True)
class Placement:
    """Dónde está la persona ahora. Dato factual reportado, no estimación RF."""

    site_name: str
    """`Albergue Colegio San José`, `Punto de encuentro Calle 45`."""

    site_type: str
    """`assembly_point`, `shelter`, `care_facility`, `field_position`, `home`."""

    municipality: str
    """Municipio. Es la granularidad más gruesa que sigue siendo útil a la familia."""

    address: str | None = None
    lat: float | None = None
    lon: float | None = None

    @property
    def reveals_health(self) -> bool:
        """Estar en un centro asistencial es, en sí mismo, un dato de salud."""
        return self.site_type == "care_facility"

    def coarse(self) -> Placement:
        """Solo municipio y tipo de sitio: lo que se le puede dar a la familia
        cuando la ubicación precisa no está consentida."""
        return Placement(
            site_name="",
            site_type=self.site_type,
            municipality=self.municipality,
        )


@dataclass(frozen=True, slots=True)
class ContactChannel:
    """Cómo alcanzar a la persona o a quien la reportó."""

    kind: str
    """`phone`, `email`, `radio`, `responder_relay`."""
    value: str
    belongs_to: str
    """`subject` | `next_of_kin` | `responder`."""


@dataclass(frozen=True, slots=True)
class FoundPersonRecord:
    """Registro de persona localizada, con su base legal incorporada.

    Invariante central: no existe un registro sin `consent`. El constructor de la
    capa de aplicación llama a `validate()` antes de persistir, y `validate()` es la
    puerta por la que no pasa un dato sensible sin causal del art. 6.
    """

    id: str
    incident_id: str
    subject: PersonReference
    status: SituationStatus
    verification: VerificationLevel
    reported_by: str
    """Actor que afirma el hallazgo. Es quien responde por su veracidad (art. 4 lit. d)."""
    found_at: int
    """Epoch ms del hallazgo, no del registro."""
    created_at: int
    updated_at: int
    consent: Consent
    controller: Controller
    retention: Retention
    placement: Placement | None = None
    contacts: tuple[ContactChannel, ...] = ()
    care_notes: str | None = None
    """Necesidades de atención en lenguaje llano. Dato sensible de salud (art. 5).

    NUNCA una valoración clínica: este servicio no evalúa a nadie (`docs/glossary.md`).
    Sirve para que quien reciba a la persona sepa qué hace falta: "requiere agua",
    "no puede caminar sin apoyo", "usa audífono".
    """
    biometric_ref: str | None = None
    """URI de la fotografía de reconocimiento. Dato sensible (art. 5)."""
    lifecycle: RecordLifecycle = RecordLifecycle.ACTIVE
    erased_at: int | None = None
    version: int = 1
    """Se incrementa en cada rectificación. Va en la cápsula para que un dispositivo
    con una copia vieja sepa que la suya quedó obsoleta."""
    notes: str = ""

    # ------------------------------------------------------------------ #
    # Clasificación                                                       #
    # ------------------------------------------------------------------ #

    def categories_present(self) -> frozenset[DataCategory]:
        """Qué categorías de dato contiene realmente este registro.

        Se calcula, no se declara: si alguien mete a la persona en un centro
        asistencial, el registro pasa a tener categoría de salud aunque el
        formulario no lo dijera.
        """
        present: set[DataCategory] = set()
        if self.subject.full_name or self.subject.document_number:
            present.add(DataCategory.IDENTITY)
        if self.contacts:
            present.add(DataCategory.CONTACT)
        if self.placement is not None:
            present.add(DataCategory.PLACEMENT)
        if (
            self.care_notes
            or self.status in HEALTH_REVEALING_STATUSES
            or (self.placement is not None and self.placement.reveals_health)
        ):
            present.add(DataCategory.HEALTH_RELATED)
        if self.biometric_ref:
            present.add(DataCategory.BIOMETRIC)
        if self.subject.is_minor:
            present.add(DataCategory.MINOR)
        return frozenset(present)

    def has_sensitive_data(self) -> bool:
        return any(c.is_sensitive for c in self.categories_present())

    # ------------------------------------------------------------------ #
    # Invariantes legales                                                 #
    # ------------------------------------------------------------------ #

    def validate(self) -> list[str]:
        """Violaciones del régimen de protección de datos. Vacío = se puede persistir."""
        problems: list[str] = []
        basis = self.consent.legal_basis

        if not self.consent.purposes:
            problems.append(
                "El registro no declara ninguna finalidad (Ley 1581 art. 4 lit. b)."
            )
        if not self.consent.scopes:
            problems.append(
                "El registro no declara ningún ámbito de divulgación (ADR-0007)."
            )

        present = self.categories_present()
        # `MINOR` queda fuera del contraste: es un marcador protector derivado de la
        # edad, no una categoría que el Titular conceda o niegue. Exigir que se
        # "autorice" ser menor de edad sería absurdo, y en campo se traduciría en un
        # 422 justo cuando se registra a un niño.
        undeclared = present - self.consent.categories - {DataCategory.MINOR}
        if undeclared:
            problems.append(
                "El registro contiene categorías no autorizadas: "
                + ", ".join(sorted(c.value for c in undeclared))
                + " (Ley 1581 art. 4 lit. b y f)."
            )

        if self.has_sensitive_data() and basis not in BASES_ALLOWING_SENSITIVE_DATA:
            problems.append(
                f"La base legal '{basis.value}' no habilita datos sensibles; "
                "el art. 6 solo admite autorización explícita, representante legal, "
                "interés vital del Titular incapacitado o urgencia sanitaria."
            )

        if basis in EXCEPTIONAL_BASES and not self.consent.proof.justification.strip():
            problems.append(
                f"La causal excepcional '{basis.value}' exige justificación escrita "
                "(Ley 1581 art. 10; deber de demostrar el Tratamiento, art. 17)."
            )

        if basis in EXCEPTIONAL_BASES and self.consent.expires_at is None:
            problems.append(
                f"La causal excepcional '{basis.value}' debe tener caducidad: una "
                "excepción sin fecha de vencimiento se convierte en regla."
            )

        if DisclosureScope.PUBLIC in self.consent.scopes and present - {
            DataCategory.MINOR
        }:
            problems.append(
                "Ningún registro con PII se divulga en el ámbito público (ADR-0007)."
            )

        if self.subject.is_minor and DisclosureScope.PUBLIC in self.consent.scopes:
            problems.append(
                "Datos de un NNA nunca van al ámbito público (Ley 1581 art. 7)."
            )

        if self.retention.legal_hold and not (
            self.retention.legal_hold_reason or ""
        ).strip():
            problems.append(
                "Una retención legal sin motivo no es oponible al Titular "
                "(Decreto 1074 art. 2.2.2.25.2.5)."
            )

        if self.found_at > self.created_at:
            problems.append("El hallazgo no puede ser posterior a su registro.")

        return problems

    # ------------------------------------------------------------------ #
    # Transiciones                                                        #
    # ------------------------------------------------------------------ #

    def erased(self, *, at_ms: int) -> FoundPersonRecord:
        """Supresión efectiva: se va la PII, queda el esqueleto auditable.

        Se conserva el `id`, el incidente y las marcas de tiempo porque el propio
        `audit_log` tiene que seguir refiriéndose a algo, y porque el conteo agregado
        del incidente no puede alterarse retroactivamente. Nada de eso identifica a
        nadie una vez que el token, el nombre y el documento desaparecen.
        """
        return replace(
            self,
            subject=self.subject.redacted(),
            placement=None,
            contacts=(),
            care_notes=None,
            biometric_ref=None,
            notes="",
            lifecycle=RecordLifecycle.ERASED,
            erased_at=at_ms,
            updated_at=at_ms,
            version=self.version + 1,
        )

    def anonymized(self, *, at_ms: int) -> FoundPersonRecord:
        """Venció la retención: sobrevive el hecho estadístico, no la persona."""
        return replace(
            self.erased(at_ms=at_ms),
            subject=PersonReference(lookup_token=""),
            lifecycle=RecordLifecycle.ANONYMIZED,
        )

    @property
    def is_readable(self) -> bool:
        return self.lifecycle is RecordLifecycle.ACTIVE


@dataclass(frozen=True, slots=True)
class RecordQuery:
    """Filtros de listado. Sin filtro por nombre: se busca por token, nunca por texto."""

    incident_id: str | None = None
    status: SituationStatus | None = None
    lookup_token: str | None = None
    updated_since: int | None = None
    include_erased: bool = False
    limit: int = 50
    offset: int = 0


@dataclass(frozen=True, slots=True)
class Claim:
    """Consulta o reclamo del Titular (Ley 1581 art. 14 y 15).

    Los plazos son legales, no de servicio: consulta 10 días hábiles prorrogables 5;
    reclamo 15 días hábiles prorrogables 8. Incumplirlos es la causa más común de
    sanción de la SIC, así que el plazo se calcula y se guarda al radicar.
    """

    id: str
    record_id: str | None
    kind: str
    """`query` (art. 14) | `claim` (art. 15)."""
    channel: str
    filed_by: str
    filed_at: int
    due_at: int
    """Vencimiento del plazo legal, en epoch ms."""
    subject_matter: str
    """`access`, `update`, `rectification`, `erasure`, `revocation`, `proof_of_consent`."""
    body: str
    status: str = "open"
    """`open` | `extended` | `answered` | `rejected`."""
    extended_until: int | None = None
    resolution: str | None = None
    resolved_at: int | None = None
    fields_to_correct: tuple[str, ...] = field(default_factory=tuple)
