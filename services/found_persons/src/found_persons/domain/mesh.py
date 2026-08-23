"""Divulgación entre dispositivos — el caso de uso propio de una malla DTN.

El problema: un teléfono en la zona quiere saber si hay novedad de una persona, y
la respuesta puede tener que atravesar otros teléfonos antes de llegarle. Eso choca
de frente con el principio de acceso restringido si se resuelve ingenuamente.

Tres piezas lo hacen compatible con la Ley 1581:

1. **Consulta firmada con token ciego.** El dispositivo pregunta por
   `HMAC(clave_incidente, documento)`, no por un nombre. Solo puede preguntar por
   alguien cuyo documento ya conoce: no hay enumeración ni pesca de datos.
2. **Cápsula minimizada, sellada y con caducidad.** La respuesta se recorta al
   ámbito del dispositivo, se cifra hacia su clave y lleva fecha de muerte. Los
   relays intermedios transportan bytes opacos, tal como exige
   `docs/security/THREAT-MODEL.md`.
3. **Lápidas.** Si el Titular revoca o suprime, la lápida viaja por la misma malla
   y las copias caducan antes de tiempo. Sin esto, la supresión sería una promesa
   que no se puede cumplir fuera del servidor.

Dueño: Miguel (API). Revisor obligatorio: Helmut (transporte, DTN y sellado).
"""

from __future__ import annotations

from dataclasses import dataclass

from found_persons.domain.canonical import canonical_bytes
from found_persons.domain.habeas_data import DisclosureScope, Purpose


@dataclass(frozen=True, slots=True)
class DeviceIdentity:
    """Dispositivo acreditado para consultar. Su ámbito decide cuánto puede recibir.

    La identidad es la clave Ed25519 de la instalación, la misma que firma los
    bundles (`docs/security/THREAT-MODEL.md` § Criptografía). Aquí solo se le añade
    la acreditación: quién respondió por este teléfono y hasta cuándo.
    """

    device_id: str
    incident_id: str
    signing_public_key: str
    """Ed25519 en base64url. Verifica las consultas que firma el dispositivo."""

    scope: DisclosureScope
    accredited_by: str
    """Autoridad del incidente que lo acreditó. Es quien responde por el acceso."""

    accredited_at: int
    kex_public_key: str | None = None
    """X25519 en base64url. Si está, la cápsula viaja cifrada hacia este teléfono."""

    organization: str | None = None
    holder_ref: str | None = None
    """A quién pertenece. Para poder revocar por persona, no solo por aparato."""

    expires_at: int | None = None
    """Acreditación con caducidad: el incidente termina, el acceso también."""

    revoked_at: int | None = None
    revocation_reason: str | None = None

    def is_active(self, now_ms: int) -> bool:
        if self.revoked_at is not None and self.revoked_at <= now_ms:
            return False
        return not (self.expires_at is not None and self.expires_at <= now_ms)


@dataclass(frozen=True, slots=True)
class DeviceQuery:
    """Consulta firmada de dispositivo a servicio.

    Lleva `nonce` y `expires_at` porque una consulta firmada que viaja por malla es
    reutilizable por definición: sin ventana ni nonce, cualquier relay podría
    repetirla indefinidamente en nombre de otro.
    """

    device_id: str
    incident_id: str
    lookup_token: str
    """Token ciego. Ver `records.blinded_lookup_token`."""

    purpose: Purpose
    justification: str
    """Va literal al `audit_log`. El Titular tiene derecho a leerla (art. 4 lit. e)."""

    nonce: str
    issued_at: int
    expires_at: int
    signature: str = ""

    def signing_payload(self) -> dict:
        """Lo que se firma. Excluye la firma, obviamente, e incluye la finalidad:
        firmar solo el token permitiría reciclar la consulta con otro propósito."""
        return {
            "typ": "found_persons.device_query.v1",
            "device_id": self.device_id,
            "incident_id": self.incident_id,
            "lookup_token": self.lookup_token,
            "purpose": self.purpose.value,
            "justification": self.justification,
            "nonce": self.nonce,
            "issued_at": self.issued_at,
            "expires_at": self.expires_at,
        }

    def signing_bytes(self) -> bytes:
        return canonical_bytes(self.signing_payload())


@dataclass(frozen=True, slots=True)
class DisclosureCapsule:
    """Respuesta autocontenida, firmada y con caducidad. La unidad que viaja por malla.

    Autocontenida porque quien la recibe puede estar a varios saltos del servicio y
    no tener forma de volver a preguntar. Firmada porque los saltos intermedios no
    son de confianza. Caducada porque un dato de emergencia que sobrevive a la
    emergencia deja de ser proporcionado (art. 4 lit. c).
    """

    capsule_id: str
    incident_id: str
    audience_device_id: str
    """Único destinatario legítimo. Un relay que la abra no encontrará nada legible
    si `payload_encrypted`; si la reenvía a otro, la firma delata el destinatario."""

    scope: DisclosureScope
    purpose: Purpose
    outcome: str
    """`granted` | `denied` | `not_found` | `erased`."""

    issued_at: int
    expires_at: int
    """Después de esto el dispositivo debe borrarla. Va dentro de la firma."""

    payload: str
    """Vista minimizada. Base64url del texto cifrado si `payload_encrypted`, o del
    JSON canónico en claro cuando el dispositivo no publicó clave X25519."""

    payload_encrypted: bool
    record_id: str | None = None
    record_version: int | None = None
    """Permite a un teléfono descartar una copia vieja recibida por otra ruta."""

    reasons: tuple[str, ...] = ()
    """Por qué se negó o qué se recortó. Se responde igual: negar en silencio impide
    al solicitante saber si debe insistir por otra vía."""

    audit_id: str = ""
    """Asiento de `audit_log` correspondiente. El Titular puede rastrear con esto."""

    max_hops: int = 4
    """Presupuesto de reenvío. Cuanto más sensible, menos lejos debería llegar."""

    retransmit_allowed: bool = True
    """`False` para lo que no debe salir del dispositivo que preguntó."""

    signature: str = ""
    """Ed25519 del servicio. Es lo que permite confiar en la cápsula sin confiar
    en el teléfono que la entregó."""

    def signing_payload(self) -> dict:
        return {
            "typ": "found_persons.capsule.v1",
            "capsule_id": self.capsule_id,
            "incident_id": self.incident_id,
            "audience_device_id": self.audience_device_id,
            "scope": self.scope.value,
            "purpose": self.purpose.value,
            "outcome": self.outcome,
            "issued_at": self.issued_at,
            "expires_at": self.expires_at,
            "payload": self.payload,
            "payload_encrypted": self.payload_encrypted,
            "record_id": self.record_id,
            "record_version": self.record_version,
            "reasons": list(self.reasons),
            "audit_id": self.audit_id,
            "max_hops": self.max_hops,
            "retransmit_allowed": self.retransmit_allowed,
        }

    def signing_bytes(self) -> bytes:
        return canonical_bytes(self.signing_payload())

    def is_fresh(self, now_ms: int) -> bool:
        return self.issued_at <= now_ms < self.expires_at
