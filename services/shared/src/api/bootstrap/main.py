"""Punto de entrada FastAPI — wiring de adaptadores reales (Sección 12.1).

Dueño: Miguel.
"""

from fastapi import FastAPI

app = FastAPI(title="SismoMesh Cloud API", version="0.1.0")


@app.get("/health")
async def health() -> dict:
    return {"status": "ok"}


# TODO(dueño=Miguel): registrar routers de protocol/openapi/sismomesh-api.yaml,
# inyectar adaptadores reales (Postgres/PostGIS, Redis, S3), middleware de audit_log.
