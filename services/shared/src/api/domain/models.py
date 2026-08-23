"""Modelo de dominio del backend — Sección 12.2 (PostgreSQL + PostGIS).

Sin dependencias de FastAPI/SQLAlchemy aquí (regla hexagonal: domain no importa
framework). Los adaptadores de persistencia (adapters/persistence) traducen hacia
y desde estas entidades.

Dueño: Miguel. Revisor obligatorio: Helmut (bundle_ingestor verifica firmas producidas por core/crypto).
"""

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Incident:
    id: str
    source: str
    cap_id: str
    magnitude: float | None
    epicenter: tuple[float, float] | None  # (lat, lon)
    started_at: int
    activated_at: int | None
    status: str
    config: dict = field(default_factory=dict)


@dataclass(frozen=True)
class Node:
    id: str
    incident_id: str
    ephemeral_id: bytes
    encrypted_profile: bytes | None
    key_policy: dict
    first_seen: int
    last_seen: int
    device_class: str | None
    transport_caps: list[str] = field(default_factory=list)
    consent_flags: dict = field(default_factory=dict)


@dataclass(frozen=True)
class Bundle:
    id: bytes
    incident_id: str
    node_id: str
    priority: int
    signature_valid: bool
    created_at: int
    received_at: int
    hop_count: int
    payload_type: str
    payload: bytes


# TODO(dueño=Miguel): Status, Location, PeerObservation, MotionEvidence,
# BiomarkerEvidence, LocalizationEstimate, Gateway, AuditLog, RawBlob — Sección 12.2.
