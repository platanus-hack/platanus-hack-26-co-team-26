"""Los cuatro verbos, camino feliz y bordes."""

from __future__ import annotations

from conftest import (
    DAY_MS,
    HOUR_MS,
    INCIDENT,
    NOW_MS,
    consent_payload,
    create_record,
    headers,
    record_payload,
)


def test_post_creates_record_and_reports_retention(client) -> None:
    response = client.post(
        "/v1/hallazgos", json=record_payload(), headers=headers()
    )
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["version"] == 1
    assert body["lifecycle"] == "active"
    assert body["legal_basis"] == "vital_interest_incapacity"
    # Sin retención explícita se aplican los 30 días operativos del modelo de amenazas.
    assert body["retention_until"] == NOW_MS + 30 * DAY_MS


def test_get_returns_minimized_record_for_responder(client) -> None:
    record_id = create_record(client)
    response = client.get(f"/v1/hallazgos/{record_id}", headers=headers())
    assert response.status_code == 200, response.text
    body = response.json()

    assert body["display_name"] == "María Fernanda Rojas Peña"
    assert body["document_number"] == "1.053.812.447"
    assert body["municipality"] == "Manizales"
    assert body["address"] == "Carrera 23 # 62-16"
    assert body["scope"] == "responder"
    assert sorted(body["categories_disclosed"]) == ["contact", "identity", "placement"]
    assert body["withheld_categories"] == []


def test_get_unknown_record_is_404(client) -> None:
    response = client.get("/v1/hallazgos/fpr_inexistente", headers=headers())
    assert response.status_code == 404
    assert response.json()["code"] == "record_not_found"


def test_list_paginates_and_filters_by_incident(client) -> None:
    create_record(client)
    create_record(client, document_number="52.114.998", full_name="Jorge Elías Cifuentes")

    response = client.get(
        "/v1/hallazgos", params={"incident_id": INCIDENT}, headers=headers()
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["total"] == 2
    assert len(body["items"]) == 2
    assert body["withheld_records"] == 0


def test_list_has_no_free_text_search(client) -> None:
    """Buscar por nombre convertiría una credencial filtrada en un directorio."""
    create_record(client)
    response = client.get(
        "/v1/hallazgos", params={"full_name": "María"}, headers=headers()
    )
    # `extra=forbid` no aplica a query params; lo que importa es que el filtro se
    # ignore y no exista como funcionalidad.
    assert response.status_code == 200
    assert response.json()["total"] == 1


def test_put_rectifies_and_bumps_version(client) -> None:
    record_id = create_record(client)

    updated = record_payload(
        status="reunified",
        placement={
            "site_name": "Domicilio de la familia",
            "site_type": "home",
            "municipality": "Manizales",
        },
    )
    response = client.put(
        f"/v1/hallazgos/{record_id}", json=updated, headers=headers()
    )
    assert response.status_code == 200, response.text
    assert response.json()["version"] == 2

    body = client.get(f"/v1/hallazgos/{record_id}", headers=headers()).json()
    assert body["status"] == "reunified"
    assert body["site_type"] == "home"


def test_put_emits_tombstone_so_mesh_copies_become_stale(client, container) -> None:
    record_id = create_record(client)
    client.put(
        f"/v1/hallazgos/{record_id}", json=record_payload(status="reunified"), headers=headers()
    )
    tombstones = container.tombstones.since(INCIDENT, 0)
    assert [t.reason for t in tombstones] == ["rectified"]
    assert tombstones[0].signature, "la lápida debe ir firmada o un relay podría fabricarla"


def test_put_on_unknown_record_is_404(client) -> None:
    response = client.put(
        "/v1/hallazgos/fpr_inexistente", json=record_payload(), headers=headers()
    )
    assert response.status_code == 404


def test_delete_redacts_pii_and_keeps_auditable_skeleton(client, container) -> None:
    record_id = create_record(client)
    response = client.delete(
        f"/v1/hallazgos/{record_id}",
        params={"reason": "solicitud directa de la Titular"},
        headers=headers(),
    )
    assert response.status_code == 200, response.text
    assert response.json()["lifecycle"] == "erased"

    stored = container.repository.get(record_id)
    assert stored is not None, "el esqueleto se conserva: audit_log apunta a él"
    assert stored.subject.full_name is None
    assert stored.subject.document_number is None
    assert stored.placement is None
    assert stored.contacts == ()


def test_delete_makes_subsequent_get_return_410(client) -> None:
    record_id = create_record(client)
    client.delete(f"/v1/hallazgos/{record_id}", headers=headers())

    response = client.get(f"/v1/hallazgos/{record_id}", headers=headers())
    assert response.status_code == 410
    assert response.json()["code"] == "record_erased"
    assert response.json()["legal_reference"] == "Ley 1581 de 2012, art. 8 lit. e"


def test_delete_is_idempotent(client) -> None:
    record_id = create_record(client)
    first = client.delete(f"/v1/hallazgos/{record_id}", headers=headers())
    second = client.delete(f"/v1/hallazgos/{record_id}", headers=headers())
    assert first.status_code == second.status_code == 200


def test_duplicate_active_record_is_409(client) -> None:
    create_record(client)
    response = client.post(
        "/v1/hallazgos", json=record_payload(), headers=headers()
    )
    assert response.status_code == 409
    assert response.json()["code"] == "record_already_exists"


def test_same_document_written_differently_is_the_same_person(client) -> None:
    """`1.053.812.447` y `1053812447` son el mismo documento. En campo se digitan
    de las dos formas, y sin normalizar acabaríamos con dos fichas divergentes."""
    create_record(client)
    response = client.post(
        "/v1/hallazgos", json=record_payload(document_number="1053812447"), headers=headers()
    )
    assert response.status_code == 409


def test_erased_record_frees_the_document_for_a_new_record(client) -> None:
    """Tras la supresión, la misma persona puede volver a registrarse si aparece de
    nuevo: la supresión borra el dato, no inhabilita a la persona."""
    record_id = create_record(client)
    client.delete(f"/v1/hallazgos/{record_id}", headers=headers())
    response = client.post("/v1/hallazgos", json=record_payload(), headers=headers())
    assert response.status_code == 201


def test_family_scope_cannot_write(client) -> None:
    response = client.post(
        "/v1/hallazgos", json=record_payload(), headers=headers("dev-family")
    )
    assert response.status_code == 403
    assert response.json()["detail"]["code"] == "insufficient_scope"


def test_requests_without_credentials_are_rejected(client) -> None:
    response = client.get("/v1/hallazgos")
    assert response.status_code == 401


def test_found_at_after_created_at_is_rejected(client) -> None:
    response = client.post(
        "/v1/hallazgos",
        json=record_payload(found_at=NOW_MS + HOUR_MS),
        headers=headers(),
    )
    assert response.status_code == 422
    assert any("posterior a su registro" in d for d in response.json()["details"])


def test_consent_without_matching_categories_is_rejected(client) -> None:
    """El registro trae contactos pero la autorización no cubre `contact`."""
    response = client.post(
        "/v1/hallazgos",
        json=record_payload(
            consent=consent_payload(categories=["identity", "placement"])
        ),
        headers=headers(),
    )
    assert response.status_code == 422
    assert any("no autorizadas" in d for d in response.json()["details"])
