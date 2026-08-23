"""Dependencias de FastAPI: autenticación, finalidad y justificación.

La finalidad y la justificación se piden como cabeceras obligatorias en toda ruta
que toque datos personales. Podrían ir en el cuerpo, pero entonces GET y DELETE
tendrían que resolverlo cada uno a su manera y acabaría habiendo una ruta sin
ellas. Como cabecera es uniforme para los cuatro verbos y no hay forma de olvidarla.

Y no van como parámetro de consulta por una razón concreta: una justificación real
dice cosas como "lo pide el hermano de la persona localizada", y eso es PII. En la
URL acabaría replicada en el log de acceso de cada proxy del camino, que es justo lo
que prohíbe la Definition of Done del proyecto ("sin PII en logs").

Como las cabeceras HTTP no transportan UTF-8 y una justificación en español lleva
tildes, se acepta **percent-encoding** (RFC 3986): `Verificaci%C3%B3n%20de%20hallazgo`.
Un texto ASCII sin codificar atraviesa `unquote` sin cambios, así que el caso simple
no necesita hacer nada especial.
"""

from __future__ import annotations

from typing import Annotated
from urllib.parse import unquote

from fastapi import Depends, Header, HTTPException, Request, status

from found_persons.application.container import Container
from found_persons.application.context import AccessContext, Principal
from found_persons.domain.habeas_data import DisclosureScope, Purpose


def get_container(request: Request) -> Container:
    return request.app.state.container


ContainerDep = Annotated[Container, Depends(get_container)]


def get_principal(
    container: ContainerDep,
    authorization: Annotated[str | None, Header()] = None,
) -> Principal:
    """Resuelve quién pide. En producción esto valida un token del IdP del incidente."""
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "code": "unauthenticated",
                "message": (
                    "Falta la credencial. Ningún dato personal de este servicio es "
                    "accesible de forma anónima (Ley 1581 art. 4 lit. f)."
                ),
            },
            headers={"WWW-Authenticate": "Bearer"},
        )
    token = authorization.split(" ", 1)[1].strip()
    principal = container.tokens.get(token)
    if principal is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "unauthenticated", "message": "Credencial no reconocida."},
            headers={"WWW-Authenticate": "Bearer"},
        )
    return principal


PrincipalDep = Annotated[Principal, Depends(get_principal)]


def get_access_context(
    x_purpose: Annotated[
        Purpose,
        Header(
            description=(
                "Finalidad del acceso. Se contrasta contra las autorizadas en el "
                "registro (Ley 1581 art. 4 lit. b)."
            )
        ),
    ],
    x_justification: Annotated[
        str,
        Header(
            min_length=10,
            max_length=1500,
            description=(
                "Por qué accede. Se guarda literal en audit_log y el Titular puede "
                "leerla (Ley 1581 art. 4 lit. e). Admite percent-encoding UTF-8 para "
                "tildes y eñes: `Verificaci%C3%B3n%20del%20hallazgo`."
            ),
        ),
    ],
) -> AccessContext:
    justification = unquote(x_justification).strip()
    if len(justification) < 10:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "code": "missing_justification",
                "message": (
                    "La justificación debe tener al menos 10 caracteres. Es lo que "
                    "leerá el Titular al ejercer su derecho a ser informado "
                    "(Ley 1581 art. 4 lit. e)."
                ),
            },
        )
    return AccessContext(purpose=x_purpose, justification=justification)


AccessDep = Annotated[AccessContext, Depends(get_access_context)]


def require_authority(principal: PrincipalDep) -> Principal:
    """Restringe una ruta a la autoridad del incidente."""
    if principal.scope is not DisclosureScope.AUTHORITY:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "code": "insufficient_scope",
                "message": (
                    "Esta operación corresponde a la autoridad del incidente "
                    "(Ley 1581 art. 10 lit. a)."
                ),
            },
        )
    return principal


AuthorityDep = Annotated[Principal, Depends(require_authority)]


def require_write_scope(principal: PrincipalDep) -> Principal:
    """Escribir exige acreditación de respondiente o de autoridad.

    Un ámbito familiar puede consultar lo que le corresponde, pero no puede crear ni
    rectificar hallazgos: la veracidad del registro responde ante la autoridad del
    incidente (art. 4 lit. d).
    """
    if principal.scope in (DisclosureScope.PUBLIC, DisclosureScope.FAMILY):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "code": "insufficient_scope",
                "message": (
                    "Solo un respondiente acreditado o la autoridad del incidente "
                    "registran o rectifican hallazgos."
                ),
            },
        )
    return principal


WriteDep = Annotated[Principal, Depends(require_write_scope)]
