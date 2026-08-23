"""Distancia entre dos puntos geográficos. Sin dependencias — ni siquiera numpy.

Se usa para decidir si dos reportes de sismo de fuentes distintas describen el
mismo evento físico (`domain/dedup.py`). Un error de estimación entre redes
sismológicas de cientos de km en los primeros segundos es normal — no hace falta
precisión geodésica, solo suficiente para descartar que sean eventos distintos.
"""

from __future__ import annotations

import math

EARTH_RADIUS_KM = 6371.0088


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Distancia en línea recta sobre la esfera terrestre, en kilómetros."""
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    d_phi = math.radians(lat2 - lat1)
    d_lambda = math.radians(lon2 - lon1)
    a = (
        math.sin(d_phi / 2) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(d_lambda / 2) ** 2
    )
    return 2 * EARTH_RADIUS_KM * math.asin(math.sqrt(a))
