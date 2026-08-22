"""send_email — responde al cliente. Llamada de red saliente; el extractor la clasifica
como tool `http` (el enum ToolKind no tiene un kind dedicado para email).
"""

from __future__ import annotations

import httpx
from langchain_core.tools import tool

_ACME_MAIL_API = "https://mail.acme.internal/v1/send"


@tool
def send_email(to: str, body: str) -> str:
    """Send an email reply to the customer through Acme's mail API."""
    response = httpx.post(_ACME_MAIL_API, json={"to": to, "body": body}, timeout=10)
    return f"sent:{response.status_code}"
