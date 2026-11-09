from __future__ import annotations

from typing import Any

from odoo import fields, models

from odoo.addons.base.models.res_users import check_identity


class ResUsers(models.Model):
    """Add MCP key/session relations and the actions to manage them."""

    _inherit = 'res.users'

    # Fields
    # ----------------------------------------

    woomcp_key_ids = fields.One2many(
        comodel_name='aypatech_woomcp.key',
        inverse_name='user_id',
        string='MCP Keys',
        user_writeable=True,
    )

    woomcp_session_ids = fields.One2many(
        comodel_name='aypatech_woomcp.session',
        inverse_name='user_id',
        string='MCP Sessions',
        domain=[('active', '=', True)],
        user_writeable=True,
    )

    # Actions
    # ----------------------------------------

    @check_identity
    def action_woomcp_generate_key(self) -> dict[str, Any]:
        """Open the wizard to generate a new MCP key for this user."""
        return {
            'type': 'ir.actions.act_window',
            'name': 'New MCP Key',
            'res_model': 'aypatech_woomcp.generate_key',
            'views': [(False, 'form')],
            'target': 'new',
        }

    def action_woomcp_revoke_sessions(self) -> dict[str, Any]:
        """Deactivate all active MCP sessions of this user and reload."""
        sessions = (
            self.env['aypatech_woomcp.session']
            .sudo()
            .search(
                [
                    ('user_id', '=', self.id),
                    ('active', '=', True),
                ],
            )
        )
        sessions.write({'active': False})
        return {'type': 'ir.actions.client', 'tag': 'reload'}
