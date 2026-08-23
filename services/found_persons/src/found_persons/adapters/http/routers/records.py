"""CRUD de hallazgos: POST, GET, PUT y DELETE.

Los cuatro verbos comparten tres cosas y conviene verlas juntas antes de leer el
código: exigen credencial, exigen cabeceras de finalidad y justificación, y todos
escriben en `audit_log` antes de devolver nada. Lo último ocurre dentro de
`RecordsService`, no aquí, para que ninguna ruta futura pueda saltárselo.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Query, Response, status

from found_persons.adapters.http import mapping
from found_persons.adapters.http import schemas as s
from found_persons.adapters.http.dependencies import (
    AccessDep,
    ContainerDep,
    PrincipalDep,
    WriteDep,
)
from found_persons.domain.records import RecordQuery
from found_persons.domain.vocabulary import SituationStatus

router = APIRouter(prefix="/v1/hallazgos", tags=["hallazgos"])


@router.post(
    "",
    response_model=s.CreatedOut,
    status_code=status.HTTP_201_CREATED,
    summary="Registrar una persona localizada",
    responses={
        403: {"model": s.ErrorOut},
        409: {"model": s.ErrorOut, "description": "Ya existe un registro activo."},
        422: {"model": s.ErrorOut, "description": "Incumple la Ley 1581."},
    },
)
def create_record(
    body: s.RecordIn,
    container: ContainerDep,
    principal: WriteDep,
    access: AccessDep,
) -> s.CreatedOut:
    """Crea el registro.

    El documento se recibe en claro y se convierte de inmediato en token ciego; el
    número se conserva solo si la autorización incluye la categoría de identidad.
    Falla con 422 si el registro resultante no sería legal de conservar —
    por ejemplo, notas de atención bajo una base legal que no habilita datos
    sensibles (art. 6).
    """
    record = container.records.create(
        mapping.new_record_command(body, now_ms=container.clock.now_ms()),
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


@router.get(
    "",
    response_model=s.PageOut,
    summary="Listar hallazgos del incidente",
    responses={403: {"model": s.ErrorOut}},
)
def list_records(
    container: ContainerDep,
    principal: PrincipalDep,
    access: AccessDep,
    incident_id: Annotated[str | None, Query()] = None,
    situation: Annotated[SituationStatus | None, Query()] = None,
    updated_since: Annotated[int | None, Query(description="Epoch ms.")] = None,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> s.PageOut:
    """Listado paginado y minimizado registro por registro.

    No admite filtro por nombre ni por documento a propósito: la única búsqueda por
    persona es por token ciego, y esa vive en la ruta de malla. Un listado con
    búsqueda por texto libre convierte cualquier credencial filtrada en un directorio
    de damnificados.
    """
    page = container.records.list(
        RecordQuery(
            incident_id=incident_id,
            status=situation,
            updated_since=updated_since,
            limit=limit,
            offset=offset,
        ),
        principal=principal,
        context=access,
    )
    return s.PageOut(
        items=[mapping.view_to_dto(v) for v in page.items],
        total=page.total,
        limit=page.limit,
        offset=page.offset,
        withheld_records=page.withheld_records,
    )


@router.get(
    "/{record_id}",
    response_model=s.RecordOut,
    summary="Consultar un hallazgo",
    responses={
        403: {"model": s.ErrorOut},
        404: {"model": s.ErrorOut},
        410: {"model": s.ErrorOut, "description": "Suprimido a petición del Titular."},
    },
)
def get_record(
    record_id: str,
    container: ContainerDep,
    principal: PrincipalDep,
    access: AccessDep,
) -> s.RecordOut:
    """Devuelve solo las categorías que corresponden al ámbito y a la autorización.

    Un 410 no es un error de quien pregunta: significa que el Titular ejerció la
    supresión y que cualquier copia local debe borrarse.
    """
    return mapping.view_to_dto(
        container.records.get(record_id, principal=principal, context=access)
    )


@router.put(
    "/{record_id}",
    response_model=s.CreatedOut,
    summary="Rectificar un hallazgo (reemplazo completo)",
    responses={
        403: {"model": s.ErrorOut},
        404: {"model": s.ErrorOut},
        410: {"model": s.ErrorOut},
        422: {"model": s.ErrorOut},
    },
)
def replace_record(
    record_id: str,
    body: s.RecordIn,
    container: ContainerDep,
    principal: WriteDep,
    access: AccessDep,
) -> s.CreatedOut:
    """Rectificación (art. 8 lit. a). Sube `version` y emite lápida.

    La lápida es lo que hace que las copias ya repartidas por la malla se den por
    obsoletas. Una revocación previa no se deshace por este camino: para volver a
    tratar el dato hace falta una autorización nueva, no una edición.
    """
    record = container.records.replace(
        record_id,
        mapping.replace_record_command(body, now_ms=container.clock.now_ms()),
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


@router.delete(
    "/{record_id}",
    response_model=s.ErasedOut,
    summary="Suprimir un hallazgo (derecho de supresión)",
    responses={
        403: {"model": s.ErrorOut},
        404: {"model": s.ErrorOut},
        409: {
            "model": s.ErrorOut,
            "description": "Hay retención legal y la supresión no procede.",
        },
    },
)
def erase_record(
    record_id: str,
    container: ContainerDep,
    principal: WriteDep,
    access: AccessDep,
    reason: Annotated[
        str,
        Query(
            min_length=5,
            description=(
                "Motivo en texto libre. Se guarda en audit_log y **no** viaja en la "
                "lápida: esta se propaga por la malla y solo lleva un motivo del enum."
            ),
        ),
    ] = "Supresión solicitada por el Titular",
) -> s.ErasedOut:
    """Supresión del art. 8 lit. e.

    No borra la fila: redacta la PII, deja un esqueleto sin datos personales y emite
    una lápida firmada. El esqueleto es necesario porque el `audit_log` tiene que
    seguir apuntando a algo y porque el conteo del incidente no puede cambiar hacia
    atrás; la lápida, porque sin ella las copias que ya viajaron por la malla
    sobrevivirían al derecho ejercido.

    Devuelve 409 si hay retención legal, con el motivo — que es la respuesta que la
    ley exige darle al Titular cuando su solicitud no procede.
    """
    erased = container.records.erase(
        record_id, principal=principal, context=access, reason=reason
    )
    return s.ErasedOut(
        record_id=erased.id,
        lifecycle=erased.lifecycle.value,
        erased_at=erased.erased_at or 0,
        tombstone_emitted=True,
        notice=(
            "Se redactaron los datos personales y se emitió una lápida firmada para "
            "que los dispositivos de la malla eliminen sus copias. El registro de "
            "accesos previos se conserva: es su derecho consultarlo."
        ),
    )


@router.post(
    "/mantenimiento/retencion",
    status_code=status.HTTP_202_ACCEPTED,
    summary="Barrido de retención vencida (uso interno)",
    include_in_schema=False,
)
def sweep_retention(container: ContainerDep, principal: WriteDep) -> Response:
    """Anonimiza lo que venció. Existe como ruta para poder dispararla desde un cron
    externo; la política de temporalidad no puede depender de que alguien se acuerde."""
    touched = container.records.sweep_expired_retention()
    return Response(
        status_code=status.HTTP_202_ACCEPTED,
        content=f'{{"anonymized":{len(touched)}}}',
        media_type="application/json",
    )
