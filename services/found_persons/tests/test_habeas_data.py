"""Cumplimiento de la Ley 1581: minimización, bases legales, auditoría y retención.

Cada test nombra el artículo que verifica. Si alguno falla, lo que se rompió no es
una funcionalidad: es el fundamento por el que este servicio puede existir.
"""

from __future__ import annotations

from conftest import (
    DAY_MS,
    consent_payload,
    create_record,
    headers,
    record_payload,
)

# --------------------------------------------------------------------------- #
# Art. 4 lit. f — minimización y acceso restringido                            #
# --------------------------------------------------------------------------- #


def test_family_scope_gets_coarse_location_only(client) -> None:
    """La familia sabe el municipio y que está a salvo; no la dirección exacta."""
    record_id = create_record(client)
    body = client.get(
        f"/v1/hallazgos/{record_id}", headers=headers("dev-family")
    ).json()

    assert body["municipality"] == "Manizales"
    assert body["site_type"] == "shelter"
    assert body["address"] is None, "la dirección exacta no corresponde al ámbito familiar"
    assert body["lat"] is None and body["lon"] is None
    assert body["site_name"] is None


def test_family_scope_never_sees_the_document_number(client) -> None:
    record_id = create_record(client)
    body = client.get(
        f"/v1/hallazgos/{record_id}", headers=headers("dev-family")
    ).json()
    assert body["display_name"] == "María Fernanda Rojas Peña"
    assert body["document_number"] is None
    assert body["document_type"] is None


def test_withheld_categories_are_declared_not_hidden(client) -> None:
    """Recortar en silencio haría creer al solicitante que eso es todo lo que hay."""
    record_id = create_record(
        client,
        consent=consent_payload(
            legal_basis="subject_consent",
            categories=["identity", "placement", "contact", "health_related"],
            scopes=["family", "responder", "authority"],
            expires_at=None,
        ),
        care_notes="Requiere agua y una silla para desplazarse.",
    )
    body = client.get(
        f"/v1/hallazgos/{record_id}", headers=headers("dev-family")
    ).json()

    assert body["care_notes"] is None
    assert "health_related" in body["withheld_categories"]


def test_responder_sees_care_notes_when_consent_covers_them(client) -> None:
    record_id = create_record(
        client,
        consent=consent_payload(
            categories=["identity", "placement", "contact", "health_related"]
        ),
        care_notes="Requiere agua y una silla para desplazarse.",
    )
    body = client.get(f"/v1/hallazgos/{record_id}", headers=headers()).json()
    assert body["care_notes"] == "Requiere agua y una silla para desplazarse."


def test_statistical_purpose_gets_no_identifying_data(client) -> None:
    """Art. 6 lit. e: la finalidad estadística exige suprimir la identidad."""
    record_id = create_record(
        client,
        consent=consent_payload(
            purposes=[
                "family_reunification",
                "response_coordination",
                "anonymized_statistics",
            ]
        ),
    )
    body = client.get(
        f"/v1/hallazgos/{record_id}",
        headers=headers("dev-authority", purpose="anonymized_statistics"),
    ).json()

    assert body["display_name"] is None
    assert body["document_number"] is None
    assert body["municipality"] is None
    assert body["categories_disclosed"] == []
    assert body["status"] == "at_assembly_point", "el hecho agregado sí se conserva"


# --------------------------------------------------------------------------- #
# Art. 4 lit. b — principio de finalidad                                       #
# --------------------------------------------------------------------------- #


def test_purpose_outside_the_authorized_ones_is_denied(client) -> None:
    record_id = create_record(client)
    response = client.get(
        f"/v1/hallazgos/{record_id}",
        headers=headers("dev-authority", purpose="authority_notification"),
    )
    assert response.status_code == 403
    assert response.json()["code"] == "disclosure_denied"
    assert any("finalidad" in d for d in response.json()["details"])


# --------------------------------------------------------------------------- #
# Art. 6 — datos sensibles                                                     #
# --------------------------------------------------------------------------- #


