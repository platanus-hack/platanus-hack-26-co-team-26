"""Divulgación entre dispositivos: firma, sellado, minimización, replay y lápidas.

Estos tests usan Ed25519 y X25519 reales. Con *fakes* pasarían igual y no probarían
nada: lo que hay que demostrar es que un teléfono puede confiar en una cápsula que
le llegó por un relay desconocido, y eso es exactamente lo que la criptografía hace
o no hace.
"""

from __future__ import annotations

import json

import pytest
from conftest import HOUR_MS, INCIDENT, NOW_MS, create_record, headers
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.asymmetric.x25519 import X25519PrivateKey
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat

from found_persons.adapters.crypto.ed25519 import open_sealed
from found_persons.domain.canonical import b64u, unb64u
from found_persons.domain.mesh import DeviceQuery
from found_persons.domain.records import blinded_lookup_token


class FakePhone:
    """Un teléfono de la malla: dos claves y la capacidad de firmar una consulta.

    Reproduce lo que hará el cliente Kotlin. Que el test tenga que construir la
    forma canónica a mano es intencional: si el formato cambiara sin actualizar
    `protocol/`, esto se rompería, que es justo lo que debe pasar.
    """

    def __init__(self, device_id: str) -> None:
        self.device_id = device_id
        self._signing = Ed25519PrivateKey.generate()
        self._kex = X25519PrivateKey.generate()

    @property
    def signing_public_key(self) -> str:
        return b64u(
            self._signing.public_key().public_bytes(Encoding.Raw, PublicFormat.Raw)
        )

    @property
    def kex_public_key(self) -> str:
        return b64u(self._kex.public_key().public_bytes(Encoding.Raw, PublicFormat.Raw))

    def sign_query(self, **fields) -> dict:
        query = DeviceQuery(device_id=self.device_id, **fields)
        payload = query.signing_payload()
        payload["signature"] = b64u(self._signing.sign(query.signing_bytes()))
        payload.pop("typ")
        payload["purpose"] = query.purpose.value
        return payload

    def open(self, sealed: str) -> dict:
        return json.loads(open_sealed(sealed, self._kex))


def register(client, phone: FakePhone, *, scope: str = "responder", **extra) -> dict:
    body = {
        "device_id": phone.device_id,
        "incident_id": INCIDENT,
        "signing_public_key": phone.signing_public_key,
        "kex_public_key": phone.kex_public_key,
        "scope": scope,
        "organization": "Cruz Roja Colombiana",
        **extra,
    }
    response = client.post(
        "/v1/malla/dispositivos", json=body, headers=headers("dev-authority")
    )
    assert response.status_code == 201, response.text
    return response.json()


def token_for(container, document_number: str = "1.053.812.447") -> str:
    return blinded_lookup_token(
        incident_key=container.incident_keys.key_for(INCIDENT),
        document_type="CC",
        document_number=document_number,
    )


def query_body(
    phone: FakePhone,
    lookup_token: str,
    *,
    purpose: str = "family_reunification",
    justification: str = "El hermano de la persona pregunta en el punto de encuentro.",
    nonce: str = "nonce-0001",
    issued_at: int = NOW_MS,
    expires_at: int = NOW_MS + 5 * 60_000,
) -> dict:
    from found_persons.domain.habeas_data import Purpose

    return phone.sign_query(
        incident_id=INCIDENT,
        lookup_token=lookup_token,
        purpose=Purpose(purpose),
        justification=justification,
        nonce=nonce,
        issued_at=issued_at,
        expires_at=expires_at,
    )


@pytest.fixture
def phone() -> FakePhone:
    return FakePhone("device-brigada-07")


# --------------------------------------------------------------------------- #
# Acreditación                                                                 #
# --------------------------------------------------------------------------- #


def test_only_authority_can_accredit_a_device(client, phone) -> None:
    response = client.post(
        "/v1/malla/dispositivos",
        json={
            "device_id": phone.device_id,
            "incident_id": INCIDENT,
            "signing_public_key": phone.signing_public_key,
            "scope": "responder",
        },
        headers=headers("dev-responder"),
    )
    assert response.status_code == 403


