"""Derechos del Titular (Ley 1581 art. 8, 12, 14 y 15).

Una API que minimice perfectamente y no deje al Titular intervenir sobre su dato
sigue siendo incumplidora. Esto verifica la otra mitad.
"""

from __future__ import annotations

from datetime import UTC, datetime

from conftest import (
    DAY_MS,
    INCIDENT,
    NOW_MS,
    consent_payload,
    create_record,
    headers,
)


def as_date(epoch_ms: int) -> str:
    return datetime.fromtimestamp(epoch_ms / 1000, tz=UTC).strftime("%Y-%m-%d")


# --------------------------------------------------------------------------- #
# Art. 8 lit. c — saber quién usó mi dato                                      #
# --------------------------------------------------------------------------- #


def test_access_history_lists_every_actor_that_touched_the_record(client) -> None:
    record_id = create_record(client)
    client.get(f"/v1/hallazgos/{record_id}", headers=headers())
    client.get(f"/v1/hallazgos/{record_id}", headers=headers("dev-authority"))

    history = client.get(
        f"/v1/hallazgos/{record_id}/accesos", headers=headers("dev-authority")
    ).json()

    actions = [e["action"] for e in history]
    assert "create" in actions
    assert actions.count("read") == 2
    actors = {e["actor"] for e in history}
    assert "user:cruz-roja:dev-responder" in actors
    assert "user:ungrd:dev-authority" in actors


def test_access_history_includes_the_justification_each_actor_gave(client) -> None:
    record_id = create_record(client)
    client.get(
        f"/v1/hallazgos/{record_id}",
        headers=headers(justification="Solicitud del puesto de mando unificado."),
    )
    history = client.get(
        f"/v1/hallazgos/{record_id}/accesos", headers=headers("dev-authority")
    ).json()
    justifications = [e["justification"] for e in history]
    assert "Solicitud del puesto de mando unificado." in justifications


def test_access_history_survives_erasure(client) -> None:
    """Saber quién vio el dato antes de borrarlo sigue siendo derecho del Titular."""
    record_id = create_record(client)
    client.get(f"/v1/hallazgos/{record_id}", headers=headers())
    client.delete(f"/v1/hallazgos/{record_id}", headers=headers())

    history = client.get(
        f"/v1/hallazgos/{record_id}/accesos", headers=headers("dev-authority")
    )
    assert history.status_code == 200
    assert any(e["action"] == "read" for e in history.json())
    assert any(e["action"] == "erase" for e in history.json())


# --------------------------------------------------------------------------- #
# Art. 8 lit. b — prueba de la autorización                                    #
# --------------------------------------------------------------------------- #


def test_consent_proof_explains_the_exceptional_basis_in_plain_language(client) -> None:
    """El deber de informar del art. 12 no se cumple citando un artículo."""
    record_id = create_record(client)
    proof = client.get(
        f"/v1/hallazgos/{record_id}/autorizacion", headers=headers("dev-authority")
    ).json()

    assert proof["legal_basis"] == "vital_interest_incapacity"
    assert "no estaba en condiciones de autorizarlo" in proof["legal_basis_explained"]
    assert "artículo 6, literal b" in proof["legal_basis_explained"]
    assert proof["granted_by"] == "user:cruz-roja:dev-responder"
    assert proof["controller"]["rnbd_registration"] == "RNBD-2026-00421"
    assert sorted(proof["categories"]) == ["contact", "identity", "placement"]


def test_consent_proof_is_itself_audited(client, container) -> None:
    record_id = create_record(client)
    client.get(
        f"/v1/hallazgos/{record_id}/autorizacion", headers=headers("dev-authority")
    )
    assert any(
        e.action == "read_consent_proof" for e in container.audit.entries
    )


# --------------------------------------------------------------------------- #
# Art. 8 lit. e — revocar                                                      #
# --------------------------------------------------------------------------- #


def test_revocation_stops_all_further_disclosure(client) -> None:
    record_id = create_record(client)
    response = client.post(
        f"/v1/hallazgos/{record_id}/revocacion",
        json={"reason": "La Titular pide que no se comparta más su ubicación."},
        headers=headers(),
    )
    assert response.status_code == 200

    denied = client.get(f"/v1/hallazgos/{record_id}", headers=headers())
    assert denied.status_code == 403
    assert "revocada por el Titular" in " ".join(denied.json()["details"])


