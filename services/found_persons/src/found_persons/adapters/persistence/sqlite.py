"""Adaptador real de persistencia sobre SQLite.

Por qué SQLite y no PostgreSQL desde ya: el destino del backend es Postgres+PostGIS
(`services/README.md`), pero este servicio tiene que poder correr en el portátil de
un coordinador de incidente sin infraestructura, que es justo el escenario en que
más falta hace. El puerto `RecordRepository` deja abierta la migración; lo que no
puede quedar abierto es si el servicio arranca o no en campo.

Las columnas indexadas se extraen del JSON al escribir (`lookup_token`,
`incident_id`, `lifecycle`, `updated_at`): buscar por token tiene que ser un índice,
no un recorrido de toda la tabla, o el límite de tasa por dispositivo no sirve de
nada frente a alguien con paciencia.
"""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from found_persons.adapters.persistence.codec import (
    audit_from_dict,
    audit_to_dict,
    claim_from_dict,
    claim_to_dict,
    device_from_dict,
    device_to_dict,
    record_from_dict,
    record_to_dict,
    tombstone_from_dict,
    tombstone_to_dict,
)
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

_SCHEMA = """
PRAGMA journal_mode = WAL;
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS records (
    id            TEXT PRIMARY KEY,
    incident_id   TEXT NOT NULL,
    lookup_token  TEXT NOT NULL,
    status        TEXT NOT NULL,
    lifecycle     TEXT NOT NULL,
    updated_at    INTEGER NOT NULL,
    erase_after   INTEGER NOT NULL,
    legal_hold    INTEGER NOT NULL DEFAULT 0,
    body          TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_records_token ON records (incident_id, lookup_token);
CREATE INDEX IF NOT EXISTS idx_records_incident ON records (incident_id, updated_at DESC);
CREATE INDEX IF NOT EXISTS idx_records_retention ON records (erase_after) WHERE legal_hold = 0;

CREATE TABLE IF NOT EXISTS audit_log (
    id          TEXT PRIMARY KEY,
    occurred_at INTEGER NOT NULL,
    actor       TEXT NOT NULL,
    subject_ref TEXT NOT NULL,
    body        TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_audit_subject ON audit_log (subject_ref, occurred_at DESC);
CREATE INDEX IF NOT EXISTS idx_audit_actor ON audit_log (actor, occurred_at DESC);

CREATE TABLE IF NOT EXISTS devices (
    device_id   TEXT PRIMARY KEY,
    incident_id TEXT NOT NULL,
    body        TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_devices_incident ON devices (incident_id);

CREATE TABLE IF NOT EXISTS tombstones (
    incident_id TEXT NOT NULL,
    sequence    INTEGER NOT NULL,
    body        TEXT NOT NULL,
    PRIMARY KEY (incident_id, sequence)
);

CREATE TABLE IF NOT EXISTS claims (
    id     TEXT PRIMARY KEY,
    status TEXT NOT NULL,
    body   TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS nonces (
    nonce      TEXT PRIMARY KEY,
    expires_at INTEGER NOT NULL
);
"""


def connect(path: str | Path = ":memory:") -> sqlite3.Connection:
    """Conexión con el esquema aplicado.

    `check_same_thread=False` porque uvicorn atiende en varios hilos; la
    serialización la garantiza el propio SQLite en modo WAL para esta carga, que es
    de escritura baja y lectura alta.
    """
    connection = sqlite3.connect(str(path), check_same_thread=False)
    connection.row_factory = sqlite3.Row
    connection.executescript(_SCHEMA)
    connection.commit()
    return connection


