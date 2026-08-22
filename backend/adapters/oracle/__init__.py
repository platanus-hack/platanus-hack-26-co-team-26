"""adapters/oracle/ — C6 (owner D3, Alex).

El oráculo dicta verdad-fundamental: ¿el ataque funcionó, sí o no? NO es opinión del LLM.
- CanaryHoneypotOracle : canary que llega al honeypot => exploited. (MVP)
- SyscallOracle        : parseo de execve/connect (opcional, roadmap).
"""

from __future__ import annotations

from adapters.oracle.canary_honeypot import CanaryHoneypotOracle

__all__ = ["CanaryHoneypotOracle"]