def test_revocation_emits_a_tombstone_for_the_mesh(client) -> None:
    record_id = create_record(client)
    client.post(
        f"/v1/hallazgos/{record_id}/revocacion",
        json={"reason": "La Titular revoca su autorización."},
        headers=headers(),
    )
    page = client.get("/v1/malla/lapidas", params={"incident_id": INCIDENT}).json()
    assert [t["reason"] for t in page["items"]] == ["consent_revoked"]


def test_revocation_cannot_be_undone_by_editing_the_record(client) -> None:
    """Volver a tratar el dato exige autorización nueva, no una edición (art. 9)."""
    from conftest import record_payload

    record_id = create_record(client)
    client.post(
        f"/v1/hallazgos/{record_id}/revocacion",
        json={"reason": "La Titular revoca su autorización."},
        headers=headers(),
    )
    client.put(
        f"/v1/hallazgos/{record_id}", json=record_payload(), headers=headers()
    )
    still_denied = client.get(f"/v1/hallazgos/{record_id}", headers=headers())
    assert still_denied.status_code == 403


def test_update_consent_after_revocation_is_rejected(client) -> None:
    record_id = create_record(client)
    client.post(
        f"/v1/hallazgos/{record_id}/revocacion",
        json={"reason": "La Titular revoca su autorización."},
        headers=headers(),
    )
    response = client.put(
        f"/v1/hallazgos/{record_id}/autorizacion",
        json=consent_payload(legal_basis="subject_consent", expires_at=None),
        headers=headers(),
    )
    assert response.status_code == 422
    assert "autorización nueva" in response.json()["message"]


def test_subject_can_narrow_the_consent_once_able_to_decide(client) -> None:
    """Se entró por interés vital; ahora la persona decide por sí misma."""
    record_id = create_record(client)
    response = client.put(
        f"/v1/hallazgos/{record_id}/autorizacion",
        json=consent_payload(
            legal_basis="subject_consent",
            expires_at=None,
            scopes=["responder", "authority"],
        ),
        headers=headers(),
    )
    assert response.status_code == 200, response.text
    assert response.json()["legal_basis"] == "subject_consent"

    # La familia ya no alcanza: el ámbito dejó de estar consentido.
    assert client.get(
        f"/v1/hallazgos/{record_id}", headers=headers("dev-family")
    ).status_code == 403
    assert client.get(
        f"/v1/hallazgos/{record_id}", headers=headers()
    ).status_code == 200


# --------------------------------------------------------------------------- #
# Art. 14 y 15 — consultas y reclamos                                          #
# --------------------------------------------------------------------------- #


def test_query_deadline_is_ten_business_days(client) -> None:
    """Radicado el lunes 24 de agosto de 2026, vence el lunes 7 de septiembre."""
    response = client.post(
        "/v1/habeas-data/peticiones",
        json={
            "kind": "query",
            "subject_matter": "access",
            "body": "Quiero saber qué datos míos tienen y quién los ha consultado.",
            "filed_by": "María Fernanda Rojas Peña",
        },
    )
    assert response.status_code == 201, response.text
    body = response.json()
    assert as_date(body["due_at"]) == "2026-09-07"
    assert "diez (10) días hábiles" in body["due_at_explained"]


def test_claim_deadline_is_fifteen_business_days(client) -> None:
    response = client.post(
        "/v1/habeas-data/peticiones",
        json={
            "kind": "claim",
            "subject_matter": "erasure",
            "body": "Solicito la supresión de mis datos del incidente.",
            "filed_by": "María Fernanda Rojas Peña",
        },
    )
    assert as_date(response.json()["due_at"]) == "2026-09-14"


def test_filing_a_claim_needs_no_credentials(client) -> None:
    """Quien reclama puede ser justamente alguien sin credenciales que descubrió que
    sus datos están aquí."""
    response = client.post(
        "/v1/habeas-data/peticiones",
        json={
            "kind": "claim",
            "subject_matter": "rectification",
            "body": "Mi apellido está mal escrito en el registro del albergue.",
            "filed_by": "anónimo",
        },
    )
    assert response.status_code == 201


