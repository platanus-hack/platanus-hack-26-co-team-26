"""Generadores de identificador de incidente."""

from __future__ import annotations

import secrets

from alert_ingestor.application.ports import IdGenerator


class SecureIdGenerator(IdGenerator):
    def new_id(self) -> str:
        return f"seismic_{secrets.token_hex(10)}"


class SequentialIdGenerator(IdGenerator):
    """*Fake* determinista para tests: `seismic_000001`, `seismic_000002`, ..."""

    def __init__(self) -> None:
        self._n = 0

    def new_id(self) -> str:
        self._n += 1
        return f"seismic_{self._n:06d}"
