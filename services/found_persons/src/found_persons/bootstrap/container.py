"""Cableado de adaptadores. El único sitio donde se decide qué implementación corre.

Todo lo demás recibe puertos por constructor, así que cambiar SQLite por PostgreSQL
o los *fakes* criptográficos por los reales es editar este archivo. Los tests
construyen su propio contenedor con adaptadores en memoria y no tocan nada más.
"""

from __future__ import annotations

import os
from datetime import date

from found_persons.adapters.clock import SystemClock
from found_persons.adapters.crypto.ed25519 import (
    Ed25519Signer,
    Ed25519Verifier,
    X25519Sealer,
)
from found_persons.adapters.ids import SecureIdGenerator
from found_persons.adapters.keys import DerivedIncidentKeyProvider
from found_persons.adapters.persistence import sqlite as sql
from found_persons.application.container import DEFAULT_CONTROLLER, Container
from found_persons.application.context import Principal
from found_persons.application.mesh import MeshDisclosureService
from found_persons.application.records import RecordsService
from found_persons.application.rights import DataSubjectRightsService
from found_persons.domain.habeas_data import Controller, DisclosureScope

#: Credenciales de desarrollo. En producción el `Principal` sale del proveedor de
#: identidad del incidente (OIDC + rol + organización), no de un diccionario.
#: Se mantienen aquí para que `make up` levante algo usable sin montar un IdP.
DEV_TOKENS: dict[str, Principal] = {
    "dev-authority": Principal(
        actor_id="user:ungrd:dev-authority",
        scope=DisclosureScope.AUTHORITY,
        organization="UNGRD",
    ),
    "dev-responder": Principal(
        actor_id="user:cruz-roja:dev-responder",
        scope=DisclosureScope.RESPONDER,
        organization="Cruz Roja Colombiana",
    ),
    "dev-family": Principal(
        actor_id="user:family:dev-family",
        scope=DisclosureScope.FAMILY,
    ),
}

def build_container(
    *,
    database_path: str | None = None,
    master_key: bytes | None = None,
    signing_seed_hex: str | None = None,
    tokens: dict[str, Principal] | None = None,
    controller: Controller | None = None,
    holidays: frozenset[date] = frozenset(),
) -> Container:
    """Construye el contenedor real: SQLite, Ed25519 y X25519.

    `signing_seed_hex` importa más de lo que parece: si la clave de firma cambia en
    cada arranque, todas las cápsulas que ya viajan por la malla dejan de verificar.
    En desarrollo se genera una efímera y se avisa por log; en producción viene del
    gestor de secretos.
    """
    connection = sql.connect(
        database_path or os.environ.get("FOUND_PERSONS_DB", ":memory:")
    )

    repository = sql.SqliteRecordRepository(connection)
    audit = sql.SqliteAuditLog(connection)
    devices = sql.SqliteDeviceDirectory(connection)
    tombstones = sql.SqliteTombstoneStore(connection)
    claims = sql.SqliteClaimRepository(connection)
    nonces = sql.SqliteNonceStore(connection)

    clock = SystemClock()
    ids = SecureIdGenerator()
    seed = signing_seed_hex or os.environ.get("FOUND_PERSONS_SIGNING_SEED")
    signer = Ed25519Signer.from_seed_hex(seed) if seed else Ed25519Signer.generate()
    verifier = Ed25519Verifier()
    sealer = X25519Sealer()

    raw_key = master_key or os.environ.get("FOUND_PERSONS_MASTER_KEY", "").encode()
    incident_keys = DerivedIncidentKeyProvider(
        raw_key if len(raw_key) >= 32 else b"desarrollo-" + b"0" * 32
    )

    resolved_controller = controller or DEFAULT_CONTROLLER

    return Container(
        records=RecordsService(
            repository=repository,
            audit=audit,
            tombstones=tombstones,
            clock=clock,
            ids=ids,
            signer=signer,
            incident_keys=incident_keys,
        ),
        mesh=MeshDisclosureService(
            repository=repository,
            devices=devices,
            audit=audit,
            tombstones=tombstones,
            nonces=nonces,
            clock=clock,
            ids=ids,
            signer=signer,
            verifier=verifier,
            sealer=sealer,
        ),
        rights=DataSubjectRightsService(
            repository=repository,
            audit=audit,
            claims=claims,
            tombstones=tombstones,
            clock=clock,
            ids=ids,
            signer=signer,
            holidays=holidays,
        ),
        repository=repository,
        audit=audit,
        devices=devices,
        tombstones=tombstones,
        claims=claims,
        nonces=nonces,
        clock=clock,
        ids=ids,
        signer=signer,
        verifier=verifier,
        sealer=sealer,
        incident_keys=incident_keys,
        tokens=tokens or dict(DEV_TOKENS),
        controller=resolved_controller,
    )
