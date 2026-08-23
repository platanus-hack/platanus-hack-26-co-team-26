"""Quién pide, para qué, y con qué justificación. Acompaña a todo caso de uso.

Ningún caso de uso recibe "el usuario" a secas: recibe un `Principal` con ámbito y
una `finalidad` explícita. Es lo que permite que la decisión de divulgación y el
asiento de auditoría se construyan siempre con la misma información.
"""

from __future__ import annotations

from dataclasses import dataclass

from found_persons.domain.habeas_data import DisclosureScope, Purpose


@dataclass(frozen=True, slots=True)
class Principal:
    """Solicitante autenticado, humano o dispositivo."""

    actor_id: str
    """`user:cruz-roja:1183`, `device:9f2c...`, `service:bundle_ingestor`."""

    scope: DisclosureScope
    organization: str | None = None
    channel: str = "http"
    """`http` o `mesh`. Cambia el canal del asiento de auditoría, no los permisos."""

    device_id: str | None = None

    @property
    def is_device(self) -> bool:
        return self.device_id is not None


@dataclass(frozen=True, slots=True)
class AccessContext:
    """Finalidad y justificación de una operación concreta.

    La justificación es obligatoria para todo lo que toque PII y se guarda literal:
    el Titular puede pedirla, y una justificación vacía es en sí misma un hallazgo
    de auditoría.
    """

    purpose: Purpose
    justification: str

    def require_justification(self) -> None:
        if not self.justification.strip():
            raise ValueError(
                "Toda operación sobre datos personales exige justificación "
                "(Ley 1581 art. 17 lit. e; regla de PII §12.3)."
            )
