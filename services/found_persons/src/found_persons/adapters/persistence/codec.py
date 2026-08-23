"""Traducción entre entidades del dominio y filas serializables.

Vive en la capa de adaptadores a propósito: el dominio no sabe que existe una base
de datos, y el día que la persistencia sea PostgreSQL con PostGIS (el destino real,
ver `services/README.md`) este archivo es el que cambia.
"""

from __future__ import annotations

from typing import Any

from found_persons.domain.habeas_data import (
    AuditEntry,
    Consent,
    ConsentProof,
    Controller,
    DataCategory,
    DisclosureScope,
    LegalBasis,
    Purpose,
    Retention,
    Tombstone,
    TombstoneReason,
)
from found_persons.domain.mesh import DeviceIdentity
from found_persons.domain.records import (
    Claim,
    ContactChannel,
    FoundPersonRecord,
    PersonReference,
    Placement,
)
from found_persons.domain.vocabulary import (
    RecordLifecycle,
    SituationStatus,
    VerificationLevel,
)


def record_to_dict(record: FoundPersonRecord) -> dict[str, Any]:
    return {
        "id": record.id,
        "incident_id": record.incident_id,
        "subject": {
            "lookup_token": record.subject.lookup_token,
            "full_name": record.subject.full_name,
            "document_type": record.subject.document_type,
            "document_number": record.subject.document_number,
            "approximate_age": record.subject.approximate_age,
            "is_minor": record.subject.is_minor,
        },
        "status": record.status.value,
        "verification": record.verification.value,
        "reported_by": record.reported_by,
        "found_at": record.found_at,
        "created_at": record.created_at,
        "updated_at": record.updated_at,
        "consent": {
            "legal_basis": record.consent.legal_basis.value,
            "purposes": sorted(p.value for p in record.consent.purposes),
            "categories": sorted(c.value for c in record.consent.categories),
            "scopes": sorted(s.value for s in record.consent.scopes),
            "expires_at": record.consent.expires_at,
            "revoked_at": record.consent.revoked_at,
            "revocation_reason": record.consent.revocation_reason,
            "proof": {
                "channel": record.consent.proof.channel,
                "captured_at": record.consent.proof.captured_at,
                "captured_by": record.consent.proof.captured_by,
                "evidence_sha256": record.consent.proof.evidence_sha256,
                "evidence_uri": record.consent.proof.evidence_uri,
                "justification": record.consent.proof.justification,
            },
        },
        "controller": {
            "name": record.controller.name,
            "legal_id": record.controller.legal_id,
            "contact_email": record.controller.contact_email,
            "rnbd_registration": record.controller.rnbd_registration,
            "privacy_notice_version": record.controller.privacy_notice_version,
        },
        "retention": {
            "erase_after_ms": record.retention.erase_after_ms,
            "legal_hold": record.retention.legal_hold,
            "legal_hold_reason": record.retention.legal_hold_reason,
        },
        "placement": None
        if record.placement is None
        else {
            "site_name": record.placement.site_name,
            "site_type": record.placement.site_type,
            "municipality": record.placement.municipality,
            "address": record.placement.address,
            "lat": record.placement.lat,
            "lon": record.placement.lon,
        },
        "contacts": [
            {"kind": c.kind, "value": c.value, "belongs_to": c.belongs_to}
            for c in record.contacts
        ],
        "care_notes": record.care_notes,
        "biometric_ref": record.biometric_ref,
        "lifecycle": record.lifecycle.value,
        "erased_at": record.erased_at,
        "version": record.version,
        "notes": record.notes,
    }


