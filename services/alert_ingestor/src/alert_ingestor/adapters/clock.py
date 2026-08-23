"""Reloj real y fijo. Ver `application/ports.Clock` sobre por qué se duplica desde
`found_persons` en vez de compartirse."""

from __future__ import annotations

import time

from alert_ingestor.application.ports import Clock


class SystemClock(Clock):
    def now_ms(self) -> int:
        return int(time.time() * 1000)


class FixedClock(Clock):
    def __init__(self, now_ms: int) -> None:
        self._now = now_ms

    def now_ms(self) -> int:
        return self._now

    def advance(self, delta_ms: int) -> None:
        self._now += delta_ms