def test_extension_adds_eight_business_days_to_a_claim(client) -> None:
    claim_id = client.post(
        "/v1/habeas-data/peticiones",
        json={
            "kind": "claim",
            "subject_matter": "access",
            "body": "Solicito copia de todos mis datos.",
            "filed_by": "María Fernanda Rojas Peña",
        },
    ).json()["id"]

    response = client.post(
        f"/v1/habeas-data/peticiones/{claim_id}/prorroga",
        json={"motive": "Se requiere consolidar el registro de accesos de tres brigadas."},
        headers=headers(),
    )
    assert response.status_code == 200, response.text
    assert response.json()["status"] == "extended"
    assert as_date(response.json()["extended_until"]) == "2026-09-24"


def test_extension_after_the_deadline_is_rejected(client, clock) -> None:
    claim_id = client.post(
        "/v1/habeas-data/peticiones",
        json={
            "kind": "query",
            "subject_matter": "access",
            "body": "Solicito conocer mis datos personales.",
            "filed_by": "María Fernanda Rojas Peña",
        },
    ).json()["id"]

    clock.advance(40 * DAY_MS)
    response = client.post(
        f"/v1/habeas-data/peticiones/{claim_id}/prorroga",
        json={"motive": "Nos quedamos sin tiempo para responder."},
        headers=headers(),
    )
    assert response.status_code == 422
    assert "ya venció" in response.json()["message"]


def test_overdue_claims_are_surfaced_as_a_breach(client, clock) -> None:
    client.post(
        "/v1/habeas-data/peticiones",
        json={
            "kind": "query",
            "subject_matter": "access",
            "body": "Solicito conocer mis datos personales.",
            "filed_by": "María Fernanda Rojas Peña",
        },
    )
    assert client.get(
        "/v1/habeas-data/peticiones-vencidas", headers=headers()
    ).json() == []

    clock.advance(40 * DAY_MS)
    overdue = client.get(
        "/v1/habeas-data/peticiones-vencidas", headers=headers()
    ).json()
    assert len(overdue) == 1


def test_answering_a_claim_closes_it(client) -> None:
    claim_id = client.post(
        "/v1/habeas-data/peticiones",
        json={
            "kind": "claim",
            "subject_matter": "rectification",
            "body": "Mi apellido está mal escrito.",
            "filed_by": "María Fernanda Rojas Peña",
        },
    ).json()["id"]

    response = client.post(
        f"/v1/habeas-data/peticiones/{claim_id}/respuesta",
        json={"resolution": "Se rectificó el apellido en el registro.", "accepted": True},
        headers=headers(),
    )
    assert response.json()["status"] == "answered"
    assert response.json()["resolved_at"] == NOW_MS


# --------------------------------------------------------------------------- #
# Art. 12 — aviso de privacidad                                                #
# --------------------------------------------------------------------------- #


def test_privacy_notice_is_public_and_names_the_controller(client) -> None:
    """Tiene que poder mostrárselo a alguien cuyos datos se recogieron cuando no
    estaba en condiciones de leer nada."""
    response = client.get("/v1/habeas-data/aviso-de-privacidad")
    assert response.status_code == 200
    body = response.json()
    assert body["responsable"]["nombre"] == "Unidad de Gestión del Riesgo de Manizales"
    assert body["responsable"]["registro_rnbd"] == "RNBD-2026-00421"
    assert len(body["derechos"]) == 6
    assert "Ley 1581 de 2012" in body["base_normativa"]
    assert "no está obligado a autorizar" in body["datos_sensibles"]


# --------------------------------------------------------------------------- #
# Token de búsqueda                                                            #
# --------------------------------------------------------------------------- #


def test_lookup_token_endpoint_requires_accreditation(client) -> None:
    """Quien puede calcular tokens puede comprobar si un documento está registrado."""
    params = {
        "incident_id": INCIDENT,
        "document_type": "CC",
        "document_number": "1.053.812.447",
    }
    assert client.get(
        "/v1/habeas-data/token-de-busqueda", params=params, headers=headers("dev-family")
    ).status_code == 403
    assert client.get(
        "/v1/habeas-data/token-de-busqueda", params=params, headers=headers()
    ).status_code == 200
