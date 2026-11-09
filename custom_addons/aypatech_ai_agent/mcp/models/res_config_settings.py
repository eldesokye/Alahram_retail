from __future__ import annotations

from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    """Add MCP session, logging and rate-limit options to the settings."""

    _inherit = 'res.config.settings'

    # Fields

    woomcp_session_timeout = fields.Integer(
        string='Commerce MCP Session Timeout (hours)',
        config_parameter='aypatech_ai_agent.mcp_session_timeout_hours',
        default=24,
        help='Inactive MCP sessions are cleaned up after this many hours.',
    )

    woomcp_log_retention = fields.Integer(
        string='Commerce MCP Log Retention (days)',
        config_parameter='aypatech_ai_agent.mcp_log_autovacuum_days',
        default=30,
        help='Audit logs older than this many days are automatically deleted.',
    )

    woomcp_rate_limit_requests = fields.Integer(
        string='Commerce MCP Rate Limit (Requests)',
        config_parameter='aypatech_ai_agent.woomcp_rate_limit_requests',
        default=60,
        help='Default maximum MCP requests per minute per key. '
        'Set to 0 to disable. Used as default when generating new keys.',
    )

    woomcp_annotate_messages = fields.Boolean(
        string='Commerce MCP Annotate Messages',
        config_parameter='aypatech_ai_agent.woomcp_annotate_messages',
        default=True,
        help=(
            'When enabled, chatter messages from MCP operations are '
            'marked to distinguish AI-originated changes from manual ones.'
        ),
    )