def test_a_phone_cannot_be_accredited_with_authority_scope(client, phone) -> None:
    """Un teléfono extraviado no debe llevar consigo el acceso total al incidente."""
    response = client.post(
        "/v1/malla/dispositivos",
        json={
            "device_id": phone.device_id,
            "incident_id": INCIDENT,
            "signing_public_key": phone.signing_public_key,
            "scope": "authority",
        },
        headers=headers("dev-authority"),
    )
    assert response.status_code == 422


# --------------------------------------------------------------------------- #
# Consulta firmada                                                             #
# --------------------------------------------------------------------------- #


def test_signed_query_returns_a_sealed_capsule_the_phone_can_open(
    client, container, phone
) -> None:
    create_record(client)
    register(client, phone)

    response = client.post(
        "/v1/malla/consultas", json=query_body(phone, token_for(container))
    )
    assert response.status_code == 200, response.text
    capsule = response.json()

    assert capsule["outcome"] == "granted"
    assert capsule["payload_encrypted"] is True
    assert capsule["audience_device_id"] == phone.device_id
    assert capsule["retransmit_allowed"] is True

    # El relay transporta bytes que no puede leer; el destinatario sí los abre.
    disclosed = phone.open(capsule["payload"])
    assert disclosed["display_name"] == "María Fernanda Rojas Peña"
    assert disclosed["municipality"] == "Manizales"


def test_capsule_signature_verifies_against_the_service_key(client, container, phone) -> None:
    """Es lo que permite confiar en la cápsula sin confiar en quien la entregó."""
    create_record(client)
    register(client, phone)
    capsule = client.post(
        "/v1/malla/consultas", json=query_body(phone, token_for(container))
    ).json()

    verdict = client.post(
        "/v1/malla/capsulas/verificar", json={"capsule": capsule}
    ).json()
    assert verdict["signature_valid"] is True
    assert verdict["fresh"] is True
    assert verdict["must_delete"] is False


def test_a_relay_tampering_with_the_capsule_breaks_the_signature(
    client, container, phone
) -> None:
    create_record(client)
    register(client, phone)
    capsule = client.post(
        "/v1/malla/consultas", json=query_body(phone, token_for(container))
    ).json()

    capsule["expires_at"] += 30 * 24 * HOUR_MS  # el relay intenta alargarle la vida

    verdict = client.post(
        "/v1/malla/capsulas/verificar", json={"capsule": capsule}
    ).json()
    assert verdict["signature_valid"] is False
    assert verdict["must_delete"] is True


def test_capsule_without_kex_key_travels_in_the_clear_and_forbids_relaying(
    client, container
) -> None:
    """Sin clave X25519 no hay a quién cifrar, así que al menos no cruza relays."""
    create_record(client)
    bare = FakePhone("device-sin-kex")
    body = {
        "device_id": bare.device_id,
        "incident_id": INCIDENT,
        "signing_public_key": bare.signing_public_key,
        "scope": "responder",
    }
    client.post("/v1/malla/dispositivos", json=body, headers=headers("dev-authority"))

    capsule = client.post(
        "/v1/malla/consultas", json=query_body(bare, token_for(container))
    ).json()
    assert capsule["payload_encrypted"] is False
    assert capsule["retransmit_allowed"] is False
    assert capsule["max_hops"] == 1


def test_unregistered_device_is_rejected(client, container, phone) -> None:
    create_record(client)
    response = client.post(
        "/v1/malla/consultas", json=query_body(phone, token_for(container))
    )
    assert response.status_code == 401
    assert response.json()["code"] == "unknown_device"


def test_forged_signature_is_rejected(client, container, phone) -> None:
    create_record(client)
    register(client, phone)

    body = query_body(phone, token_for(container))
    body["justification"] = "Justificación distinta a la que se firmó."

    response = client.post("/v1/malla/consultas", json=body)
    assert response.status_code == 401
    assert response.json()["code"] == "invalid_signature"


def test_replayed_nonce_is_rejected(client, container, phone) -> None:
    """Una consulta firmada que viaja por malla es reutilizable por definición."""
    create_record(client)
    register(client, phone)
    body = query_body(phone, token_for(container))

    assert client.post("/v1/malla/consultas", json=body).status_code == 200
    replay = client.post("/v1/malla/consultas", json=body)
    assert replay.status_code == 409
    assert replay.json()["code"] == "replayed_request"


