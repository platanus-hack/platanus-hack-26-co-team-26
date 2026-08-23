"""Claves HMAC por incidente para el token ciego de búsqueda.

En producción la clave maestra vive en el gestor de secretos y la del incidente se
deriva con HKDF; nunca se guarda una clave por incidente en base de datos, porque
quien la tenga puede construir tokens para documentos que adivine y comprobar si
existen. La derivación es determinista para que dos réplicas del servicio calculen
el mismo token.
"""

from __future__ import annotations

import hashlib
import hmac
import os

from found_persons.application.ports import IncidentKeyProvider

_HKDF_INFO = b"helius/found_persons/lookup-token/v1"


class DerivedIncidentKeyProvider(IncidentKeyProvider):
    """HKDF-Expand sobre una clave maestra. Adaptador real."""

    def __init__(self, master_key: bytes) -> None:
        if len(master_key) < 32:
            raise ValueError(
                "La clave maestra debe tener al menos 32 bytes: de ella depende que "
                "el token de búsqueda no sea reversible por fuerza bruta."
            )
        self._master = master_key

    def key_for(self, incident_id: str) -> bytes:
        return hmac.new(
            self._master,
            _HKDF_INFO + b"\x00" + incident_id.encode("utf-8"),
            hashlib.sha256,
        ).digest()

    @classmethod
    def from_env(cls, var: str = "FOUND_PERSONS_MASTER_KEY") -> DerivedIncidentKeyProvider:
        raw = os.environ.get(var)
        if not raw:
            raise RuntimeError(
                f"Falta {var}. Sin clave maestra el token de búsqueda sería "
                "predecible y cualquiera podría comprobar si un documento está "
                "registrado."
            )
        return cls(bytes.fromhex(raw) if len(raw) == 64 else raw.encode("utf-8"))


class StaticIncidentKeyProvider(IncidentKeyProvider):
    """*Fake* determinista para tests y para el arranque de demostración."""

    def __init__(self, key: bytes = b"clave-de-desarrollo-no-usar-en-produccion") -> None:
        self._key = key

    def key_for(self, incident_id: str) -> bytes:
        return hashlib.sha256(self._key + incident_id.encode("utf-8")).digest()
