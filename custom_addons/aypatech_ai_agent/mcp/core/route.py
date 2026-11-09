from __future__ import annotations

from collections.abc import Callable
from typing import Any

from odoo import http


def mcp_route(route: str | list[str] | None = None, **kw: Any) -> Callable:
    """Wrap ``http.route`` with the MCP dispatcher type, auth and CORS defaults."""
    kw.setdefault('cors', '*')
    kw.update(
        {
            'type': 'woomcp',
            'auth': 'woomcp',
            'csrf': False,
            'save_session': False,
        },
    )
    return http.route(route=route, **kw)