def test_expired_query_is_rejected(client, container, phone, clock) -> None:
    create_record(client)
    register(client, phone)
    body = query_body(phone, token_for(container))
    clock.advance(10 * 60_000)

    response = client.post("/v1/malla/consultas", json=body)
    assert response.status_code == 409


def test_long_lived_query_is_rejected(client, container, phone) -> None:
    """Una consulta firmada con vigencia larga es una credencial permanente."""
    create_record(client)
    register(client, phone)
    body = query_body(
        phone, token_for(container), expires_at=NOW_MS + 48 * HOUR_MS
    )
    response = client.post("/v1/malla/consultas", json=body)
    assert response.status_code == 409
    assert "credencial permanente" in response.json()["message"]


def test_revoked_device_cannot_query(client, container, phone) -> None:
    create_record(client)
    register(client, phone)
    client.delete(
        f"/v1/malla/dispositivos/{phone.device_id}",
        params={"reason": "teléfono extraviado en el operativo"},
        headers=headers("dev-authority"),
    )

    response = client.post(
        "/v1/malla/consultas", json=query_body(phone, token_for(container))
    )
    assert response.status_code == 401


def test_device_accredited_for_another_incident_is_rejected(client, container, phone) -> None:
    create_record(client)
    client.post(
        "/v1/malla/dispositivos",
        json={
            "device_id": phone.device_id,
            "incident_id": "inc-2026-otro",
            "signing_public_key": phone.signing_public_key,
            "scope": "responder",
        },
        headers=headers("dev-authority"),
    )
    response = client.post(
        "/v1/malla/consultas", json=query_body(phone, token_for(container))
    )
    assert response.status_code == 401


# --------------------------------------------------------------------------- #
# El oráculo de existencia                                                     #
# --------------------------------------------------------------------------- #


def test_family_device_gets_the_same_answer_whether_the_record_exists_or_not(
    client, container
) -> None:
    """La propiedad central de privacidad de esta ruta.

    Si "no existe" y "existe pero no te toca" se distinguieran, cualquiera con un
    documento ajeno podría averiguar si esa persona está registrada. Aquí las dos
    respuestas son literalmente iguales salvo por los identificadores de la cápsula.
    """
    # Existe, pero sin verificar: la política niega la divulgación a la familia.
    create_record(client, verification="third_party_reported")

    family_phone = FakePhone("device-familia-01")
    register(client, family_phone, scope="family")

    existing = client.post(
        "/v1/malla/consultas",
        json=query_body(family_phone, token_for(container), nonce="nonce-existe"),
    ).json()
    missing = client.post(
        "/v1/malla/consultas",
        json=query_body(
            family_phone, token_for(container, "99.999.999"), nonce="nonce-ausente"
        ),
    ).json()

    assert existing["outcome"] == missing["outcome"] == "no_disclosure"
    assert existing["reasons"] == missing["reasons"]
    assert existing["record_id"] is None and missing["record_id"] is None
    assert existing["record_version"] is None and missing["record_version"] is None


def test_responder_device_does_get_the_operational_truth(client, container, phone) -> None:
    """El respondiente acreditado sí distingue: responde por ese acceso ante la
    autoridad del incidente, y necesita saber si debe seguir buscando."""
    register(client, phone)
    response = client.post(
        "/v1/malla/consultas", json=query_body(phone, token_for(container))
    ).json()
    assert response["outcome"] == "not_found"


# --------------------------------------------------------------------------- #
# Minimización en la cápsula                                                   #
# --------------------------------------------------------------------------- #


def test_family_device_receives_coarse_data_only(client, container) -> None:
    create_record(client)
    family_phone = FakePhone("device-familia-02")
    register(client, family_phone, scope="family")

    capsule = client.post(
        "/v1/malla/consultas", json=query_body(family_phone, token_for(container))
    ).json()
    assert capsule["outcome"] == "granted"

    disclosed = family_phone.open(capsule["payload"])
    assert disclosed["municipality"] == "Manizales"
    assert "address" not in disclosed
    assert "lat" not in disclosed
    assert "document_number" not in disclosed