def record_from_dict(raw: dict[str, Any]) -> FoundPersonRecord:
    consent_raw = raw["consent"]
    proof_raw = consent_raw["proof"]
    placement_raw = raw.get("placement")
    return FoundPersonRecord(
        id=raw["id"],
        incident_id=raw["incident_id"],
        subject=PersonReference(**raw["subject"]),
        status=SituationStatus(raw["status"]),
        verification=VerificationLevel(raw["verification"]),
        reported_by=raw["reported_by"],
        found_at=raw["found_at"],
        created_at=raw["created_at"],
        updated_at=raw["updated_at"],
        consent=Consent(
            legal_basis=LegalBasis(consent_raw["legal_basis"]),
            purposes=frozenset(Purpose(p) for p in consent_raw["purposes"]),
            categories=frozenset(DataCategory(c) for c in consent_raw["categories"]),
            scopes=frozenset(DisclosureScope(s) for s in consent_raw["scopes"]),
            proof=ConsentProof(**proof_raw),
            expires_at=consent_raw["expires_at"],
            revoked_at=consent_raw["revoked_at"],
            revocation_reason=consent_raw["revocation_reason"],
        ),
        controller=Controller(**raw["controller"]),
        retention=Retention(**raw["retention"]),
        placement=None if placement_raw is None else Placement(**placement_raw),
        contacts=tuple(ContactChannel(**c) for c in raw.get("contacts", [])),
        care_notes=raw.get("care_notes"),
        biometric_ref=raw.get("biometric_ref"),
        lifecycle=RecordLifecycle(raw["lifecycle"]),
        erased_at=raw.get("erased_at"),
        version=raw.get("version", 1),
        notes=raw.get("notes", ""),
    )


def audit_to_dict(entry: AuditEntry) -> dict[str, Any]:
    return {
        "id": entry.id,
        "occurred_at": entry.occurred_at,
        "actor": entry.actor,
        "actor_scope": entry.actor_scope.value,
        "subject_ref": entry.subject_ref,
        "action": entry.action,
        "purpose": entry.purpose.value,
        "justification": entry.justification,
        "legal_basis": entry.legal_basis.value,
        "categories_disclosed": sorted(c.value for c in entry.categories_disclosed),
        "outcome": entry.outcome,
        "channel": entry.channel,
    }


def audit_from_dict(raw: dict[str, Any]) -> AuditEntry:
    return AuditEntry(
        id=raw["id"],
        occurred_at=raw["occurred_at"],
        actor=raw["actor"],
        actor_scope=DisclosureScope(raw["actor_scope"]),
        subject_ref=raw["subject_ref"],
        action=raw["action"],
        purpose=Purpose(raw["purpose"]),
        justification=raw["justification"],
        legal_basis=LegalBasis(raw["legal_basis"]),
        categories_disclosed=frozenset(
            DataCategory(c) for c in raw["categories_disclosed"]
        ),
        outcome=raw["outcome"],
        channel=raw["channel"],
    )


def device_to_dict(device: DeviceIdentity) -> dict[str, Any]:
    return {
        "device_id": device.device_id,
        "incident_id": device.incident_id,
        "signing_public_key": device.signing_public_key,
        "scope": device.scope.value,
        "accredited_by": device.accredited_by,
        "accredited_at": device.accredited_at,
        "kex_public_key": device.kex_public_key,
        "organization": device.organization,
        "holder_ref": device.holder_ref,
        "expires_at": device.expires_at,
        "revoked_at": device.revoked_at,
        "revocation_reason": device.revocation_reason,
    }


def device_from_dict(raw: dict[str, Any]) -> DeviceIdentity:
    data = dict(raw)
    data["scope"] = DisclosureScope(data["scope"])
    return DeviceIdentity(**data)


def tombstone_to_dict(tombstone: Tombstone) -> dict[str, Any]:
    return {
        "record_id": tombstone.record_id,
        "incident_id": tombstone.incident_id,
        "issued_at": tombstone.issued_at,
        "reason": tombstone.reason.value,
        "sequence": tombstone.sequence,
        "signature": tombstone.signature,
    }


def tombstone_from_dict(raw: dict[str, Any]) -> Tombstone:
    data = dict(raw)
    data["reason"] = TombstoneReason(data["reason"])
    return Tombstone(**data)


def claim_to_dict(claim: Claim) -> dict[str, Any]:
    return {
        "id": claim.id,
        "record_id": claim.record_id,
        "kind": claim.kind,
        "channel": claim.channel,
        "filed_by": claim.filed_by,
        "filed_at": claim.filed_at,
        "due_at": claim.due_at,
        "subject_matter": claim.subject_matter,
        "body": claim.body,
        "status": claim.status,
        "extended_until": claim.extended_until,
        "resolution": claim.resolution,
        "resolved_at": claim.resolved_at,
        "fields_to_correct": list(claim.fields_to_correct),
    }


def claim_from_dict(raw: dict[str, Any]) -> Claim:
    data = dict(raw)
    data["fields_to_correct"] = tuple(data.get("fields_to_correct", ()))
    return Claim(**data)
