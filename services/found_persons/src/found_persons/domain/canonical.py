"""Serialización canónica para firmar.

Dos dispositivos tienen que producir byte por byte lo mismo a partir del mismo
contenido, o la firma no verifica. El equivalente Kotlin vive en `:core:crypto`
y el del protocolo en `protocol/docs/PROTOCOL.md`.

Reglas: claves ordenadas, sin espacios, UTF-8, sin escapar no-ASCII, `null` omitido.
"""

from __future__ import annotations

import base64
import json
from typing import Any


def _prune(value: Any) -> Any:
    """Quita los `None` recursivamente: un campo ausente y un campo nulo firman igual."""
    if isinstance(value, dict):
        return {k: _prune(v) for k, v in value.items() if v is not None}
    if isinstance(value, (list, tuple)):
        return [_prune(v) for v in value]
    if isinstance(value, (set, frozenset)):
        return sorted(_prune(v) for v in value)
    return value


def canonical_bytes(payload: dict[str, Any]) -> bytes:
    """Bytes canónicos y estables de un objeto. Es lo que se firma y se verifica."""
    return json.dumps(
        _prune(payload),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")


def b64u(raw: bytes) -> str:
    """base64url sin relleno — el formato que viaja en la malla (bytes son caros)."""
    return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")


def unb64u(value: str) -> bytes:
    padding = "=" * (-len(value) % 4)
    return base64.urlsafe_b64decode(value + padding)
