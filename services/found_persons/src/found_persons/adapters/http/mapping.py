"""Conversión DTO ↔ dominio. Deliberadamente aburrida y explícita.

Nada de copiar campos automáticamente: si mañana alguien añade `lookup_token` al
DTO de salida, tiene que escribirlo a mano y alguien lo verá en la revisión. Un
mapeo automático habría filtrado el token sin que nadie se enterara.
"""

from __future__ import annotations

from found_persons.adapters.http import schemas as s
from found_persons.application.records import NewRecordCommand, ReplaceRecordCommand
from found_persons.domain.habeas_data import (
    AuditEntry,
    Consent,
    ConsentProof,
    Controller,
    Retention,
    Tombstone,
)
from found_persons.domain.mesh import DeviceIdentity, DeviceQuery, DisclosureCapsule
from found_persons.domain.policies import DisclosureView, default_retention_deadline
from found_persons.domain.records import Claim, ContactChannel, Placement


def consent_from_dto(dto: s.ConsentIn, *, now_ms: int) -> Consent:
    return Consent(
        legal_basis=dto.legal_basis,
        purposes=frozenset(dto.purposes),
        categories=frozenset(dto.categories),
        scopes=frozenset(dto.scopes),
        proof=ConsentProof(
            channel=dto.proof.channel,
            captured_at=dto.proof.captured_at or now_ms,
            captured_by=dto.proof.captured_by,
            evidence_sha256=dto.proof.evidence_sha256,
            evidence_uri=dto.proof.evidence_uri,
            justification=dto.proof.justification,
        ),
        expires_at=dto.expires_at,
    )


def controller_from_dto(dto: s.ControllerIn) -> Controller:
    return Controller(
        name=dto.name,
        legal_id=dto.legal_id,
        contact_email=dto.contact_email,
        rnbd_registration=dto.rnbd_registration,
        privacy_notice_version=dto.privacy_notice_version,
    )


def retention_from_dto(dto: s.RetentionIn | None, *, now_ms: int) -> Retention | None:
    if dto is None:
        return None
    return Retention(
        erase_after_ms=dto.erase_after_ms or default_retention_deadline(now_ms),
        legal_hold=dto.legal_hold,
        legal_hold_reason=dto.legal_hold_reason,
    )


def placement_from_dto(dto: s.PlacementIn | None) -> Placement | None:
    if dto is None:
        return None
    return Placement(
        site_name=dto.site_name,
        site_type=dto.site_type,
        municipality=dto.municipality,
        address=dto.address,
        lat=dto.lat,
        lon=dto.lon,
    )


def contacts_from_dto(items: list[s.ContactIn]) -> tuple[ContactChannel, ...]:
    return tuple(
        ContactChannel(kind=c.kind, value=c.value, belongs_to=c.belongs_to)
        for c in items
    )


def new_record_command(dto: s.RecordIn, *, now_ms: int) -> NewRecordCommand:
    return NewRecordCommand(
        incident_id=dto.incident_id,
        status=dto.status,
        verification=dto.verification,
        found_at=dto.found_at,
        consent=consent_from_dto(dto.consent, now_ms=now_ms),
        controller=controller_from_dto(dto.controller),
        document_type=dto.document_type,
        document_number=dto.document_number,
        full_name=dto.full_name,
        approximate_age=dto.approximate_age,
        is_minor=dto.is_minor,
        placement=placement_from_dto(dto.placement),
        contacts=contacts_from_dto(dto.contacts),
        care_notes=dto.care_notes,
        biometric_ref=dto.biometric_ref,
        retention=retention_from_dto(dto.retention, now_ms=now_ms),
        notes=dto.notes,
    )


def replace_record_command(dto: s.RecordIn, *, now_ms: int) -> ReplaceRecordCommand:
    return ReplaceRecordCommand(
        status=dto.status,
        verification=dto.verification,
        found_at=dto.found_at,
        consent=consent_from_dto(dto.consent, now_ms=now_ms),
        controller=controller_from_dto(dto.controller),
        document_type=dto.document_type,
        document_number=dto.document_number,
        full_name=dto.full_name,
        approximate_age=dto.approximate_age,
        is_minor=dto.is_minor,
        placement=placement_from_dto(dto.placement),
        contacts=contacts_from_dto(dto.contacts),
        care_notes=dto.care_notes,
        biometric_ref=dto.biometric_ref,
        retention=retention_from_dto(dto.retention, now_ms=now_ms),
        notes=dto.notes,
    )


