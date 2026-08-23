"""Casos de uso del ciclo de vida del registro: crear, leer, listar, rectificar, suprimir.

Cada uno de los cuatro verbos HTTP entra por aquí, y cada uno escribe en
`audit_log` **antes** de devolver nada (regla de PII §12.3 y ADR-0007). El orden no
es un detalle: si el proceso muere entre responder y auditar, queda una divulgación
sin rastro, que es exactamente lo que la trazabilidad debe impedir.

Dueño: Miguel.
"""

from __future__ import annotations

from dataclasses import dataclass, replace

from found_persons.application.context import AccessContext, Principal
from found_persons.application.ports import (
    AuditLog,
    Clock,
    IdGenerator,
    IncidentKeyProvider,
    RecordRepository,
    Signer,
    TombstoneStore,
)
from found_persons.domain.canonical import canonical_bytes
from found_persons.domain.errors import (
    DisclosureDenied,
    ErasureBlocked,
    HabeasDataViolation,
    RecordAlreadyExists,
    RecordErased,
    RecordNotFound,
)
from found_persons.domain.habeas_data import (
    AuditEntry,
    Consent,
    Controller,
    DataCategory,
    DisclosureScope,
    Retention,
    Tombstone,
    TombstoneReason,
)
from found_persons.domain.policies import (
    DisclosureView,
    decide,
    default_retention_deadline,
    project,
)
from found_persons.domain.records import (
    ContactChannel,
    FoundPersonRecord,
    PersonReference,
    Placement,
    RecordQuery,
    blinded_lookup_token,
)
from found_persons.domain.vocabulary import (
    RecordLifecycle,
    SituationStatus,
    VerificationLevel,
)


@dataclass(frozen=True, slots=True)
class NewRecordCommand:
    """Alta de un hallazgo. El documento llega en claro y sale convertido en token."""

    incident_id: str
    status: SituationStatus
    verification: VerificationLevel
    found_at: int
    consent: Consent
    controller: Controller
    document_type: str
    document_number: str
    full_name: str | None = None
    approximate_age: int | None = None
    is_minor: bool = False
    placement: Placement | None = None
    contacts: tuple[ContactChannel, ...] = ()
    care_notes: str | None = None
    biometric_ref: str | None = None
    retention: Retention | None = None
    notes: str = ""


@dataclass(frozen=True, slots=True)
class ReplaceRecordCommand:
    """Rectificación completa (art. 8 lit. a). Sustituye el contenido, no la historia.

    No se puede cambiar de incidente ni resucitar un registro suprimido: eso sería
    reescribir la trazabilidad, no rectificar un dato.
    """

    status: SituationStatus
    verification: VerificationLevel
    found_at: int
    consent: Consent
    controller: Controller
    document_type: str
    document_number: str
    full_name: str | None = None
    approximate_age: int | None = None
    is_minor: bool = False
    placement: Placement | None = None
    contacts: tuple[ContactChannel, ...] = ()
    care_notes: str | None = None
    biometric_ref: str | None = None
    retention: Retention | None = None
    notes: str = ""


@dataclass(frozen=True, slots=True)
class Page:
    items: list[DisclosureView]
    total: int
    limit: int
    offset: int
    withheld_records: int
    """Cuántos registros de la página se ocultaron por política. Se informa el número
    porque negar la existencia del recorte sería engañoso, y el conteo agregado no
    identifica a nadie."""


