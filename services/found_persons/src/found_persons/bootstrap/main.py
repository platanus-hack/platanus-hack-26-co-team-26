"""Fábrica de la aplicación FastAPI.

Un solo sitio decide qué código HTTP corresponde a cada error del dominio. El
dominio no importa `fastapi` (regla de `.importlinter`) y por eso lanza excepciones
propias; la traducción vive aquí, en el borde.

Arranque local:

    uvicorn found_persons.bootstrap.main:app --reload --port 8010
"""

from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from found_persons.adapters.http.routers import mesh, records, rights
from found_persons.bootstrap.container import Container, build_container
from found_persons.domain import errors as domain_errors

#: Error del dominio → código HTTP → referencia legal que se devuelve al cliente.
#: Que la referencia viaje en la respuesta no es adorno: quien recibe un 403 tiene
#: derecho a saber en qué se funda la negativa.
ERROR_MAP: dict[type[Exception], tuple[int, str | None]] = {
    domain_errors.RecordNotFound: (404, None),
    domain_errors.RecordErased: (410, "Ley 1581 de 2012, art. 8 lit. e"),
    domain_errors.RecordAlreadyExists: (409, "Ley 1581 de 2012, art. 4 lit. d"),
    domain_errors.DisclosureDenied: (403, "Ley 1581 de 2012, art. 4 lit. f"),
    domain_errors.ErasureBlocked: (409, "Decreto 1074 de 2015, art. 2.2.2.25.2.5"),
    domain_errors.HabeasDataViolation: (422, "Ley 1581 de 2012, art. 4 y 6"),
    domain_errors.UnknownDevice: (401, None),
    domain_errors.InvalidSignature: (401, None),
    domain_errors.ReplayedRequest: (409, None),
    domain_errors.DeviceQuotaExceeded: (429, "Ley 1581 de 2012, art. 4 lit. g"),
}

DESCRIPTION = """
API de personas localizadas de HELIUS.

Registra que una persona reportada como no localizada fue **ubicada**, y permite
consultarlo desde otros dispositivos de la malla bajo el régimen colombiano de
protección de datos personales (Constitución art. 15, Ley 1581 de 2012, Decreto
1074 de 2015).

**Cómo leer esta API antes de usarla:**

* Todo endpoint que toca datos personales exige las cabeceras `X-Purpose` y
  `X-Justification`, y escribe en `audit_log` **antes** de responder.
* Lo que se devuelve está minimizado según el ámbito del solicitante
  (`public` < `family` < `responder` < `authority`, ver ADR-0007) intersecado con
  lo que el Titular autorizó. Lo que se recorta se declara en `withheld_categories`.
* La búsqueda por persona es siempre por **token ciego**
  `HMAC(clave_del_incidente, documento)`. No existe búsqueda por nombre.
* `DELETE` no borra la fila: redacta los datos personales y emite una **lápida**
  firmada para que los teléfonos de la malla eliminen sus copias.
* El Titular puede consultar quién accedió a su dato, pedir prueba de la
  autorización, revocarla y radicar reclamos con plazos legales.

Este servicio no evalúa clínicamente a nadie ni declara el estado vital de ninguna
persona — ver `docs/glossary.md`.
"""


def create_app(container: Container | None = None) -> FastAPI:
    """Construye la app. Recibe el contenedor para que los tests inyecten *fakes*."""
    app = FastAPI(
        title="HELIUS — API de personas localizadas",
        version="0.1.0",
        description=DESCRIPTION,
        openapi_tags=[
            {"name": "hallazgos", "description": "Ciclo de vida del registro."},
            {"name": "malla", "description": "Divulgación entre dispositivos."},
            {
                "name": "habeas-data",
                "description": "Derechos del Titular: acceso, prueba, revocación, reclamos.",
            },
        ],
    )
    app.state.container = container or build_container()

    app.include_router(records.router)
    app.include_router(mesh.router)
    app.include_router(rights.router)

    @app.exception_handler(domain_errors.DomainError)
    async def handle_domain_error(
        _: Request, exc: domain_errors.DomainError
    ) -> JSONResponse:
        # Se recorre el MRO para que una subclase herede el mapeo de su padre sin
        # tener que declararlo, pero una subclase con mapeo propio gane.
        for klass in type(exc).__mro__:
            if klass in ERROR_MAP:
                status_code, legal_reference = ERROR_MAP[klass]
                break
        else:
            status_code, legal_reference = 400, None

        return JSONResponse(
            status_code=status_code,
            content={
                "code": exc.code,
                "message": exc.message,
                "details": exc.details,
                "legal_reference": legal_reference,
            },
        )

    @app.get("/health", tags=["operación"], summary="Salud del servicio")
    async def health() -> dict:
        return {
            "status": "ok",
            "service": "found_persons",
            "signing_public_key": app.state.container.signer.public_key_b64u(),
        }

    return app


app = create_app()