def view_to_dto(view: DisclosureView) -> s.RecordOut:
    """Vista minimizada → DTO. Sin `lookup_token`: quien lee no debe poder
    reconstruir la clave de búsqueda de otra persona."""
    return s.RecordOut(
        record_id=view.record_id,
        incident_id=view.incident_id,
        status=view.status,
        verification=view.verification,
        found_at=view.found_at,
        updated_at=view.updated_at,
        version=view.version,
        scope=view.scope,
        categories_disclosed=sorted(c.value for c in view.categories),
        withheld_categories=list(view.withheld),
        display_name=view.display_name,
        initials=view.initials,
        document_type=view.document_type,
        document_number=view.document_number,
        is_minor=view.is_minor,
        site_name=view.site_name,
        site_type=view.site_type,
        municipality=view.municipality,
        address=view.address,
        lat=view.lat,
        lon=view.lon,
        contacts=[dict(c) for c in view.contacts],
        care_notes=view.care_notes,
        biometric_ref=view.biometric_ref,
    )


def device_to_dto(device: DeviceIdentity) -> s.DeviceOut:
    return s.DeviceOut(
        device_id=device.device_id,
        incident_id=device.incident_id,
        scope=device.scope,
        organization=device.organization,
        accredited_by=device.accredited_by,
        accredited_at=device.accredited_at,
        expires_at=device.expires_at,
        revoked_at=device.revoked_at,
        sealed_delivery=bool(device.kex_public_key),
    )


def query_from_dto(dto: s.DeviceQueryIn) -> DeviceQuery:
    return DeviceQuery(
        device_id=dto.device_id,
        incident_id=dto.incident_id,
        lookup_token=dto.lookup_token,
        purpose=dto.purpose,
        justification=dto.justification,
        nonce=dto.nonce,
        issued_at=dto.issued_at,
        expires_at=dto.expires_at,
        signature=dto.signature,
    )


def capsule_to_dto(capsule: DisclosureCapsule) -> s.CapsuleOut:
    return s.CapsuleOut(
        capsule_id=capsule.capsule_id,
        incident_id=capsule.incident_id,
        audience_device_id=capsule.audience_device_id,
        scope=capsule.scope,
        purpose=capsule.purpose,
        outcome=capsule.outcome,
        issued_at=capsule.issued_at,
        expires_at=capsule.expires_at,
        payload=capsule.payload,
        payload_encrypted=capsule.payload_encrypted,
        record_id=capsule.record_id,
        record_version=capsule.record_version,
        reasons=list(capsule.reasons),
        audit_id=capsule.audit_id,
        max_hops=capsule.max_hops,
        retransmit_allowed=capsule.retransmit_allowed,
        signature=capsule.signature,
    )


def capsule_from_dto(dto: s.CapsuleOut) -> DisclosureCapsule:
    return DisclosureCapsule(
        capsule_id=dto.capsule_id,
        incident_id=dto.incident_id,
        audience_device_id=dto.audience_device_id,
        scope=dto.scope,
        purpose=dto.purpose,
        outcome=dto.outcome,
        issued_at=dto.issued_at,
        expires_at=dto.expires_at,
        payload=dto.payload,
        payload_encrypted=dto.payload_encrypted,
        record_id=dto.record_id,
        record_version=dto.record_version,
        reasons=tuple(dto.reasons),
        audit_id=dto.audit_id,
        max_hops=dto.max_hops,
        retransmit_allowed=dto.retransmit_allowed,
        signature=dto.signature,
    )


def tombstone_to_dto(tombstone: Tombstone) -> s.TombstoneOut:
    return s.TombstoneOut(
        record_id=tombstone.record_id,
        incident_id=tombstone.incident_id,
        issued_at=tombstone.issued_at,
        reason=tombstone.reason,
        sequence=tombstone.sequence,
        signature=tombstone.signature,
    )


def audit_to_dto(entry: AuditEntry) -> s.AuditEntryOut:
    return s.AuditEntryOut(
        id=entry.id,
        occurred_at=entry.occurred_at,
        actor=entry.actor,
        actor_scope=entry.actor_scope,
        action=entry.action,
        purpose=entry.purpose,
        justification=entry.justification,
        legal_basis=entry.legal_basis,
        categories_disclosed=sorted(c.value for c in entry.categories_disclosed),
        outcome=entry.outcome,
        channel=entry.channel,
    )


def claim_to_dto(claim: Claim) -> s.ClaimOut:
    plazo = (
        "diez (10) días hábiles, prorrogables cinco (5) — Ley 1581 art. 14"
        if claim.kind == "query"
        else "quince (15) días hábiles, prorrogables ocho (8) — Ley 1581 art. 15"
    )
    return s.ClaimOut(
        id=claim.id,
        kind=claim.kind,
        record_id=claim.record_id,
        subject_matter=claim.subject_matter,
        filed_by=claim.filed_by,
        filed_at=claim.filed_at,
        due_at=claim.due_at,
        due_at_explained=plazo,
        status=claim.status,
        extended_until=claim.extended_until,
        resolution=claim.resolution,
        resolved_at=claim.resolved_at,
    )
