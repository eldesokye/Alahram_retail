from __future__ import annotations

from odoo import fields, models


class MCPClientTool(models.Model):
    """One tool advertised by an external MCP server, cached from ``tools/list``."""

    _name = 'aypatech_wooai.mcp.client.tool'
    _description = 'External MCP Server Tool'
    _order = 'name'

    server_id = fields.Many2one(
        comodel_name='aypatech_wooai.mcp.client.server',
        required=True,
        ondelete='cascade',
        index=True,
    )
    name = fields.Char(required=True)
    description = fields.Text()
    input_schema = fields.Text(help='JSON Schema for this tool\'s arguments, as returned by the server.')

    _unique_per_server = models.Constraint(
        'unique(server_id, name)',
        'This server already advertises a tool with this name.',
    )