class SqliteRecordRepository(RecordRepository):
    def __init__(self, connection: sqlite3.Connection) -> None:
        self._db = connection

    def get(self, record_id: str) -> FoundPersonRecord | None:
        row = self._db.execute(
            "SELECT body FROM records WHERE id = ?", (record_id,)
        ).fetchone()
        return None if row is None else record_from_dict(json.loads(row["body"]))

    def find_by_lookup_token(
        self, incident_id: str, lookup_token: str
    ) -> FoundPersonRecord | None:
        if not lookup_token:
            return None
        # Se prefiere el activo; si no hay, el más reciente (puede estar suprimido, y
        # esa distinción importa para quien ya tenía una copia).
        row = self._db.execute(
            """
            SELECT body FROM records
             WHERE incident_id = ? AND lookup_token = ?
             ORDER BY (lifecycle = 'active') DESC, updated_at DESC
             LIMIT 1
            """,
            (incident_id, lookup_token),
        ).fetchone()
        return None if row is None else record_from_dict(json.loads(row["body"]))

    def search(self, query: RecordQuery) -> tuple[list[FoundPersonRecord], int]:
        where: list[str] = []
        params: list[object] = []
        if query.incident_id:
            where.append("incident_id = ?")
            params.append(query.incident_id)
        if query.status is not None:
            where.append("status = ?")
            params.append(query.status.value)
        if query.lookup_token:
            where.append("lookup_token = ?")
            params.append(query.lookup_token)
        if query.updated_since is not None:
            where.append("updated_at >= ?")
            params.append(query.updated_since)
        if not query.include_erased:
            where.append("lifecycle = ?")
            params.append(RecordLifecycle.ACTIVE.value)

        clause = f"WHERE {' AND '.join(where)}" if where else ""
        total = self._db.execute(
            f"SELECT COUNT(*) AS n FROM records {clause}", params
        ).fetchone()["n"]
        rows = self._db.execute(
            f"SELECT body FROM records {clause} ORDER BY updated_at DESC, id LIMIT ? OFFSET ?",
            [*params, query.limit, query.offset],
        ).fetchall()
        return [record_from_dict(json.loads(r["body"])) for r in rows], total

    def save(self, record: FoundPersonRecord) -> None:
        self._db.execute(
            """
            INSERT INTO records
                (id, incident_id, lookup_token, status, lifecycle, updated_at,
                 erase_after, legal_hold, body)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                lookup_token = excluded.lookup_token,
                status       = excluded.status,
                lifecycle    = excluded.lifecycle,
                updated_at   = excluded.updated_at,
                erase_after  = excluded.erase_after,
                legal_hold   = excluded.legal_hold,
                body         = excluded.body
            """,
            (
                record.id,
                record.incident_id,
                record.subject.lookup_token,
                record.status.value,
                record.lifecycle.value,
                record.updated_at,
                record.retention.erase_after_ms,
                int(record.retention.legal_hold),
                json.dumps(record_to_dict(record), ensure_ascii=False),
            ),
        )
        self._db.commit()

    def purge(self, record_id: str) -> None:
        self._db.execute("DELETE FROM records WHERE id = ?", (record_id,))
        self._db.commit()

    def due_for_anonymization(
        self, now_ms: int, limit: int = 100
    ) -> list[FoundPersonRecord]:
        rows = self._db.execute(
            """
            SELECT body FROM records
             WHERE erase_after <= ? AND legal_hold = 0 AND lifecycle != ?
             ORDER BY erase_after
             LIMIT ?
            """,
            (now_ms, RecordLifecycle.ANONYMIZED.value, limit),
        ).fetchall()
        return [record_from_dict(json.loads(r["body"])) for r in rows]


class SqliteAuditLog(AuditLog):
    """`audit_log` en tabla propia y solo-append.

    No hay método de borrado ni de actualización a propósito: un registro de acceso
    que se puede editar no prueba nada. La retención del propio log se gestiona
    fuera, con volcado a almacenamiento inmutable.
    """

    def __init__(self, connection: sqlite3.Connection) -> None:
        self._db = connection

    def record(self, entry: AuditEntry) -> None:
        self._db.execute(
            "INSERT INTO audit_log (id, occurred_at, actor, subject_ref, body) VALUES (?, ?, ?, ?, ?)",
            (
                entry.id,
                entry.occurred_at,
                entry.actor,
                entry.subject_ref,
                json.dumps(audit_to_dict(entry), ensure_ascii=False),
            ),
        )
        self._db.commit()

    def for_subject(self, subject_ref: str, limit: int = 200) -> list[AuditEntry]:
        rows = self._db.execute(
            "SELECT body FROM audit_log WHERE subject_ref = ? ORDER BY occurred_at DESC LIMIT ?",
            (subject_ref, limit),
        ).fetchall()
        return [audit_from_dict(json.loads(r["body"])) for r in rows]

    def count_for_actor_since(self, actor: str, since_ms: int) -> int:
        row = self._db.execute(
            "SELECT COUNT(*) AS n FROM audit_log WHERE actor = ? AND occurred_at >= ?",
            (actor, since_ms),
        ).fetchone()
        return int(row["n"])


