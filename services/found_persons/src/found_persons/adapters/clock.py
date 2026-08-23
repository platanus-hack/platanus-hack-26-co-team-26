"""Relojes. El fijo no es solo para tests: es la única forma de razonar sobre plazos."""

from __future__ import annotations

import time

from found_persons.application.ports import Clock


class SystemClock(Clock):
    def now_ms(self) -> int:
        return int(time.time() * 1000)


class FixedClock(Clock):
    """Reloj controlado. Adaptador *fake* exigido por CONTRIBUTING para el puerto `Clock`."""

    def __init__(self, now_ms: int) -> None:
        self._now = now_ms

    def now_ms(self) -> int:
        return self._now

    def advance(self, delta_ms: int) -> None:
        self._now += delta_ms

    def set(self, now_ms: int) -> None:
        self._now = now_ms
