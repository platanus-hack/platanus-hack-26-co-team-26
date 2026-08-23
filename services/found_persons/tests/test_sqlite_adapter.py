"""Integración contra el adaptador real de persistencia.

El resto de la batería corre sobre los *fakes* en memoria, que es lo correcto para
probar reglas. Pero un puerto con dos implementaciones y una sola probada es un
puerto con una implementación probada: esto verifica que la de verdad se comporta
igual en lo que importa — serialización de ida y vuelta, búsqueda por token,
paginación y barrido de retención.
"""

from __future__ import annotations

import pytest
from conftest import DAY_MS, INCIDENT, NOW_MS, create_record, headers, record_payload
from fastapi.testclient import TestClient

from found_persons.adapters.clock import FixedClock
from found_persons.adapters.crypto.ed25519 import (
    Ed25519Signer,
    Ed25519Verifier,
    X25519Sealer,
)
from found_persons.adapters.ids import SequentialIdGenerator
from found_persons.adapters.keys import StaticIncidentKeyProvider
from found_persons.adapters.persistence import sqlite as sql
from found_persons.application.mesh import MeshDisclosureService
from found_persons.application.records import RecordsService
from found_persons.application.rights import DataSubjectRightsService
from found_persons.bootstrap.container import DEV_TOKENS, Container
from found_persons.bootstrap.main import create_app
from found_persons.domain.habeas_data import DataCategory
from found_persons.domain.records import RecordQuery, blinded_lookup_token


@pytest.fixture
def sqlite_container(tmp_path):
    """Contenedor sobre un archivo real, no `:memory:`.

    Con `:memory:` no se comprobaría que el JSON serializado sobrevive a un `commit`
    y vuelve a leerse igual, que es la mitad del riesgo de este adaptador.
    """
    connection = sql.connect(tmp_path / "found_persons.db")
    clock = FixedClock(NOW_MS)
    repository = sql.SqliteRecordRepository(connection)
    audit = sql.SqliteAuditLog(connection)
    devices = sql.SqliteDeviceDirectory(connection)
    tombstones = sql.SqliteTombstoneStore(connection)
    claims = sql.SqliteClaimRepository(connection)
    nonces = sql.SqliteNonceStore(connection)
    ids = SequentialIdGenerator()
    signer = Ed25519Signer.generate()
    keys = StaticIncidentKeyProvider()

    return Container(
        records=RecordsService(
            repository=repository,
            audit=audit,
            tombstones=tombstones,
            clock=clock,
            ids=ids,
            signer=signer,
            incident_keys=keys,
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
            verifier=Ed25519Verifier(),
            sealer=X25519Sealer(),
        ),
        rights=DataSubjectRightsService(
            repository=repository,
            audit=audit,
            claims=claims,
            tombstones=tombstones,
            clock=clock,
            ids=ids,
            signer=signer,
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
        verifier=Ed25519Verifier(),
        sealer=X25519Sealer(),
        incident_keys=keys,
        tokens=dict(DEV_TOKENS),
    )


@pytest.fixture
def sqlite_client(sqlite_container) -> TestClient:
    return TestClient(create_app(sqlite_container))


def test_record_survives_a_round_trip_through_disk(sqlite_client, sqlite_container) -> None:
    record_id = create_record(sqlite_client)
    stored = sqlite_container.repository.get(record_id)

    assert stored.subject.full_name == "María Fernanda Rojas Peña"
    assert stored.consent.legal_basis.value == "vital_interest_incapacity"
    assert stored.consent.categories == {
        DataCategory.IDENTITY,
        DataCategory.PLACEMENT,
        DataCategory.CONTACT,
    }
    assert stored.placement.lat == pytest.approx(5.0703)
    assert stored.contacts[0].value == "+573001234567"
    assert stored.retention.erase_after_ms == NOW_MS + 30 * DAY_MS


def test_lookup_by_blinded_token_uses_the_index(sqlite_client, sqlite_container) -> None:
    create_record(sqlite_client)
    token = blinded_lookup_token(
        incident_key=sqlite_container.incident_keys.key_for(INCIDENT),
        document_type="CC",
        document_number="1053812447",
    )
    found = sqlite_container.repository.find_by_lookup_token(INCIDENT, token)
    assert found is not None
    assert found.subject.full_name == "María Fernanda Rojas Peña"


def test_search_paginates_and_counts_correctly(sqlite_client, sqlite_container) -> None:
    for i in range(7):
        sqlite_client.post(
            "/v1/hallazgos",
            json=record_payload(
                document_number=f"10{i}0000000", full_name=f"Persona {i}"
            ),
            headers=headers(),
        )

    page, total = sqlite_container.repository.search(
        RecordQuery(incident_id=INCIDENT, limit=3, offset=3)
    )
    assert total == 7
    assert len(page) == 3


def test_erased_record_keeps_its_token_so_the_mesh_learns_it_was_deleted(
    sqlite_client, sqlite_container
) -> None:
    record_id = create_record(sqlite_client)
    sqlite_client.delete(f"/v1/hallazgos/{record_id}", headers=headers())

    token = blinded_lookup_token(
        incident_key=sqlite_container.incident_keys.key_for(INCIDENT),
        document_type="CC",
        document_number="1.053.812.447",
    )
    found = sqlite_container.repository.find_by_lookup_token(INCIDENT, token)
    assert found is not None
    assert found.lifecycle.value == "erased"
    assert found.subject.full_name is None


def test_retention_sweep_works_against_the_index(
    sqlite_client, sqlite_container
) -> None:
    record_id = create_record(sqlite_client)
    sqlite_container.clock.advance(31 * DAY_MS)
    assert sqlite_container.records.sweep_expired_retention() == [record_id]
    assert sqlite_container.repository.get(record_id).lifecycle.value == "anonymized"


def test_audit_log_is_append_only_and_queryable_by_subject(
    sqlite_client, sqlite_container
) -> None:
    record_id = create_record(sqlite_client)
    sqlite_client.get(f"/v1/hallazgos/{record_id}", headers=headers())

    entries = sqlite_container.audit.for_subject(record_id)
    assert {e.action for e in entries} == {"create", "read"}
    assert all(e.justification for e in entries)


def test_nonce_store_rejects_the_second_use(sqlite_container) -> None:
    assert sqlite_container.nonces.remember("nonce-unico-01", NOW_MS + 60_000) is True
    assert sqlite_container.nonces.remember("nonce-unico-01", NOW_MS + 60_000) is False
