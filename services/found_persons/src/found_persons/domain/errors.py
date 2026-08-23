"""Errores del dominio. La capa HTTP los traduce a códigos; el dominio no los conoce."""

from __future__ import annotations


class DomainError(Exception):
    """Base. Todo error del dominio lleva un motivo legible por una persona."""

    code = "domain_error"

    def __init__(self, message: str, *, details: list[str] | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.details = details or []


class RecordNotFound(DomainError):
    code = "record_not_found"


class RecordErased(DomainError):
    """El registro existió y fue suprimido. Se distingue de "no existe" a propósito:
    quien tenía una copia por malla necesita saber que debe borrarla."""

    code = "record_erased"


class HabeasDataViolation(DomainError):
    """El Tratamiento pedido no está habilitado por la Ley 1581. Nunca se degrada
    silenciosamente a una respuesta parcial: se niega y se audita."""

    code = "habeas_data_violation"


class ErasureBlocked(DomainError):
    """Hay retención legal. La supresión no procede y hay que decir por qué."""

    code = "erasure_blocked"


class UnknownDevice(DomainError):
    code = "unknown_device"


class InvalidSignature(DomainError):
    code = "invalid_signature"


class ReplayedRequest(DomainError):
    """Nonce repetido o consulta caducada. Impide reusar una consulta firmada."""

    code = "replayed_request"


class DeviceQuotaExceeded(DomainError):
    """Un dispositivo pidiendo demasiado es lo que parece: alguien recolectando.
    El límite de tasa es una medida de seguridad exigida por el art. 4 lit. g."""

    code = "device_quota_exceeded"


class DisclosureDenied(HabeasDataViolation):
    """El registro existe y es válido, pero este solicitante no puede verlo.

    Se separa de `HabeasDataViolation` porque significan cosas distintas para quien
    llama: aquella dice "lo que pides es ilegal de guardar", esta dice "es legal
    pero no te corresponde". La primera es 422; la segunda, 403.
    """

    code = "disclosure_denied"


class RecordAlreadyExists(HabeasDataViolation):
    """Ya hay un registro activo para esa persona en el incidente."""

    code = "record_already_exists"
