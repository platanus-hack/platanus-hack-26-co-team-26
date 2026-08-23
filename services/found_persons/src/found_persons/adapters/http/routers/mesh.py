"""Rutas de divulgación entre dispositivos.

Estas rutas son las que un teléfono llama cuando alcanza un gateway. No usan la
credencial bearer: el dispositivo se autentica firmando la propia consulta con su
identidad Ed25519, la misma con la que firma los bundles de la malla. Así una
consulta que viaja varios saltos sigue siendo verificable al llegar, y un relay que
la manipule invalida la firma.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Query, status

from found_persons.adapters.http import mapping
from found_persons.adapters.http import schemas as s
from found_persons.adapters.http.dependencies import AuthorityDep, ContainerDep
from found_persons.application.mesh import DeviceRegistration

router = APIRouter(prefix="/v1/malla", tags=["malla"])


@router.post(
    "/dispositivos",
    response_model=s.DeviceOut,
    status_code=status.HTTP_201_CREATED,
    summary="Acreditar un dispositivo para consultar por malla",
    responses={403: {"model": s.ErrorOut}},
)
def register_device(
    body: s.DeviceRegistrationIn,
    container: ContainerDep,
    principal: AuthorityDep,
) -> s.DeviceOut:
    """Acredita un teléfono con un ámbito concreto.

    Solo la autoridad del incidente puede hacerlo, y no puede otorgar ámbito
    AUTHORITY a un móvil: un teléfono extraviado no debe llevar consigo el acceso
    total al incidente.

    Si el dispositivo publica `kex_public_key`, sus cápsulas viajarán cifradas hacia
    esa clave y podrán atravesar relays. Si no, se entregan en claro y con el
    reenvío prohibido.
    """
    device = container.mesh.register_device(
        DeviceRegistration(
            device_id=body.device_id,
            incident_id=body.incident_id,
            signing_public_key=body.signing_public_key,
            scope=body.scope,
            kex_public_key=body.kex_public_key,
            organization=body.organization,
            holder_ref=body.holder_ref,
            expires_at=body.expires_at,
        ),
        principal=principal,
    )
    return mapping.device_to_dto(device)


@router.delete(
    "/dispositivos/{device_id}",
    response_model=s.DeviceOut,
    summary="Revocar la acreditación de un dispositivo",
    responses={403: {"model": s.ErrorOut}, 404: {"model": s.ErrorOut}},
)
def revoke_device(
    device_id: str,
    container: ContainerDep,
    principal: AuthorityDep,
    reason: Annotated[str, Query(min_length=5)] = "device_lost",
) -> s.DeviceOut:
    """Retira la acreditación: teléfono perdido, turno terminado, incidente cerrado."""
    return mapping.device_to_dto(
        container.mesh.revoke_device(device_id, reason=reason, principal=principal)
    )


@router.post(
    "/consultas",
    response_model=s.CapsuleOut,
    summary="Consultar por token ciego y recibir una cápsula firmada",
    responses={
        401: {"model": s.ErrorOut, "description": "Dispositivo no acreditado o firma inválida."},
        409: {"model": s.ErrorOut, "description": "Nonce repetido o consulta caducada."},
        429: {"model": s.ErrorOut, "description": "Límite de consultas por hora."},
    },
)
def query_by_token(body: s.DeviceQueryIn, container: ContainerDep) -> s.CapsuleOut:
    """El método de dispositivo a dispositivo.

    El dispositivo pregunta por `HMAC(clave_del_incidente, documento)` — nunca por un
    nombre —, así que solo puede preguntar por alguien cuyo documento ya conoce. La
    respuesta es una cápsula autocontenida, minimizada según el ámbito acreditado,
    cifrada hacia la clave del teléfono y con fecha de caducidad, firmada por el
    servicio para que los saltos intermedios no puedan alterarla.

    Para los ámbitos `public` y `family` la respuesta negativa es siempre la misma
    (`no_disclosure`) exista o no el registro: si se distinguieran, esta ruta sería
    un oráculo que permite averiguar con un documento ajeno si esa persona está en
    el sistema.
    """
    return mapping.capsule_to_dto(container.mesh.answer(mapping.query_from_dto(body)))


@router.post(
    "/capsulas/verificar",
    response_model=s.CapsuleVerdictOut,
    summary="Revalidar una cápsula recibida por la malla",
)
def verify_capsule(
    body: s.CapsuleVerifyIn, container: ContainerDep
) -> s.CapsuleVerdictOut:
    """Comprueba firma, vigencia y si el dato quedó suprimido o rectificado.

    Un teléfono puede verificar la firma por su cuenta; lo que no puede saber
    estando aislado es si el Titular revocó o rectificó después. Esta es la primera
    llamada que debería hacer al recuperar conectividad, antes de mostrarle nada a
    nadie.
    """
    verdict = container.mesh.verify_capsule(mapping.capsule_from_dto(body.capsule))
    return s.CapsuleVerdictOut(
        signature_valid=verdict.signature_valid,
        fresh=verdict.fresh,
        superseded=verdict.superseded,
        must_delete=verdict.must_delete,
        reasons=list(verdict.reasons),
        current_tombstone_sequence=verdict.current_tombstone_sequence,
    )


@router.get(
    "/lapidas",
    response_model=s.TombstonePageOut,
    summary="Lápidas de supresión para propagar por la malla",
)
def tombstones(
    container: ContainerDep,
    incident_id: Annotated[str, Query()],
    since_sequence: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=500)] = 200,
) -> s.TombstonePageOut:
    """Supresiones y revocaciones posteriores a una secuencia.

    Es la contrapartida honesta del derecho de supresión: sin este canal, borrar en
    el servidor no alcanzaría a los teléfonos que ya tienen copia. No lleva PII —
    solo identificadores y motivo —, así que un dispositivo que nunca recibió una
    cápsula de ese registro no aprende nada al leerla.
    """
    items = container.mesh.tombstones_since(
        incident_id, sequence=since_sequence, limit=limit
    )
    return s.TombstonePageOut(
        items=[mapping.tombstone_to_dto(t) for t in items],
        next_sequence=items[-1].sequence if items else since_sequence,
        service_public_key=container.signer.public_key_b64u(),
    )
