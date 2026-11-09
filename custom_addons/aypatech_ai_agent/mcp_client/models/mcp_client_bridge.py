from __future__ import annotations

import json

from odoo import _, api, models
from odoo.exceptions import UserError

from odoo.addons.aypatech_ai_agent.mcp.core.tool import mcp_tool


class MCPClientBridgeMixin(models.AbstractModel):
    """Expose external MCP servers' tools to the agent's own tool-calling loop.

    Rather than re-registering every remote tool individually (the static
    ``@mcp_tool`` registry is built once per Odoo registry, not per
    request), the agent gets two bridge tools: one to discover what is
    available, one to call it. This mirrors how a human using an MCP
    client such as Claude Desktop sees and invokes tools from several
    configured servers side by side.
    """

    _inherit = 'aypatech_woomcp.mixin'

    @api.model
    @mcp_tool(
        name='list_mcp_client_tools',
        description=(
            'List the tools advertised by the external MCP servers configured '
            'on this instance (Settings > AI Agent > External MCP Servers). '
            "Call 'call_mcp_client_tool' to actually invoke one. Each tool is "
            "returned with the name of the server that owns it."
        ),
        input_schema={
            'type': 'object',
            'properties': {
                'server': {
                    'type': 'string',
                    'description': 'Only list tools from this server (by name). Omit to list all.',
                },
            },
        },
        category='read',
        registry='odoo',
    )
    def _mcp_list_mcp_client_tools(self, server: str | None = None) -> dict:
        """Return the cached tool catalog of active external MCP servers."""
        domain = [('active', '=', True)]
        if server:
            domain.append(('name', '=', server))
        servers = self.env['aypatech_wooai.mcp.client.server'].sudo().search(domain)
        tools = []
        for srv in servers:
            for tool in srv.tool_ids:
                tools.append({
                    'server': srv.name,
                    'name': tool.name,
                    'description': tool.description,
                    'input_schema': json.loads(tool.input_schema or '{}'),
                })
        return {'tools': tools}

    @api.model
    @mcp_tool(
        name='call_mcp_client_tool',
        description=(
            "Call a tool on a configured external MCP server. Use "
            "'list_mcp_client_tools' first to see server names, tool names "
            'and their expected arguments.'
        ),
        input_schema={
            'type': 'object',
            'properties': {
                'server': {
                    'type': 'string',
                    'description': 'The server name, as shown by list_mcp_client_tools.',
                },
                'tool': {
                    'type': 'string',
                    'description': 'The tool name on that server.',
                },
                'arguments': {
                    'type': 'object',
                    'description': 'Arguments to pass to the tool, matching its input schema.',
                },
            },
            'required': ['server', 'tool'],
        },
        category='call',
        registry='odoo',
    )
    def _mcp_call_mcp_client_tool(
        self,
        server: str | None = None,
        tool: str | None = None,
        arguments: dict | None = None,
    ) -> dict:
        """Dispatch a tool call to the named external MCP server."""
        if not server or not tool:
            raise UserError(_("Both 'server' and 'tool' are required."))
        record = self.env['aypatech_wooai.mcp.client.server'].sudo().search(
            [('name', '=', server), ('active', '=', True)], limit=1,
        )
        if not record:
            raise UserError(_('No active external MCP server named %(name)s.', name=server))
        return record.call_tool(tool, arguments or {})
