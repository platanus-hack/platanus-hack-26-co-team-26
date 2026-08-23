"""Errores del dominio. Los adaptadores traducen sus propios fallos (timeouts,
JSON malformado, websocket caído) a estos antes de que crucen hacia application/."""

from __future__ import annotations


class AlertIngestError(Exception):
    code = "alert_ingest_error"


class SourceUnavailable(AlertIngestError):
    """La fuente no respondió o cortó la conexión. Se espera y se reintenta:
    una fuente sísmica caída no es motivo para tumbar todo el servicio."""

    code = "source_unavailable"


class MalformedEvent(AlertIngestError):
    """La fuente entregó algo que no se pudo normalizar. Se descarta ese evento
    puntual — no debe tumbar el resto del lote."""

    code = "malformed_event"
