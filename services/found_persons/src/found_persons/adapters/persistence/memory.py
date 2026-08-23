"""Adaptadores en memoria — *fakes* deterministas exigidos por CONTRIBUTING.

No son juguetes: el arranque de demostración corre sobre estos, porque un incidente
simulado no debería dejar datos personales en disco. Toda la lógica de filtrado y
orden vive aquí para que el adaptador SQLite pueda testearse contra el mismo
comportamiento.
"""

from __future__ import annotations

from found_persons.application.ports import (
    AuditLog,
    ClaimRepository,
    DeviceDirectory,
    NonceStore,
    RecordRepository,
    TombstoneStore,
)
from found_persons.domain.habeas_data import AuditEntry, Tombstone
from found_persons.domain.mesh import DeviceIdentity
from found_persons.domain.records import Claim, FoundPersonRecord, RecordQuery
from found_persons.domain.vocabulary import RecordLifecycle


class InMemoryRecordRepository(RecordRepository):
    def __init__(self) -> None:
        self._by_id: dict[str, FoundPersonRecord] = {}

    def get(self, record_id: str) -> FoundPersonRecord | None:
        return self._by_id.get(record_id)

    def find_by_lookup_token(
        self, incident_id: str, lookup_token: str
    ) -> FoundPersonRecord | None:
        if not lookup_token:
            return None
        candidates = [
            r
            for r in self._by_id.values()
            if r.incident_id == incident_id
            and r.subject.lookup_token == lookup_token
        ]
        if not candidates:
            return None
        # Un registro suprimido conserva su token: es lo que permite responder
        # "esto se borró" en vez de "esto nunca existió" a quien ya tenía copia.
        active = [c for c in candidates if c.lifecycle is RecordLifecycle.ACTIVE]
        pool = active or candidates
        return max(pool, key=lambda r: r.updated_at)

    def search(self, query: RecordQuery) -> tuple[list[FoundPersonRecord], int]:
        rows = list(self._by_id.values())
        if query.incident_id:
            rows = [r for r in rows if r.incident_id == query.incident_id]
        if query.status is not None:
            rows = [r for r in rows if r.status is query.status]
        if query.lookup_token:
            rows = [r for r in rows if r.subject.lookup_token == query.lookup_token]
        if query.updated_since is not None:
            rows = [r for r in rows if r.updated_at >= query.updated_since]
        if not query.include_erased:
            rows = [r for r in rows if r.lifecycle is RecordLifecycle.ACTIVE]
        rows.sort(key=lambda r: (-r.updated_at, r.id))
        total = len(rows)
        page = rows[query.offset : query.offset + query.limit]
        return page, total

    def save(self, record: FoundPersonRecord) -> None:
        self._by_id[record.id] = record

    def purge(self, record_id: str) -> None:
        self._by_id.pop(record_id, None)

    def due_for_anonymization(
        self, now_ms: int, limit: int = 100
    ) -> list[FoundPersonRecord]:
        due = [
            r
            for r in self._by_id.values()
            if r.lifecycle is not RecordLifecycle.ANONYMIZED
            and r.retention.expired(now_ms)
            and not r.retention.legal_hold
        ]
        due.sort(key=lambda r: r.retention.erase_after_ms)
        return due[:limit]


class InMemoryAuditLog(AuditLog):
    def __init__(self) -> None:
        self._entries: list[AuditEntry] = []

    def record(self, entry: AuditEntry) -> None:
        self._entries.append(entry)

    def for_subject(self, subject_ref: str, limit: int = 200) -> list[AuditEntry]:
        rows = [e for e in self._entries if e.subject_ref == subject_ref]
        rows.sort(key=lambda e: e.occurred_at, reverse=True)
        return rows[:limit]

    def count_for_actor_since(self, actor: str, since_ms: int) -> int:
        return sum(
            1 for e in self._entries if e.actor == actor and e.occurred_at >= since_ms
        )

    @property
    def entries(self) -> list[AuditEntry]:
        """Solo para tests: permite afirmar que se auditó antes de responder."""
        return list(self._entries)


class InMemoryDeviceDirectory(DeviceDirectory):
    def __init__(self) -> None:
        self._devices: dict[str, DeviceIdentity] = {}

    def get(self, device_id: str) -> DeviceIdentity | None:
        return self._devices.get(device_id)

    def save(self, device: DeviceIdentity) -> None:
        self._devices[device.device_id] = device

    def list_for_incident(self, incident_id: str) -> list[DeviceIdentity]:
        return [d for d in self._devices.values() if d.incident_id == incident_id]


class InMemoryTombstoneStore(TombstoneStore):
    def __init__(self) -> None:
        self._by_incident: dict[str, list[Tombstone]] = {}

    def append(self, tombstone: Tombstone) -> None:
        self._by_incident.setdefault(tombstone.incident_id, []).append(tombstone)

    def since(
        self, incident_id: str, sequence: int, limit: int = 500
    ) -> list[Tombstone]:
        rows = [
            t
            for t in self._by_incident.get(incident_id, [])
            if t.sequence > sequence
        ]
        rows.sort(key=lambda t: t.sequence)
        return rows[:limit]

    def next_sequence(self, incident_id: str) -> int:
        return len(self._by_incident.get(incident_id, [])) + 1


class InMemoryClaimRepository(ClaimRepository):
    def __init__(self) -> None:
        self._claims: dict[str, Claim] = {}

    def get(self, claim_id: str) -> Claim | None:
        return self._claims.get(claim_id)

    def save(self, claim: Claim) -> None:
        self._claims[claim.id] = claim

    def open_claims(self, now_ms: int) -> list[Claim]:
        return [c for c in self._claims.values() if c.status in {"open", "extended"}]


class InMemoryNonceStore(NonceStore):
    """Anti-replay con purga perezosa. En producción esto es Redis con TTL nativo."""

    def __init__(self) -> None:
        self._seen: dict[str, int] = {}

    def remember(self, nonce: str, expires_at_ms: int) -> bool:
        self._evict(expires_at_ms)
        if nonce in self._seen:
            return False
        self._seen[nonce] = expires_at_ms
        return True

    def _evict(self, now_ms: int) -> None:
        expired = [n for n, exp in self._seen.items() if exp < now_ms]
        for nonce in expired:
            del self._seen[nonce]