class SqliteDeviceDirectory(DeviceDirectory):
    def __init__(self, connection: sqlite3.Connection) -> None:
        self._db = connection

    def get(self, device_id: str) -> DeviceIdentity | None:
        row = self._db.execute(
            "SELECT body FROM devices WHERE device_id = ?", (device_id,)
        ).fetchone()
        return None if row is None else device_from_dict(json.loads(row["body"]))

    def save(self, device: DeviceIdentity) -> None:
        self._db.execute(
            """
            INSERT INTO devices (device_id, incident_id, body) VALUES (?, ?, ?)
            ON CONFLICT(device_id) DO UPDATE SET
                incident_id = excluded.incident_id, body = excluded.body
            """,
            (
                device.device_id,
                device.incident_id,
                json.dumps(device_to_dict(device), ensure_ascii=False),
            ),
        )
        self._db.commit()

    def list_for_incident(self, incident_id: str) -> list[DeviceIdentity]:
        rows = self._db.execute(
            "SELECT body FROM devices WHERE incident_id = ?", (incident_id,)
        ).fetchall()
        return [device_from_dict(json.loads(r["body"])) for r in rows]


class SqliteTombstoneStore(TombstoneStore):
    def __init__(self, connection: sqlite3.Connection) -> None:
        self._db = connection

    def append(self, tombstone: Tombstone) -> None:
        self._db.execute(
            "INSERT OR REPLACE INTO tombstones (incident_id, sequence, body) VALUES (?, ?, ?)",
            (
                tombstone.incident_id,
                tombstone.sequence,
                json.dumps(tombstone_to_dict(tombstone), ensure_ascii=False),
            ),
        )
        self._db.commit()

    def since(
        self, incident_id: str, sequence: int, limit: int = 500
    ) -> list[Tombstone]:
        rows = self._db.execute(
            """
            SELECT body FROM tombstones
             WHERE incident_id = ? AND sequence > ?
             ORDER BY sequence LIMIT ?
            """,
            (incident_id, sequence, limit),
        ).fetchall()
        return [tombstone_from_dict(json.loads(r["body"])) for r in rows]

    def next_sequence(self, incident_id: str) -> int:
        row = self._db.execute(
            "SELECT COALESCE(MAX(sequence), 0) AS s FROM tombstones WHERE incident_id = ?",
            (incident_id,),
        ).fetchone()
        return int(row["s"]) + 1


class SqliteClaimRepository(ClaimRepository):
    def __init__(self, connection: sqlite3.Connection) -> None:
        self._db = connection

    def get(self, claim_id: str) -> Claim | None:
        row = self._db.execute(
            "SELECT body FROM claims WHERE id = ?", (claim_id,)
        ).fetchone()
        return None if row is None else claim_from_dict(json.loads(row["body"]))

    def save(self, claim: Claim) -> None:
        self._db.execute(
            """
            INSERT INTO claims (id, status, body) VALUES (?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET status = excluded.status, body = excluded.body
            """,
            (claim.id, claim.status, json.dumps(claim_to_dict(claim), ensure_ascii=False)),
        )
        self._db.commit()

    def open_claims(self, now_ms: int) -> list[Claim]:
        rows = self._db.execute(
            "SELECT body FROM claims WHERE status IN ('open', 'extended')"
        ).fetchall()
        return [claim_from_dict(json.loads(r["body"])) for r in rows]


class SqliteNonceStore(NonceStore):
    def __init__(self, connection: sqlite3.Connection) -> None:
        self._db = connection

    def remember(self, nonce: str, expires_at_ms: int) -> bool:
        self._db.execute("DELETE FROM nonces WHERE expires_at < ?", (expires_at_ms,))
        try:
            self._db.execute(
                "INSERT INTO nonces (nonce, expires_at) VALUES (?, ?)",
                (nonce, expires_at_ms),
            )
        except sqlite3.IntegrityError:
            self._db.commit()
            return False
        self._db.commit()
        return True
