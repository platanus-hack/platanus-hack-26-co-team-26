"""Plazos legales de consultas y reclamos (Ley 1581 art. 14 y 15).

Estos plazos no son objetivos de servicio: son términos legales, y vencerlos es la
causa más frecuente de sanción de la SIC. Por eso el vencimiento se calcula y se
persiste al radicar, no se deduce después.

Los días son **hábiles**. El cálculo de aquí excluye sábados y domingos; los
festivos de la Ley 51 de 1983 entran por `holidays`, que el adaptador rellena desde
el calendario del año. Sin festivos, el plazo calculado es más corto que el legal,
que es el lado seguro por el que equivocarse.
"""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta

#: Art. 14: la consulta se atiende en diez días hábiles.
QUERY_BUSINESS_DAYS = 10
#: Art. 14 inc. 2: prorrogable cinco días hábiles más, informando al Titular.
QUERY_EXTENSION_BUSINESS_DAYS = 5
#: Art. 15: el reclamo se atiende en quince días hábiles.
CLAIM_BUSINESS_DAYS = 15
#: Art. 15 inc. final: prorrogable ocho días hábiles más.
CLAIM_EXTENSION_BUSINESS_DAYS = 8
#: Art. 15 inc. 1: si el reclamo está incompleto, cinco días para subsanar.
CLAIM_COMPLETION_BUSINESS_DAYS = 5


def add_business_days(
    start_ms: int, days: int, *, holidays: frozenset[date] = frozenset()
) -> int:
    """Suma días hábiles a un instante epoch-ms y devuelve epoch-ms.

    El día de radicación no cuenta: el término empieza a correr al día hábil
    siguiente, que es la lectura estándar del art. 62 del Código de Régimen Político
    y Municipal para términos en días.
    """
    current = datetime.fromtimestamp(start_ms / 1000, tz=UTC)
    remaining = days
    while remaining > 0:
        current += timedelta(days=1)
        if current.weekday() >= 5 or current.date() in holidays:
            continue
        remaining -= 1
    return int(current.timestamp() * 1000)


def deadline_for(
    kind: str, filed_at_ms: int, *, holidays: frozenset[date] = frozenset()
) -> int:
    """Vencimiento del término según el tipo de petición."""
    days = QUERY_BUSINESS_DAYS if kind == "query" else CLAIM_BUSINESS_DAYS
    return add_business_days(filed_at_ms, days, holidays=holidays)


def extension_for(
    kind: str, deadline_ms: int, *, holidays: frozenset[date] = frozenset()
) -> int:
    """Vencimiento tras la prórroga. Solo es válida si se informó al Titular antes
    de que venciera el término inicial, con expresión de los motivos."""
    days = (
        QUERY_EXTENSION_BUSINESS_DAYS
        if kind == "query"
        else CLAIM_EXTENSION_BUSINESS_DAYS
    )
    return add_business_days(deadline_ms, days, holidays=holidays)
