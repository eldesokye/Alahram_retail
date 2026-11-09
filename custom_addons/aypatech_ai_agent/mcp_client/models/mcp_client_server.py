from __future__ import annotations

import json
import logging
import uuid

import requests

from odoo import api, fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

DEFAULT_TIMEOUT = 30
AUTH_TYPES = [
    ('none', 'No Authentication'),
    ('bearer', 'Bearer Token'),
    ('header', 'Custom Header'),
]


class MCPClientServer(models.Model):
    """A remote MCP server this instance can call out to as a client.

    Lets the agent's own tool-calling loop reach tools exposed by another
    MCP server (this module's own ``mcp`` package, or any third party)
    without that server having to be an Odoo database.
    """

    _name = 'aypatech_wooai.mcp.client.server'
    _description = 'External MCP Server'
    _order = 'sequence, name'

    name = fields.Char(required=True)
    active = fields.Boolean(default=True)
    sequence = fields.Integer(default=10)
    company_id = fields.Many2one(
        comodel_name='res.company',
        default=lambda self: self.env.company,
    )
    url = fields.Char(
        string='Endpoint URL',
        required=True,
        help='The MCP Streamable HTTP endpoint, e.g. https://example.com/mcp',
    )
    auth_type = fields.Selection(AUTH_TYPES, default='none', required=True)
    api_key = fields.Char(string='Token / Key', groups='base.group_system')
    header_name = fields.Char(default='Authorization')
    timeout = fields.Integer(default=DEFAULT_TIMEOUT)
    description = fields.Text()
    tool_ids = fields.One2many(
        comodel_name='aypatech_wooai.mcp.client.tool',
        inverse_name='server_id',
    )
    tool_count = fields.Integer(compute='_compute_tool_count')
    last_sync = fields.Datetime(readonly=True)
    last_error = fields.Char(readonly=True)

    _unique_name = models.Constraint('unique(name)', 'A server with this name already exists.')

    @api.depends('tool_ids')
    def _compute_tool_count(self) -> None:
        for server in self:
            server.tool_count = len(server.tool_ids)

    # ----------------------------------------
    # Transport
    # ----------------------------------------

    def _headers(self) -> dict:
        self.ensure_one()
        headers = {
            'Content-Type': 'application/json',
            'Accept': 'application/json, text/event-stream',
        }
        if self.auth_type == 'bearer' and self.api_key:
            headers['Authorization'] = f'Bearer {self.api_key}'
        elif self.auth_type == 'header' and self.api_key:
            headers[self.header_name or 'Authorization'] = self.api_key
        return headers

    def _rpc(self, method: str, params: dict | None = None) -> dict:
        """Send one JSON-RPC 2.0 request and return its ``result``.

        :raise UserError: on a transport error or a JSON-RPC error response.
        """
        self.ensure_one()
        body = {
            'jsonrpc': '2.0',
            'id': str(uuid.uuid4()),
            'method': method,
            'params': params or {},
        }
        try:
            response = requests.post(
                self.url,
                headers=self._headers(),
                json=body,
                timeout=self.timeout or DEFAULT_TIMEOUT,
            )
            response.raise_for_status()
        except requests.RequestException as error:
            raise UserError(
                self.env._(
                    'Could not reach MCP server %(name)s: %(error)s',
                    name=self.name,
                    error=str(error)[:300],
                )
            ) from error
        content_type = response.headers.get('Content-Type', '')
        if 'text/event-stream' in content_type:
            payload = self._parse_sse(response.text)
        else:
            try:
                payload = response.json()
            except ValueError as error:
                raise UserError(
                    self.env._('MCP server %(name)s returned a non-JSON response.', name=self.name)
                ) from error
        if payload.get('error'):
            raise UserError(
                self.env._(
                    'MCP server %(name)s error: %(error)s',
                    name=self.name,
                    error=json.dumps(payload['error'])[:300],
                )
            )
        return payload.get('result') or {}

    @staticmethod
    def _parse_sse(text: str) -> dict:
        """Return the last JSON ``data:`` payload of a Server-Sent-Events body."""
        payload = {}
        for line in text.splitlines():
            if line.startswith('data:'):
                chunk = line[5:].strip()
                if chunk:
                    try:
                        payload = json.loads(chunk)
                    except ValueError:
                        continue
        return payload

    # ----------------------------------------
    # Actions
    # ----------------------------------------

    def action_sync_tools(self) -> dict:
        """Call ``initialize`` then ``tools/list`` and refresh the cached tool catalog."""
        for server in self:
            try:
                server._rpc(
                    'initialize',
                    {
                        'protocolVersion': '2025-06-18',
                        'capabilities': {},
                        'clientInfo': {'name': 'aypatech_ai_agent', 'version': '1.0'},
                    },
                )
                result = server._rpc('tools/list')
            except UserError as error:
                server.write({'last_error': str(error)[:500]})
                continue
            tools = result.get('tools') or []
            server.tool_ids.unlink()
            Tool = self.env['aypatech_wooai.mcp.client.tool']
            for tool in tools:
                Tool.create({
                    'server_id': server.id,
                    'name': tool.get('name'),
                    'description': tool.get('description') or '',
                    'input_schema': json.dumps(tool.get('inputSchema') or {}),
                })
            server.write({
                'last_sync': fields.Datetime.now(),
                'last_error': False,
            })
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'type': 'success',
                'title': self.env._('MCP Client'),
                'message': self.env._('Tool catalog refreshed.'),
            },
        }

    def call_tool(self, tool_name: str, arguments: dict | None = None) -> dict:
        """Invoke ``tools/call`` on this server and return its result payload."""
        self.ensure_one()
        return self._rpc(
            'tools/call',
            {'name': tool_name, 'arguments': arguments or {}},
        )
