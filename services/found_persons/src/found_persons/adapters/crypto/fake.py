"""*Fakes* criptográficos. Deterministas, legibles y evidentemente inseguros.

Son para tests que no van sobre criptografía: si un test de política tuviera que
generar claves reales, sería lento y su fallo diría poco. Los tests de firma usan
los adaptadores reales de `ed25519.py`.
"""

from __future__ import annotations

import hashlib

from found_persons.application.ports import PayloadSealer, SignatureVerifier, Signer
from found_persons.domain.canonical import b64u


class FakeSigner(Signer):
    def __init__(self, secret: bytes = b"fake-signer") -> None:
        self._secret = secret

    def sign(self, message: bytes) -> str:
        return b64u(hashlib.sha256(self._secret + message).digest())

    def public_key_b64u(self) -> str:
        return b64u(hashlib.sha256(self._secret).digest())


class FakeVerifier(SignatureVerifier):
    """Acepta la firma `sha256(clave_pública_declarada || mensaje)`."""

    def verify(self, message: bytes, signature_b64u: str, public_key_b64u: str) -> bool:
        expected = b64u(
            hashlib.sha256(public_key_b64u.encode("ascii") + message).digest()
        )
        return signature_b64u == expected

    @staticmethod
    def sign_as(public_key_b64u: str, message: bytes) -> str:
        """Produce la firma que este verificador aceptaría para esa clave."""
        return b64u(
            hashlib.sha256(public_key_b64u.encode("ascii") + message).digest()
        )


class NoopSealer(PayloadSealer):
    """No cifra. Marca el resultado para que ningún test lo confunda con lo real."""

    def seal(self, plaintext: bytes, recipient_kex_public_key_b64u: str) -> str:
        return b64u(b"UNSEALED:" + plaintext)