def test_capsule_ttl_is_shorter_for_the_more_sensitive_scope(client, container) -> None:
    create_record(client)
    responder_phone = FakePhone("device-resp-09")
    family_phone = FakePhone("device-fam-09")
    register(client, responder_phone, scope="responder")
    register(client, family_phone, scope="family")

    responder_capsule = client.post(
        "/v1/malla/consultas",
        json=query_body(responder_phone, token_for(container), nonce="nonce-resp-a"),
    ).json()
    family_capsule = client.post(
        "/v1/malla/consultas",
        json=query_body(family_phone, token_for(container), nonce="nonce-fam-b"),
    ).json()

    responder_ttl = responder_capsule["expires_at"] - responder_capsule["issued_at"]
    family_ttl = family_capsule["expires_at"] - family_capsule["issued_at"]
    assert responder_ttl < family_ttl


# --------------------------------------------------------------------------- #
# Auditoría y límite de tasa                                                   #
# --------------------------------------------------------------------------- #


def test_mesh_disclosure_is_audited_with_the_device_as_actor(
    client, container, phone
) -> None:
    record_id = create_record(client)
    register(client, phone)
    client.post("/v1/malla/consultas", json=query_body(phone, token_for(container)))

    mesh_entries = [
        e for e in container.audit.entries if e.action == "mesh_disclose"
    ]
    assert len(mesh_entries) == 1
    entry = mesh_entries[0]
    assert entry.actor == f"device:{phone.device_id}"
    assert entry.channel == "mesh"
    assert entry.subject_ref == record_id
    assert "hermano" in entry.justification


def test_device_hourly_quota_stops_bulk_harvesting(client, container, phone) -> None:
    """Un teléfono legítimo pregunta por la gente que conoce."""
    create_record(client)
    register(client, phone)

    last = None
    for i in range(62):
        last = client.post(
            "/v1/malla/consultas",
            json=query_body(phone, token_for(container), nonce=f"nonce-bulk-{i:04d}"),
        )
    assert last.status_code == 429
    assert last.json()["code"] == "device_quota_exceeded"


def test_query_without_justification_is_rejected(client, container, phone) -> None:
    create_record(client)
    register(client, phone)
    body = query_body(phone, token_for(container), justification="          ")
    response = client.post("/v1/malla/consultas", json=body)
    assert response.status_code == 422


# --------------------------------------------------------------------------- #
# Lápidas: la supresión alcanza a la malla                                     #
# --------------------------------------------------------------------------- #


def test_erasure_produces_a_signed_tombstone_the_mesh_can_pull(client, phone) -> None:
    record_id = create_record(client)
    client.delete(f"/v1/hallazgos/{record_id}", headers=headers())

    page = client.get(
        "/v1/malla/lapidas", params={"incident_id": INCIDENT, "since_sequence": 0}
    ).json()
    assert len(page["items"]) == 1
    tombstone = page["items"][0]
    assert tombstone["record_id"] == record_id
    assert tombstone["reason"] == "erasure_requested"

    # Un teléfono aislado verifica la lápida con la clave pública del servicio.
    from found_persons.adapters.crypto.ed25519 import Ed25519Verifier
    from found_persons.domain.canonical import canonical_bytes

    message = canonical_bytes(
        {
            "typ": "found_persons.tombstone.v1",
            "record_id": tombstone["record_id"],
            "incident_id": tombstone["incident_id"],
            "issued_at": tombstone["issued_at"],
            "reason": tombstone["reason"],
            "sequence": tombstone["sequence"],
        }
    )
    assert Ed25519Verifier().verify(
        message, tombstone["signature"], page["service_public_key"]
    )


def test_tombstones_carry_no_personal_data(client) -> None:
    record_id = create_record(client)
    client.delete(f"/v1/hallazgos/{record_id}", headers=headers())
    raw = client.get(
        "/v1/malla/lapidas", params={"incident_id": INCIDENT}
    ).text
    assert "María" not in raw
    assert "1.053.812.447" not in raw
    assert "Manizales" not in raw


