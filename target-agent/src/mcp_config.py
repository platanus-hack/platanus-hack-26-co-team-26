"""Declaracion estatica de los servidores MCP conectados al agente de Acme.

El extractor (backend/adapters/extractor) lee este modulo por AST — no abre ningun
transporte MCP de verdad. Mantener esta lista como literales planos (no construida
dinamicamente) es lo que la hace extraible estaticamente.
"""

MCP_SERVERS = [
    {
        "id": "mcp.notion",
        "name": "notion",
        "url": "http://localhost:3845/sse",
        "transport": "sse",
        "trust_level": "third_party",
        "tools": [
            {
                "name": "search_pages",
                "description": "Search Notion pages by query",
                "side_effects": "read",
            },
        ],
    },
]