def test_sensitive_data_under_a_basis_that_does_not_allow_it_is_rejected(client) -> None:
    """`public_authority_duty` (art. 10 lit. a) no está entre las causales del art. 6."""
    response = client.post(
        "/v1/hallazgos",
        json=record_payload(
            consent=consent_payload(
                legal_basis="public_authority_duty",
                categories=["identity", "placement", "contact", "health_related"],
            ),
            care_notes="Requiere apoyo para caminar.",
        ),
        headers=headers("dev-authority"),
    )
    assert response.status_code == 422
    details = " ".join(response.json()["details"])
    assert "no habilita datos sensibles" in details
    assert "art. 6" in details


def test_care_facility_placement_is_health_data_even_without_notes(client) -> None:
    """Estar en un centro asistencial es un dato de salud aunque nadie lo declare.

    La categoría se calcula del contenido, no del formulario: si dependiera de que
    el operador marcara una casilla, bastaría con no marcarla para saltarse el art. 6.
    """
    response = client.post(
        "/v1/hallazgos",
        json=record_payload(
            consent=consent_payload(
                legal_basis="public_authority_duty",
                categories=["identity", "placement", "contact"],
            ),
            placement={
                "site_name": "Hospital de Caldas",
                "site_type": "care_facility",
                "municipality": "Manizales",
            },
        ),
        headers=headers("dev-authority"),
    )
    assert response.status_code == 422
    assert "health_related" in " ".join(response.json()["details"])


def test_exceptional_basis_requires_written_justification(client) -> None:
    proof = consent_payload()["proof"] | {"justification": "   "}
    response = client.post(
        "/v1/hallazgos",
        json=record_payload(consent=consent_payload(proof=proof)),
        headers=headers(),
    )
    assert response.status_code == 422
    assert "justificación escrita" in " ".join(response.json()["details"])


def test_exceptional_basis_requires_an_expiry(client) -> None:
    """Una excepción sin fecha de vencimiento deja de ser excepción."""
    response = client.post(
        "/v1/hallazgos",
        json=record_payload(consent=consent_payload(expires_at=None)),
        headers=headers(),
    )
    assert response.status_code == 422
    assert "caducidad" in " ".join(response.json()["details"])


def test_expired_legal_basis_stops_disclosure(client, clock) -> None:
    record_id = create_record(client)
    clock.advance(31 * DAY_MS)

    response = client.get(f"/v1/hallazgos/{record_id}", headers=headers())
    assert response.status_code == 403
    assert "caducada" in " ".join(response.json()["details"])


# --------------------------------------------------------------------------- #
# ADR-0007 — ningún dato personal en el ámbito público                         #
# --------------------------------------------------------------------------- #


def test_public_scope_cannot_be_consented_for_a_record_with_pii(client) -> None:
    response = client.post(
        "/v1/hallazgos",
        json=record_payload(
            consent=consent_payload(scopes=["public", "family", "responder"])
        ),
        headers=headers(),
    )
    assert response.status_code == 422
    assert "ámbito público" in " ".join(response.json()["details"])


# --------------------------------------------------------------------------- #
# Art. 4 lit. d — veracidad                                                    #
# --------------------------------------------------------------------------- #


def test_unverified_finding_is_not_disclosed_to_family(client) -> None:
    """Una falsa noticia de hallazgo hace más daño que la ausencia de noticia."""
    record_id = create_record(client, verification="third_party_reported")
    response = client.get(
        f"/v1/hallazgos/{record_id}", headers=headers("dev-family")
    )
    assert response.status_code == 403
    assert "verificado por un respondiente" in " ".join(response.json()["details"])


# --------------------------------------------------------------------------- #
# Art. 7 — interés superior del NNA                                            #
# --------------------------------------------------------------------------- #


def test_minor_is_not_disclosed_to_family_on_a_vital_interest_basis(client) -> None:
    """Entregar la ubicación de un NNA a quien dice ser familia es el riesgo que el
    art. 7 busca evitar. Hace falta representante legal o respaldo de autoridad."""
    record_id = create_record(client, is_minor=True, approximate_age=9)
    response = client.get(
        f"/v1/hallazgos/{record_id}", headers=headers("dev-family")
    )
    assert response.status_code == 403
    assert "NNA" in " ".join(response.json()["details"])


def test_minor_is_disclosed_to_family_with_guardian_consent(client) -> None:
    record_id = create_record(
        client,
        is_minor=True,
        approximate_age=9,
        consent=consent_payload(
            legal_basis="legal_guardian_consent", expires_at=None
        ),
    )
    response = client.get(
        f"/v1/hallazgos/{record_id}", headers=headers("dev-family")
    )
    assert response.status_code == 200
    assert response.json()["is_minor"] is True