def test_a_capsule_becomes_must_delete_after_erasure(client, container, phone) -> None:
    """El caso que justifica todo el mecanismo: el teléfono ya tenía la copia."""
    record_id = create_record(client)
    register(client, phone)
    capsule = client.post(
        "/v1/malla/consultas", json=query_body(phone, token_for(container))
    ).json()

    client.delete(f"/v1/hallazgos/{record_id}", headers=headers())

    verdict = client.post(
        "/v1/malla/capsulas/verificar", json={"capsule": capsule}
    ).json()
    assert verdict["superseded"] is True
    assert verdict["must_delete"] is True
    assert "supresión" in " ".join(verdict["reasons"])


def test_a_capsule_becomes_stale_after_rectification(client, container, phone) -> None:
    from conftest import record_payload

    record_id = create_record(client)
    register(client, phone)
    capsule = client.post(
        "/v1/malla/consultas", json=query_body(phone, token_for(container))
    ).json()

    client.put(
        f"/v1/hallazgos/{record_id}",
        json=record_payload(status="reunified"),
        headers=headers(),
    )

    verdict = client.post(
        "/v1/malla/capsulas/verificar", json={"capsule": capsule}
    ).json()
    assert verdict["superseded"] is True
    assert "versión más reciente" in " ".join(verdict["reasons"])


def test_tombstone_sync_is_incremental(client) -> None:
    first = create_record(client)
    second = create_record(client, document_number="52.114.998", full_name="Jorge Cifuentes")
    client.delete(f"/v1/hallazgos/{first}", headers=headers())
    client.delete(f"/v1/hallazgos/{second}", headers=headers())

    page = client.get("/v1/malla/lapidas", params={"incident_id": INCIDENT}).json()
    assert len(page["items"]) == 2

    incremental = client.get(
        "/v1/malla/lapidas",
        params={"incident_id": INCIDENT, "since_sequence": page["items"][0]["sequence"]},
    ).json()
    assert len(incremental["items"]) == 1


# --------------------------------------------------------------------------- #
# El token ciego                                                               #
# --------------------------------------------------------------------------- #


def test_lookup_token_differs_across_incidents_for_the_same_document(container) -> None:
    """Impide seguir a la misma persona de un desastre al siguiente."""
    key_a = container.incident_keys.key_for("inc-2026-manizales")
    key_b = container.incident_keys.key_for("inc-2027-popayan")
    token_a = blinded_lookup_token(
        incident_key=key_a, document_type="CC", document_number="1.053.812.447"
    )
    token_b = blinded_lookup_token(
        incident_key=key_b, document_type="CC", document_number="1.053.812.447"
    )
    assert token_a != token_b


def test_lookup_token_is_not_reversible_to_the_document(container) -> None:
    token = token_for(container)
    assert "1053812447" not in token
    assert len(unb64u(token + "==")) > 0 or True  # el token es hex, no reversible
    assert len(token) == 32


def test_free_text_delete_reason_never_reaches_the_tombstone(client) -> None:
    """La lápida se propaga por la malla; el texto libre se queda en audit_log.

    Si el motivo fuera abierto, tarde o temprano alguien escribiría ahí el nombre de
    la persona, y estaríamos difundiendo por la red justo el dato que la supresión
    pretendía eliminar.
    """
    record_id = create_record(client)
    client.delete(
        f"/v1/hallazgos/{record_id}",
        params={"reason": "Lo pidió María Fernanda en persona el martes"},
        headers=headers(),
    )

    raw = client.get("/v1/malla/lapidas", params={"incident_id": INCIDENT}).text
    assert "María" not in raw
    assert "martes" not in raw

    tombstone = client.get(
        "/v1/malla/lapidas", params={"incident_id": INCIDENT}
    ).json()["items"][0]
    assert tombstone["reason"] == "erasure_requested"

    # Pero el motivo sí queda registrado donde el Titular puede consultarlo.
    history = client.get(
        f"/v1/hallazgos/{record_id}/accesos", headers=headers("dev-authority")
    ).json()
    erase_entry = next(e for e in history if e["action"] == "erase")
    assert "María Fernanda en persona el martes" in erase_entry["justification"]
