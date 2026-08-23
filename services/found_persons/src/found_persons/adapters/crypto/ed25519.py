"""Firma y sellado reales.

Las primitivas son las mismas que fija `docs/security/THREAT-MODEL.md`: Ed25519
para identidad y firma, X25519 + HKDF para el acuerdo de clave, ChaCha20-Poly1305
para el contenido. Así una cápsula y un bundle de la malla se validan contra la
misma identidad del teléfono.

`services/shared` declara `pysodium` para lo mismo. Aquí se usa `cryptography`
porque es la que ya está en el entorno y porque el puerto existe justo para que
cambiarla sea tocar este archivo y ninguno más.

Dueño: Miguel. Revisor obligatorio: Helmut.
"""

from __future__ import annotations

import os

from cryptography.exceptions import InvalidSignature as _CryptoInvalidSignature
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey,
    Ed25519PublicKey,
)
from cryptography.hazmat.primitives.asymmetric.x25519 import (
    X25519PrivateKey,
    X25519PublicKey,
)
from cryptography.hazmat.primitives.ciphers.aead import ChaCha20Poly1305
from cryptography.hazmat.primitives.kdf.hkdf import HKDF

from found_persons.application.ports import PayloadSealer, SignatureVerifier, Signer
from found_persons.domain.canonical import b64u, unb64u

_SEAL_INFO = b"sismomesh/found_persons/capsule/v1"


def _raw_public(key) -> bytes:
    return key.public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    )


class Ed25519Signer(Signer):
    """Firma del servicio. La clave privada nunca sale de aquí."""

    def __init__(self, private_key: Ed25519PrivateKey) -> None:
        self._key = private_key

    def sign(self, message: bytes) -> str:
        return b64u(self._key.sign(message))

    def public_key_b64u(self) -> str:
        return b64u(_raw_public(self._key.public_key()))

    @classmethod
    def generate(cls) -> Ed25519Signer:
        """Clave efímera. Válida para desarrollo; en producción viene del KMS, porque
        una clave que cambia en cada reinicio invalida todas las cápsulas emitidas."""
        return cls(Ed25519PrivateKey.generate())

    @classmethod
    def from_seed_hex(cls, seed_hex: str) -> Ed25519Signer:
        return cls(Ed25519PrivateKey.from_private_bytes(bytes.fromhex(seed_hex)))


class Ed25519Verifier(SignatureVerifier):
    """Verificación de lo que firman los dispositivos. Nunca lanza: devuelve `False`.

    Que no lance es deliberado — una firma inválida es un caso de negocio esperado
    (un relay que altera bytes, un teléfono mal configurado), no una excepción.
    """

    def verify(self, message: bytes, signature_b64u: str, public_key_b64u: str) -> bool:
        try:
            public_key = Ed25519PublicKey.from_public_bytes(unb64u(public_key_b64u))
            public_key.verify(unb64u(signature_b64u), message)
        except (_CryptoInvalidSignature, ValueError, TypeError):
            return False
        return True


class X25519Sealer(PayloadSealer):
    """Sella la cápsula hacia la clave del teléfono destinatario.

    Formato: `b64u(pub_efímera(32) || nonce(12) || ciphertext)`. La clave efímera es
    por cápsula, así que dos cápsulas para el mismo teléfono no comparten clave: si
    una se compromete, las demás siguen cerradas.

    El destinatario va en los datos autenticados adicionales, de modo que reetiquetar
    una cápsula para otro teléfono rompe el descifrado además de la firma.
    """

    def seal(self, plaintext: bytes, recipient_kex_public_key_b64u: str) -> str:
        recipient = X25519PublicKey.from_public_bytes(
            unb64u(recipient_kex_public_key_b64u)
        )
        ephemeral = X25519PrivateKey.generate()
        shared = ephemeral.exchange(recipient)
        key = HKDF(
            algorithm=hashes.SHA256(), length=32, salt=None, info=_SEAL_INFO
        ).derive(shared)

        nonce = os.urandom(12)
        ephemeral_pub = _raw_public(ephemeral.public_key())
        ciphertext = ChaCha20Poly1305(key).encrypt(
            nonce, plaintext, recipient_kex_public_key_b64u.encode("ascii")
        )
        return b64u(ephemeral_pub + nonce + ciphertext)


def open_sealed(
    sealed_b64u: str, recipient_private_key: X25519PrivateKey
) -> bytes:
    """Contraparte de `X25519Sealer.seal`. Es lo que hará el teléfono en Kotlin.

    Vive aquí para que el test pueda comprobar que lo sellado se abre — un cifrado
    que nadie verifica que descifre es un cifrado que puede llevar meses roto.
    """
    raw = unb64u(sealed_b64u)
    ephemeral_pub, nonce, ciphertext = raw[:32], raw[32:44], raw[44:]
    shared = recipient_private_key.exchange(X25519PublicKey.from_public_bytes(ephemeral_pub))
    key = HKDF(
        algorithm=hashes.SHA256(), length=32, salt=None, info=_SEAL_INFO
    ).derive(shared)
    aad = b64u(_raw_public(recipient_private_key.public_key())).encode("ascii")
    return ChaCha20Poly1305(key).decrypt(nonce, ciphertext, aad)
