"""Rutas de ejercicio de derechos del Titular (Ley 1581 art. 8, 14 y 15).

Sin estas rutas el servicio sería una base de datos bien minimizada pero
incumplidora: la ley no solo limita lo que se puede hacer con el dato, también
obliga a que el Titular pueda intervenir sobre él.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Body, Query, status

from found_persons.adapters.http import mapping
from found_persons.adapters.http import schemas as s
from found_persons.adapters.http.dependencies import (
    AccessDep,
    ContainerDep,
    PrincipalDep,
    WriteDep,
)

router = APIRouter(tags=["habeas-data"])


@router.get(
    "/v1/hallazgos/{record_id}/accesos",
    response_model=list[s.AuditEntryOut],
    summary="Quién accedió a este registro (art. 8 lit. c)",
    responses={404: {"model": s.ErrorOut}},
)
def access_history(
    record_id: str,
    container: ContainerDep,
    principal: PrincipalDep,
    access: AccessDep,
) -> list[s.AuditEntryOut]:
    """Historial completo de accesos, incluidos los denegados.

    Funciona también sobre registros suprimidos: saber quién vio el dato antes de
    borrarlo sigue siendo derecho del Titular, y es la única forma de que la
    trazabilidad signifique algo para él y no solo para la auditoría.
    """
    entries = container.rights.access_history(
        record_id, principal=principal, context=access
    )
    return [mapping.audit_to_dto(e) for e in entries]


@router.get(
    "/v1/hallazgos/{record_id}/autorizacion",
    response_model=s.ConsentProofOut,
    summary="Prueba de la autorización otorgada (art. 8 lit. b)",
    responses={404: {"model": s.ErrorOut}},
)
def consent_proof(
    record_id: str,
    container: ContainerDep,
    principal: PrincipalDep,
    access: AccessDep,
) -> s.ConsentProofOut:
    """Qué se autorizó, quién lo autorizó y cómo se recogió.

    Cuando la base legal fue una excepción (interés vital, urgencia sanitaria), aquí
    aparece la justificación que se invocó, explicada en lenguaje llano: el deber de
    informar del art. 12 no se cumple citando un artículo.
    """
    proof = container.rights.proof_of_consent(
        record_id, principal=principal, context=access
    )
    return s.ConsentProofOut(
        record_id=proof.record_id,
        legal_basis=proof.legal_basis,
        legal_basis_explained=proof.legal_basis_explained,
        granted_by=proof.granted_by,
        granted_at=proof.granted_at,
        channel=proof.channel,
        purposes=list(proof.purposes),
        categories=list(proof.categories),
        scopes=list(proof.scopes),
        justification=proof.justification,
        evidence_sha256=proof.evidence_sha256,
        evidence_uri=proof.evidence_uri,
        expires_at=proof.expires_at,
        revoked_at=proof.revoked_at,
        controller={
            "name": proof.controller.name,
            "legal_id": proof.controller.legal_id,
            "contact_email": proof.controller.contact_email,
            "rnbd_registration": proof.controller.rnbd_registration,
        },
    )


@router.put(
    "/v1/hallazgos/{record_id}/autorizacion",
    response_model=s.CreatedOut,
    summary="Ajustar la autorización granular",
    responses={404: {"model": s.ErrorOut}, 422: {"model": s.ErrorOut}},
)
def update_consent(
    record_id: str,
    body: s.ConsentIn,
    container: ContainerDep,
    principal: WriteDep,
    access: AccessDep,
) -> s.CreatedOut:
    """Cambia categorías, finalidades y ámbitos autorizados.

    Es el camino normal cuando alguien entró por interés vital y luego recupera la
    capacidad de decidir: ahora dice él mismo qué autoriza. Si la autorización ya
    fue revocada, esta ruta falla — volver a tratar el dato exige una autorización
    nueva, no la edición de la anterior (art. 9).
    """
    record = container.rights.update_consent(
        record_id,
        mapping.consent_from_dto(body, now_ms=container.clock.now_ms()),
        principal=principal,
        context=access,
    )
    return s.CreatedOut(
        record_id=record.id,
        version=record.version,
        lifecycle=record.lifecycle.value,
        retention_until=record.retention.erase_after_ms,
        legal_basis=record.consent.legal_basis,
    )


@router.post(
    "/v1/hallazgos/{record_id}/revocacion",
    response_model=s.CreatedOut,
    summary="Revocar la autorización (art. 8 lit. e)",
    responses={404: {"model": s.ErrorOut}},
)
def revoke_consent(
    record_id: str,
    body: s.RevocationIn,
    container: ContainerDep,
    principal: PrincipalDep,
    access: AccessDep,
) -> s.CreatedOut:
    """Revoca la autorización. Ninguna consulta posterior vuelve a obtener el dato.

    Revocar no es suprimir: el registro sigue existiendo por si hay deberes de
    conservación, pero deja de ser divulgable de inmediato y se emite lápida para
    invalidar las copias que ya salieron por la malla. Para eliminar el contenido,
    use DELETE sobre el hallazgo.
    """
    record = container.rights.revoke_consent(
        record_id, reason=body.reason, principal=principal, context=access
    )
    return s.CreatedOut(
        record_id=record.id,
        version=record.version,
        lifecycle=record.lifecycle.value,
        retention_until=record.retention.erase_after_ms,
        legal_basis=record.consent.legal_basis,
    )


@router.post(
    "/v1/habeas-data/peticiones",
    response_model=s.ClaimOut,
    status_code=status.HTTP_201_CREATED,
    summary="Radicar una consulta (art. 14) o un reclamo (art. 15)",
)
def file_claim(body: s.ClaimIn, container: ContainerDep) -> s.ClaimOut:
    """Radica la petición y fija su vencimiento en días hábiles.

    Sin autenticación a propósito: quien reclama puede ser precisamente alguien que
    no tiene credenciales y descubrió que sus datos están aquí. El plazo se calcula
    al radicar porque vencerlo es un incumplimiento con consecuencias, no un retraso
    de servicio.
    """
    claim = container.rights.file_claim(
        kind=body.kind,
        record_id=body.record_id,
        subject_matter=body.subject_matter,
        body=body.body,
        filed_by=body.filed_by,
        channel=body.channel,
    )
    return mapping.claim_to_dto(claim)


@router.get(
    "/v1/habeas-data/peticiones/{claim_id}",
    response_model=s.ClaimOut,
    summary="Estado de una petición",
    responses={404: {"model": s.ErrorOut}},
)
def get_claim(claim_id: str, container: ContainerDep) -> s.ClaimOut:
    from found_persons.domain.errors import RecordNotFound

    claim = container.claims.get(claim_id)
    if claim is None:
        raise RecordNotFound(f"No existe la petición '{claim_id}'.")
    return mapping.claim_to_dto(claim)


@router.post(
    "/v1/habeas-data/peticiones/{claim_id}/prorroga",
    response_model=s.ClaimOut,
    summary="Prorrogar el término, informando los motivos",
    responses={404: {"model": s.ErrorOut}, 422: {"model": s.ErrorOut}},
)
def extend_claim(
    claim_id: str,
    container: ContainerDep,
    principal: WriteDep,
    motive: Annotated[str, Body(embed=True, min_length=10)],
) -> s.ClaimOut:
    """La prórroga solo vale si se informa antes del vencimiento y con motivos."""
    return mapping.claim_to_dto(container.rights.extend_claim(claim_id, motive=motive))


@router.post(
    "/v1/habeas-data/peticiones/{claim_id}/respuesta",
    response_model=s.ClaimOut,
    summary="Responder de fondo una petición",
    responses={404: {"model": s.ErrorOut}},
)
def answer_claim(
    claim_id: str,
    container: ContainerDep,
    principal: WriteDep,
    resolution: Annotated[str, Body(embed=True, min_length=10)],
    accepted: Annotated[bool, Body(embed=True)] = True,
) -> s.ClaimOut:
    return mapping.claim_to_dto(
        container.rights.answer_claim(
            claim_id, resolution=resolution, accepted=accepted
        )
    )


@router.get(
    "/v1/habeas-data/peticiones-vencidas",
    response_model=list[s.ClaimOut],
    summary="Peticiones con el término vencido",
)
def overdue_claims(container: ContainerDep, principal: WriteDep) -> list[s.ClaimOut]:
    """Alarma operativa. Que se venza un término no es un atraso: es incumplir la ley."""
    return [mapping.claim_to_dto(c) for c in container.rights.overdue_claims()]


@router.get(
    "/v1/habeas-data/aviso-de-privacidad",
    summary="Aviso de privacidad (Decreto 1074 art. 2.2.2.25.3.2)",
)
def privacy_notice(container: ContainerDep) -> dict:
    """Público y sin credencial.

    Tiene que poder mostrárselo a alguien cuyos datos se recogieron cuando no estaba
    en condiciones de leer nada. Exigir autenticación para leer el aviso de
    privacidad sería contradictorio con su propósito.
    """
    return container.rights.privacy_notice(container.controller)


@router.get(
    "/v1/habeas-data/token-de-busqueda",
    summary="Calcular el token ciego de un documento (uso acreditado)",
)
def compute_lookup_token(
    container: ContainerDep,
    principal: WriteDep,
    incident_id: Annotated[str, Query()],
    document_type: Annotated[str, Query()],
    document_number: Annotated[str, Query()],
) -> dict:
    """Devuelve el token con el que se consulta por esa persona.

    Existe porque un dispositivo necesita construir el token y la clave del incidente
    no se le entrega completa. Requiere acreditación de escritura: quien puede
    calcular tokens puede comprobar si un documento está registrado, así que este
    acceso está tan restringido como el propio dato.
    """
    from found_persons.domain.records import blinded_lookup_token

    return {
        "incident_id": incident_id,
        "lookup_token": blinded_lookup_token(
            incident_key=container.incident_keys.key_for(incident_id),
            document_type=document_type,
            document_number=document_number,
        ),
        "notice": (
            "El token es específico de este incidente. No sirve para correlacionar a "
            "la misma persona en otro desastre."
        ),
    }
