#!/usr/bin/env python3
"""Verificador de referencia de EmergencyBundle v1.

Regla central: se verifica sobre los BYTES RECIBIDOS. Nunca se re-serializa
el payload, por eso Dart y Python nunca discrepan por el formato de un float.
"""
import base64, hashlib, json, sys

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
from cryptography.exceptions import InvalidSignature

VALID_STATUS = {"SAFE", "HELP", "TRAPPED", "UNCONFIRMED"}   # DEAD no existe. A proposito.


class Rejected(Exception):
    pass


def pseudonym(pub_raw: bytes) -> str:
    return base64.urlsafe_b64encode(hashlib.sha256(pub_raw).digest()[:12]).decode().rstrip("=")


def verify(envelope: dict) -> dict:
    """Devuelve el payload parseado o lanza Rejected.

    El bundle es AUTO-VERIFICABLE: trae su propia clave publica, y el
    signer_key_id debe ser el hash de esa clave. Nadie necesita un registro
    de claves previo -- ni el relay, ni el gateway, ni el backend.
    """
    if envelope.get("v") != 1:
        raise Rejected(f"version no soportada: {envelope.get('v')}")

    pubkey_raw = base64.b64decode(envelope["signer_pubkey_b64"])
    if pseudonym(pubkey_raw) != envelope["signer_key_id"]:
        raise Rejected("signer_key_id no corresponde a signer_pubkey_b64")

    raw = base64.b64decode(envelope["payload_b64"])       # bytes tal como llegaron

    if hashlib.sha256(raw).hexdigest() != envelope["payload_hash"]:
        raise Rejected("payload_hash no coincide")

    try:
        Ed25519PublicKey.from_public_bytes(pubkey_raw).verify(
            base64.b64decode(envelope["signature"]), raw)
    except InvalidSignature:
        raise Rejected("firma invalida")

    payload = json.loads(raw)
    if payload.get("status") not in VALID_STATUS:
        raise Rejected(f"status invalido: {payload.get('status')}")
    return payload


def main():
    import os
    d = os.path.join(os.path.dirname(__file__), "..", "fixtures")
    expect = {
        "bundle-valid.json": True,
        "bundle-duplicate.json": True,       # duplicado es valido; lo filtra el store, no la cripto
        "bundle-with-evidence.json": True,
        "bundle-expired.json": True,         # TTL es politica del store, no integridad
        "bundle-tampered.json": False,
        "bundle-forged-key.json": False,     # clave publica cambiada -> key_id ya no cuadra
    }
    fail = 0
    for name, should_pass in expect.items():
        env = json.load(open(os.path.join(d, name)))
        try:
            verify(env)
            ok, detail = True, "aceptado"
        except Rejected as e:
            ok, detail = False, f"rechazado: {e}"
        mark = "PASS" if ok == should_pass else "FAIL"
        if mark == "FAIL":
            fail += 1
        print(f"  [{mark}] {name:32} {detail}")
    print("\nTodo correcto." if not fail else f"\n{fail} caso(s) fuera de lo esperado.")
    return 1 if fail else 0


if __name__ == "__main__":
    sys.exit(main())
