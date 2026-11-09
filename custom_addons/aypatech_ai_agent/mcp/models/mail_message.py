from __future__ import annotations

from typing import Any

from odoo import api, fields, models


class MailMessage(models.Model):
    """Store and expose the originating MCP key name on messages."""

    _inherit = 'mail.message'

    # ------------------------------------
    # Fields
    # ------------------------------------

    woomcp_name = fields.Char(
        string='MCP Key',
        readonly=True,
    )

    # ------------------------------------
    # Helper
    # ------------------------------------

    def _store_message_fields(self, res, **kwargs) -> None:
        """Add the MCP-origin flag to the fields sent to the web client."""
        super()._store_message_fields(res, **kwargs)
        res.append('woomcp_name')

    # ------------------------------------
    # ORM
    # ------------------------------------

    @api.model_create_multi
    def create(self, vals_list: list[dict[str, Any]]) -> models.BaseModel:
        """Default ``woomcp_name`` from the context when an MCP key is active."""
        if woomcp_name := self.env.context.get('woomcp_name'):
            for vals in vals_list:
                vals.setdefault('woomcp_name', woomcp_name)
        return super().create(vals_list)
