from __future__ import annotations

from odoo.http import router
from odoo.http.requestlib import Request
from odoo.http.router import db_filter
from odoo.http.session import Session
from odoo.tools import config


def resolve_mcp_db(request: Request, session: Session) -> str | None:
    """Resolve an MCP request's database from a ``?db=`` selector."""
    host = request.httprequest.environ['HTTP_HOST']
    db_param = config.get('mcp_db_param', 'db')
    database = (request.httprequest.args.get(db_param) or '').strip()
    if database and db_filter([database], host=host):
        session.can_save = False
        session.db = database
        return database
    return None


_set_session_and_dbname = router._set_session_and_dbname


def _set_mcp_session_and_dbname(request: Request) -> None:
    """Resolve the database for ``/mcp`` requests, honouring a ``?db=`` selector.

    Odoo picks the database from the session cookie or the monodb setup, and
    an MCP client has neither on a multi-database server. It can still name
    the database in the URL, so fall back to that when nothing else matched.
    """
    _set_session_and_dbname(request)
    path = request.httprequest.path
    if not request.db and (path == '/aypatech_ai_agent/mcp' or path.startswith('/aypatech_ai_agent/mcp/')):
        request.db = resolve_mcp_db(request, request.session)


router._set_session_and_dbname = _set_mcp_session_and_dbname
