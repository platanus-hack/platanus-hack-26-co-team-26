"""Fixtures compartidas.

El contenedor de tests usa persistencia en memoria y reloj fijo, pero criptografía
**real**: si las cápsulas se firmaran con un *fake*, los tests de malla no probarían
nada de lo que importa. Los identificadores sí son deterministas, para poder
afirmar sobre ellos.
"""

from __future__ import annotations

from urllib.parse import quote

import pytest
from fastapi.testclient import TestClient

from found_persons.adapters.clock import FixedClock
from found_persons.adapters.crypto.ed25519 import (
    Ed25519Signer,
    Ed25519Verifier,
    X25519Sealer,
)
from found_persons.adapters.ids import SequentialIdGenerator
from found_persons.adapters.keys import StaticIncidentKeyProvider
from found_persons.adapters.persistence.memory import (
    InMemoryAuditLog,
    InMemoryClaimRepository,
    InMemoryDeviceDirectory,
    InMemoryNonceStore,
    InMemoryRecordRepository,
    InMemoryTombstoneStore,
)
from found_persons.application.mesh import MeshDisclosureService
from found_persons.application.records import RecordsService
from found_persons.application.rights import DataSubjectRightsService
from found_persons.bootstrap.container import DEV_TOKENS, Container
from found_persons.bootstrap.main import create_app
from found_persons.domain.habeas_data import Controller

#: Lunes 24 de agosto de 2026, 12:00 UTC. Lunes a propósito: los plazos legales van
#: en días hábiles y empezar en fin de semana escondería errores de cálculo.
NOW_MS = 1787572800000

HOUR_MS = 3_600_000
DAY_MS = 24 * HOUR_MS

INCIDENT = "inc-2026-manizales"

TEST_CONTROLLER = Controller(
    name="Unidad de Gestión del Riesgo de Manizales",
    legal_id="NIT-890801052",
    contact_email="habeasdata@ugr-manizales.gov.co",
    rnbd_registration="RNBD-2026-00421",
)


@pytest.fixture
def clock() -> FixedClock:
    return FixedClock(NOW_MS)


@pytest.fixture
def container(clock: FixedClock) -> Container:
    repository = InMemoryRecordRepository()
    audit = InMemoryAuditLog()
    devices = InMemoryDeviceDirectory()
    tombstones = InMemoryTombstoneStore()
    claims = InMemoryClaimRepository()
    nonces = InMemoryNonceStore()
    ids = SequentialIdGenerator()
    signer = Ed25519Signer.generate()
    verifier = Ed25519Verifier()
    sealer = X25519Sealer()
    incident_keys = StaticIncidentKeyProvider()

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
        tokens=dict(DEV_TOKENS),
        controller=TEST_CONTROLLER,
    )


@pytest.fixture
def client(container: Container) -> TestClient:
    return TestClient(create_app(container))


# --------------------------------------------------------------------------- #
# Cabeceras                                                                    #
# --------------------------------------------------------------------------- #


def headers(
    token: str = "dev-responder",
    *,
    purpose: str = "family_reunification",
    justification: str = "Verificación de hallazgo para reunificación familiar.",
) -> dict[str, str]:
    """Cabeceras de una petición autenticada.

    La justificación va percent-encoded: las cabeceras HTTP no transportan UTF-8 y
    cualquier justificación escrita en español lleva tildes. Que el caso normal
    necesite codificarse es exactamente lo que un cliente real encontrará, así que
    los tests pasan por el mismo aro.
    """
    return {
        "Authorization": f"Bearer {token}",
        "X-Purpose": purpose,
        "X-Justification": quote(justification),
    }


# --------------------------------------------------------------------------- #
# Cuerpos de ejemplo                                                           #
# --------------------------------------------------------------------------- #


def consent_payload(**overrides) -> dict:
    """Autorización por interés vital: el caso típico de este servicio.

    Lleva caducidad porque el dominio la exige para toda causal excepcional — una
    excepción sin fecha de vencimiento acaba comportándose como la regla.
    """
    base = {
        "legal_basis": "vital_interest_incapacity",
        "purposes": ["family_reunification", "response_coordination"],
        "categories": ["identity", "placement", "contact"],
        "scopes": ["family", "responder", "authority"],
        "expires_at": NOW_MS + 30 * DAY_MS,
        "proof": {
            "channel": "verbal_responder",
            "captured_by": "user:cruz-roja:dev-responder",
            "captured_at": NOW_MS - HOUR_MS,
            "justification": (
                "La persona fue localizada sin capacidad de manifestar su voluntad; "
                "el tratamiento es necesario para proteger su interés vital "
                "(Ley 1581 art. 6 lit. b)."
            ),
        },
    }
    base.update(overrides)
    return base


def record_payload(**overrides) -> dict:
    base = {
        "incident_id": INCIDENT,
        "document_type": "CC",
        "document_number": "1.053.812.447",
        "full_name": "María Fernanda Rojas Peña",
        "approximate_age": 34,
        "is_minor": False,
        "status": "at_assembly_point",
        "verification": "responder_verified",
        "found_at": NOW_MS - 2 * HOUR_MS,
        "consent": consent_payload(),
        "controller": {
            "name": TEST_CONTROLLER.name,
            "legal_id": TEST_CONTROLLER.legal_id,
            "contact_email": TEST_CONTROLLER.contact_email,
            "rnbd_registration": TEST_CONTROLLER.rnbd_registration,
        },
        "placement": {
            "site_name": "Albergue Colegio San Jorge",
            "site_type": "shelter",
            "municipality": "Manizales",
            "address": "Carrera 23 # 62-16",
            "lat": 5.0703,
            "lon": -75.5138,
        },
        "contacts": [
            {"kind": "phone", "value": "+573001234567", "belongs_to": "next_of_kin"}
        ],
        "notes": "",
    }
    base.update(overrides)
    return base


def create_record(client: TestClient, **overrides) -> str:
    """Crea un registro y devuelve su id. Falla ruidosamente si la creación no pasa."""
    response = client.post(
        "/v1/hallazgos", json=record_payload(**overrides), headers=headers()
    )
    assert response.status_code == 201, response.text
    return response.json()["record_id"]
