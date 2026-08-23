"""Optional model registry; never part of the urgent measurement path.

Integrado desde el blueprint de Laura (docs/ppg/README.md). Distribuye
`ppg_tiny_tcn_int8.tflite` aprobados a la app; Android siempre conserva una
versión funcional empacada (HeuristicFallback / SafetyFirstClassifier en
core/signal/ppg si este servicio no está disponible).
"""
from __future__ import annotations

import hashlib
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel

app = FastAPI(title="SismoMesh PPG Model Registry", version="1.0.0")
MODEL_DIR = Path(__file__).resolve().parent.parent / "models"


class ModelManifest(BaseModel):
    version: str
    status: str
    preprocessor: str
    sha256: str
    bytes: int


def manifest_for(version: str) -> ModelManifest:
    model = MODEL_DIR / version / "ppg_tiny_tcn_int8.tflite"
    approved = MODEL_DIR / version / "APPROVED"
    if not model.is_file() or not approved.is_file():
        raise HTTPException(404, "Approved model not found")
    blob = model.read_bytes()
    return ModelManifest(
        version=version,
        status="approved",
        preprocessor="ppg-pre-v1",
        sha256=hashlib.sha256(blob).hexdigest(),
        bytes=len(blob),
    )


@app.get("/v1/ppg/models/{version}/manifest", response_model=ModelManifest)
def get_manifest(version: str):
    return manifest_for(version)


@app.get("/v1/ppg/models/{version}")
def get_model(version: str):
    manifest_for(version)
    return FileResponse(MODEL_DIR / version / "ppg_tiny_tcn_int8.tflite", media_type="application/octet-stream")


@app.get("/health")
def health():
    return {"status": "ok"}