def test_minor_is_disclosed_to_family_when_authority_verified(client) -> None:
    """Vía alterna cuando no hay representante legal localizable, que en un desastre
    es el caso frecuente."""
    record_id = create_record(
        client, is_minor=True, approximate_age=9, verification="authority_verified"
    )
    response = client.get(
        f"/v1/hallazgos/{record_id}", headers=headers("dev-family")
    )
    assert response.status_code == 200


# --------------------------------------------------------------------------- #
# §12.3 / ADR-0007 — audit_log antes de responder                              #
# --------------------------------------------------------------------------- #


def test_every_read_is_audited_with_actor_purpose_and_justification(client, container) -> None:
    record_id = create_record(client)
    client.get(f"/v1/hallazgos/{record_id}", headers=headers())

    reads = [e for e in container.audit.entries if e.action == "read"]
    assert len(reads) == 1
    entry = reads[0]
    assert entry.actor == "user:cruz-roja:dev-responder"
    assert entry.purpose.value == "family_reunification"
    assert entry.justification == "Verificación de hallazgo para reunificación familiar."
    assert entry.outcome == "granted"
    assert entry.channel == "http"


def test_denied_reads_are_audited_too(client, container) -> None:
    """Un acceso denegado es exactamente lo que un auditor quiere poder ver."""
    record_id = create_record(client, verification="third_party_reported")
    client.get(f"/v1/hallazgos/{record_id}", headers=headers("dev-family"))

    denied = [e for e in container.audit.entries if e.outcome == "denied"]
    assert len(denied) == 1
    assert denied[0].actor == "user:family:dev-family"


def test_audit_is_written_before_the_response_leaves(client, container) -> None:
    """La escritura precede a la respuesta: si el proceso muere entremedias, no
    puede quedar una divulgación sin rastro."""
    record_id = create_record(client)
    before = len(container.audit.entries)
    response = client.get(f"/v1/hallazgos/{record_id}", headers=headers())
    assert response.status_code == 200
    assert len(container.audit.entries) == before + 1


def test_justification_shorter_than_ten_characters_is_rejected(client) -> None:
    record_id = create_record(client)
    response = client.get(
        f"/v1/hallazgos/{record_id}",
        headers={
            "Authorization": "Bearer dev-responder",
            "X-Purpose": "family_reunification",
            "X-Justification": "porque",
        },
    )
    assert response.status_code == 422


# --------------------------------------------------------------------------- #
# Art. 4 lit. c y d — temporalidad                                             #
# --------------------------------------------------------------------------- #


def test_legal_hold_blocks_erasure_and_explains_why(client) -> None:
    record_id = create_record(
        client,
        retention={
            "legal_hold": True,
            "legal_hold_reason": "Solicitado por la Fiscalía en el radicado 2026-00871.",
        },
    )
    response = client.delete(f"/v1/hallazgos/{record_id}", headers=headers())
    assert response.status_code == 409
    assert response.json()["code"] == "erasure_blocked"
    assert "Fiscalía" in " ".join(response.json()["details"])
    assert response.json()["legal_reference"] == "Decreto 1074 de 2015, art. 2.2.2.25.2.5"


def test_expired_retention_is_anonymized_and_no_longer_disclosed(client, container, clock) -> None:
    record_id = create_record(client)
    clock.advance(31 * DAY_MS)

    anonymized = container.records.sweep_expired_retention()
    assert anonymized == [record_id]

    stored = container.repository.get(record_id)
    assert stored.lifecycle.value == "anonymized"
    assert stored.subject.lookup_token == "", "sin token no se puede volver a buscar"
    assert stored.subject.full_name is None

    response = client.get(f"/v1/hallazgos/{record_id}", headers=headers())
    assert response.status_code == 403
    assert "retención" in " ".join(response.json()["details"])


def test_records_under_legal_hold_survive_the_retention_sweep(client, container, clock) -> None:
    create_record(
        client,
        retention={
            "legal_hold": True,
            "legal_hold_reason": "Actuación administrativa en curso.",
        },
    )
    clock.advance(400 * DAY_MS)
    assert container.records.sweep_expired_retention() == []
