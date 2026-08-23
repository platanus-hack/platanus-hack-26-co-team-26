"""Generadores de identificadores.

El real usa `secrets`: un id correlativo filtraría cuánta gente hay registrada y en
qué orden apareció, que en un desastre es información sensible por sí sola.
"""

from __future__ import annotations

import secrets

from found_persons.application.ports import IdGenerator


class SecureIdGenerator(IdGenerator):
    def new_id(self, prefix: str) -> str:
        return f"{prefix}_{secrets.token_hex(12)}"

    def new_nonce(self) -> str:
        return secrets.token_hex(16)


class SequentialIdGenerator(IdGenerator):
    """*Fake* determinista. Solo para tests: no usar jamás en un despliegue."""

    def __init__(self) -> None:
        self._counters: dict[str, int] = {}
        self._nonce = 0

    def new_id(self, prefix: str) -> str:
        self._counters[prefix] = self._counters.get(prefix, 0) + 1
        return f"{prefix}_{self._counters[prefix]:06d}"

    def new_nonce(self) -> str:
        self._nonce += 1
        return f"nonce_{self._nonce:06d}"
