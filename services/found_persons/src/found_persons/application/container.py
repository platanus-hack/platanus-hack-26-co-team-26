"""Agregado de servicios y puertos ya resueltos.

Vive en `application` y no en `bootstrap` por una razón de capas: el adaptador HTTP
necesita alcanzar los casos de uso, y si el tipo que se los entrega estuviera en
`bootstrap`, `adapters` importaría hacia arriba y la regla de `.importlinter`
dejaría de sostenerse.

Aquí solo está la **forma** del grafo. Quién lo construye —SQLite o memoria,
Ed25519 real o *fake*— lo decide `bootstrap/container.py`, que es el único módulo
autorizado a conocer adaptadores concretos.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from found_persons.application.context import Principal
from found_persons.application.mesh import MeshDisclosureService
from found_persons.application.ports import (
    AuditLog,
    ClaimRepository,
    Clock,
    DeviceDirectory,
    IdGenerator,
    IncidentKeyProvider,
    NonceStore,
    PayloadSealer,
    RecordRepository,
    SignatureVerifier,
    Signer,
    TombstoneStore,
)
from found_persons.application.records import RecordsService
from found_persons.application.rights import DataSubjectRightsService
from found_persons.domain.habeas_data import Controller

#: Responsable del Tratamiento por defecto. Un despliegue real **debe** sustituirlo:
#: un aviso de privacidad que no nombra a nadie no cumple el deber de informar
#: (Ley 1581 art. 12).
DEFAULT_CONTROLLER = Controller(
    name="Autoridad del incidente (configurar en despliegue)",
    legal_id="NIT-000000000",
    contact_email="habeasdata@sismomesh.example",
    rnbd_registration=None,
)


@dataclass(slots=True)
class Container:
    """Grafo de dependencias resuelto que el adaptador HTTP consume."""

    records: RecordsService
    mesh: MeshDisclosureService
    rights: DataSubjectRightsService
    repository: RecordRepository
    audit: AuditLog
    devices: DeviceDirectory
    tombstones: TombstoneStore
    claims: ClaimRepository
    nonces: NonceStore
    clock: Clock
    ids: IdGenerator
    signer: Signer
    verifier: SignatureVerifier
    sealer: PayloadSealer
    incident_keys: IncidentKeyProvider
    tokens: dict[str, Principal] = field(default_factory=dict)
    controller: Controller = DEFAULT_CONTROLLER
