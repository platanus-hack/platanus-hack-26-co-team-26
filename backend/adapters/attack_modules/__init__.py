"""adapters/attack_modules/ — C5 (owner D3, Alex).

Ataques concretos como adaptadores intercambiables bajo `AttackModulePort`
(ver domain/ports.py). MVP: cmd_injection + indirect_injection. mcp_rug_pull = opcional.
garak/PyRIT se envuelven como adaptador después (roadmap).
"""

from __future__ import annotations

from domain.ports import AttackModulePort

from adapters.attack_modules.cmd_injection import CmdInjection
from adapters.attack_modules.indirect_injection import IndirectInjection

# Registro id -> instancia. El sandbox resuelve `surface.attack_modules` (nombres) por aquí.
REGISTRY: dict[str, AttackModulePort] = {
    m.id: m for m in (CmdInjection(), IndirectInjection())
}


def get_module(module_id: str) -> AttackModulePort | None:
    """Devuelve el adaptador de ataque por id, o None si no está registrado."""
    return REGISTRY.get(module_id)


__all__ = ["CmdInjection", "IndirectInjection", "REGISTRY", "get_module"]