class RecordsService:
    """Los cuatro verbos, más el barrido de retención."""

    def __init__(
        self,
        *,
        repository: RecordRepository,
        audit: AuditLog,
        tombstones: TombstoneStore,
        clock: Clock,
        ids: IdGenerator,
        signer: Signer,
        incident_keys: IncidentKeyProvider,
    ) -> None:
        self._repo = repository
        self._audit = audit
        self._tombstones = tombstones
        self._clock = clock
        self._ids = ids
        self._signer = signer
        self._keys = incident_keys

    # ------------------------------------------------------------------ #
    # POST                                                                #
    # ------------------------------------------------------------------ #

    def create(
        self, command: NewRecordCommand, *, principal: Principal, context: AccessContext
    ) -> FoundPersonRecord:
        """Registra un hallazgo. Falla si el resultado no sería legal de conservar."""
        context.require_justification()
        now = self._clock.now_ms()

        token = blinded_lookup_token(
            incident_key=self._keys.key_for(command.incident_id),
            document_type=command.document_type,
            document_number=command.document_number,
        )

        existing = self._repo.find_by_lookup_token(command.incident_id, token)
        if existing is not None and existing.lifecycle is RecordLifecycle.ACTIVE:
            raise RecordAlreadyExists(
                "Ya existe un registro activo para esa persona en este incidente. "
                "Rectifíquelo con PUT en lugar de duplicarlo: dos registros divergentes "
                "de la misma persona rompen el principio de veracidad (art. 4 lit. d).",
                details=[existing.id],
            )

        record = FoundPersonRecord(
            id=self._ids.new_id("fpr"),
            incident_id=command.incident_id,
            subject=PersonReference(
                lookup_token=token,
                full_name=command.full_name,
                document_type=command.document_type,
                document_number=command.document_number,
                approximate_age=command.approximate_age,
                is_minor=command.is_minor,
            ),
            status=command.status,
            verification=command.verification,
            reported_by=principal.actor_id,
            found_at=command.found_at,
            created_at=now,
            updated_at=now,
            consent=command.consent,
            controller=command.controller,
            retention=command.retention
            or Retention(erase_after_ms=default_retention_deadline(now)),
            placement=command.placement,
            contacts=command.contacts,
            care_notes=command.care_notes,
            biometric_ref=command.biometric_ref,
            notes=command.notes,
        )

        self._enforce(record, principal=principal, context=context, action="create")
        self._audit_entry(
            record=record,
            principal=principal,
            context=context,
            action="create",
            categories=record.categories_present(),
            outcome="granted",
        )
        self._repo.save(record)
        return record

    # ------------------------------------------------------------------ #
    # GET                                                                 #
    # ------------------------------------------------------------------ #

    def get(
        self, record_id: str, *, principal: Principal, context: AccessContext
    ) -> DisclosureView:
        """Lectura minimizada. Audita también cuando niega."""
        context.require_justification()
        now = self._clock.now_ms()
        record = self._repo.get(record_id)
        if record is None:
            raise RecordNotFound(f"No existe el registro '{record_id}'.")

        decision = decide(
            record, scope=principal.scope, purpose=context.purpose, now_ms=now
        )
        self._audit_entry(
            record=record,
            principal=principal,
            context=context,
            action="read",
            categories=decision.categories,
            outcome=decision.outcome,
        )

        if not decision.granted:
            if record.lifecycle is RecordLifecycle.ERASED:
                raise RecordErased(
                    "El registro fue suprimido a petición del Titular.",
                    details=list(decision.reasons),
                )
            raise DisclosureDenied(
                "La divulgación no está habilitada para este solicitante.",
                details=list(decision.reasons),
            )
        return project(record, decision)

    def list(
        self, query: RecordQuery, *, principal: Principal, context: AccessContext
    ) -> Page:
        """Listado. Cada elemento pasa por la misma política que una lectura suelta.

        Un listado es la vía clásica por la que se escapa PII: se controla el detalle
        y se olvida la colección. Aquí no hay atajo — se evalúa registro por registro
        y lo denegado simplemente no aparece.
        """
        context.require_justification()
        now = self._clock.now_ms()
        records, total = self._repo.search(query)

        views: list[DisclosureView] = []
        withheld = 0
        disclosed: set[DataCategory] = set()

        for record in records:
            decision = decide(
                record, scope=principal.scope, purpose=context.purpose, now_ms=now
            )
            if not decision.granted:
                withheld += 1
                continue
            disclosed |= decision.categories
            views.append(project(record, decision))

        self._audit_entry(
            record=None,
            principal=principal,
            context=context,
            action="list",
            categories=frozenset(disclosed),
            outcome="partial" if withheld else "granted",
            subject_ref=f"incident:{query.incident_id or 'all'}",
            legal_basis_hint=records[0].consent.legal_basis if records else None,
        )

        return Page(
            items=views,
            total=total,
            limit=query.limit,
            offset=query.offset,
            withheld_records=withheld,
        )

    # ------------------------------------------------------------------ #
    # PUT                                                                 #
    # ------------------------------------------------------------------ #

    def replace(
        self,
        record_id: str,
        command: ReplaceRecordCommand,
        *,
        principal: Principal,
        context: AccessContext,
    ) -> FoundPersonRecord:
        """Rectificación completa. Sube `version` para invalidar copias en malla."""
        context.require_justification()
        now = self._clock.now_ms()
        current = self._repo.get(record_id)
        if current is None:
            raise RecordNotFound(f"No existe el registro '{record_id}'.")
        if current.lifecycle is not RecordLifecycle.ACTIVE:
            raise RecordErased(
                "Un registro suprimido o anonimizado no se rectifica: volver a "
                "poblarlo con datos personales desharía el derecho ya ejercido "
                "(Ley 1581 art. 8 lit. e)."
            )

        token = blinded_lookup_token(
            incident_key=self._keys.key_for(current.incident_id),
            document_type=command.document_type,
            document_number=command.document_number,
        )

        consent = command.consent
        if current.consent.revoked_at is not None:
            # Una revocación no se puede deshacer editando el registro. Si el Titular
            # quiere volver a autorizar, tiene que otorgar una autorización nueva.
            consent = replace(
                consent,
                revoked_at=current.consent.revoked_at,
                revocation_reason=current.consent.revocation_reason,
            )

        updated = replace(
            current,
            subject=PersonReference(
                lookup_token=token,
                full_name=command.full_name,
                document_type=command.document_type,
                document_number=command.document_number,
                approximate_age=command.approximate_age,
                is_minor=command.is_minor,
            ),
            status=command.status,
            verification=command.verification,
            found_at=command.found_at,
            consent=consent,
            controller=command.controller,
            retention=command.retention or current.retention,
            placement=command.placement,
            contacts=command.contacts,
            care_notes=command.care_notes,
            biometric_ref=command.biometric_ref,
            notes=command.notes,
            updated_at=now,
            version=current.version + 1,
        )

        self._enforce(updated, principal=principal, context=context, action="update")
        self._audit_entry(
            record=updated,
            principal=principal,
            context=context,
            action="update",
            categories=updated.categories_present(),
            outcome="granted",
        )
        self._repo.save(updated)

        # Los datos cambiaron: lo que ya viajó por la malla quedó desactualizado.
        self._emit_tombstone(updated, reason=TombstoneReason.RECTIFIED, now_ms=now)
        return updated

    # ------------------------------------------------------------------ #
    # DELETE                                                              #
    # ------------------------------------------------------------------ #

    def erase(
        self,
        record_id: str,
        *,
        principal: Principal,
        context: AccessContext,
        reason: str = "",
    ) -> FoundPersonRecord:
        """Supresión (art. 8 lit. e).

        No es un `DELETE FROM`. Se redacta la PII y se conserva un esqueleto sin
        datos personales, porque el `audit_log` tiene que seguir apuntando a algo y
        porque el conteo del incidente no puede cambiar retroactivamente. Y se emite
        una lápida: sin ella, las copias que ya viajaron por la malla sobrevivirían
        al derecho ejercido, y la supresión sería una ficción.

        `reason` es texto libre y se queda en `audit_log`. La lápida lleva únicamente
        `TombstoneReason.ERASURE_REQUESTED`: se propaga por la malla y no puede
        transportar lo que alguien escriba en un campo abierto.
        """
        context.require_justification()
        now = self._clock.now_ms()
        record = self._repo.get(record_id)
        if record is None:
            raise RecordNotFound(f"No existe el registro '{record_id}'.")
        if record.lifecycle is RecordLifecycle.ERASED:
            return record

        if record.retention.blocks_erasure():
            self._audit_entry(
                record=record,
                principal=principal,
                context=context,
                action="erase",
                categories=frozenset(),
                outcome="denied",
            )
            raise ErasureBlocked(
                "La supresión no procede mientras exista retención legal.",
                details=[
                    record.retention.legal_hold_reason or "",
                    (
                        "Decreto 1074 art. 2.2.2.25.2.5: la supresión no aplica cuando "
                        "eliminar el dato obstruye una actuación judicial o administrativa."
                    ),
                ],
            )

        erased = record.erased(at_ms=now)
        detail = reason.strip()
        self._audit_entry(
            record=record,
            principal=principal,
            context=context,
            action="erase",
            categories=record.categories_present(),
            outcome="granted",
            justification_suffix=f" Motivo de la supresión: {detail}" if detail else "",
        )
        self._repo.save(erased)
        self._emit_tombstone(
            erased, reason=TombstoneReason.ERASURE_REQUESTED, now_ms=now
        )
        return erased

    # ------------------------------------------------------------------ #
    # Retención                                                           #
    # ------------------------------------------------------------------ #

    def sweep_expired_retention(self, *, limit: int = 100) -> list[str]:
        """Anonimiza lo que venció. Pensado para un job periódico, no para una ruta.

        Es la contrapartida del principio de temporalidad: sin este barrido, la
        política de retención sería un párrafo en un documento y nada más.
        """
        now = self._clock.now_ms()
        touched: list[str] = []
        for record in self._repo.due_for_anonymization(now, limit=limit):
            anonymized = record.anonymized(at_ms=now)
            self._repo.save(anonymized)
            self._emit_tombstone(
                anonymized, reason=TombstoneReason.RETENTION_EXPIRED, now_ms=now
            )
            self._audit.record(
                AuditEntry(
                    id=self._ids.new_id("aud"),
                    occurred_at=now,
                    actor="service:retention_sweeper",
                    actor_scope=DisclosureScope.AUTHORITY,
                    subject_ref=record.id,
                    action="anonymize",
                    purpose=context_purpose_for_sweep(),
                    justification=(
                        "Venció la retención operativa configurada para el registro "
                        "(Ley 1581 art. 4 lit. c y d)."
                    ),
                    legal_basis=record.consent.legal_basis,
                    categories_disclosed=frozenset(),
                    outcome="granted",
                    channel="job",
                )
            )
            touched.append(record.id)
        return touched

    # ------------------------------------------------------------------ #
    # Interno                                                             #
    # ------------------------------------------------------------------ #

    def _enforce(
        self,
        record: FoundPersonRecord,
        *,
        principal: Principal,
        context: AccessContext,
        action: str,
    ) -> None:
        problems = record.validate()
        if context.purpose not in record.consent.purposes:
            problems.append(
                f"La operación se justifica en la finalidad '{context.purpose.value}', "
                "que no está entre las autorizadas en el registro (art. 4 lit. b)."
            )
        if problems:
            self._audit_entry(
                record=record,
                principal=principal,
                context=context,
                action=action,
                categories=frozenset(),
                outcome="denied",
            )
            raise HabeasDataViolation(
                "El registro no cumple el régimen de protección de datos.",
                details=problems,
            )

    def _emit_tombstone(
        self, record: FoundPersonRecord, *, reason: TombstoneReason, now_ms: int
    ) -> None:
        tombstone = Tombstone(
            record_id=record.id,
            incident_id=record.incident_id,
            issued_at=now_ms,
            reason=reason,
            sequence=self._tombstones.next_sequence(record.incident_id),
        )
        signed = replace(
            tombstone,
            signature=self._signer.sign(
                canonical_bytes(
                    {
                        "typ": "found_persons.tombstone.v1",
                        "record_id": tombstone.record_id,
                        "incident_id": tombstone.incident_id,
                        "issued_at": tombstone.issued_at,
                        "reason": tombstone.reason.value,
                        "sequence": tombstone.sequence,
                    }
                )
            ),
        )
        self._tombstones.append(signed)

    def _audit_entry(
        self,
        *,
        record: FoundPersonRecord | None,
        principal: Principal,
        context: AccessContext,
        action: str,
        categories,
        outcome: str,
        subject_ref: str | None = None,
        legal_basis_hint=None,
        justification_suffix: str = "",
    ) -> str:
        from found_persons.domain.habeas_data import LegalBasis

        basis = (
            record.consent.legal_basis
            if record is not None
            else (legal_basis_hint or LegalBasis.PUBLIC_AUTHORITY_DUTY)
        )
        entry = AuditEntry(
            id=self._ids.new_id("aud"),
            occurred_at=self._clock.now_ms(),
            actor=principal.actor_id,
            actor_scope=principal.scope,
            subject_ref=subject_ref or (record.id if record else "unknown"),
            action=action,
            purpose=context.purpose,
            justification=context.justification + justification_suffix,
            legal_basis=basis,
            categories_disclosed=frozenset(categories),
            outcome=outcome,
            channel=principal.channel,
        )
        self._audit.record(entry)
        return entry.id


def context_purpose_for_sweep():
    """Finalidad del barrido automático: no divulga nada, solo cumple la retención."""
    from found_persons.domain.habeas_data import Purpose

    return Purpose.ANONYMIZED_STATISTICS
