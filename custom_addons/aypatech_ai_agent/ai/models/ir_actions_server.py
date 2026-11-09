from __future__ import annotations

from odoo import fields, models


class IrActionsServer(models.Model):
    """Add the ``ai_session`` server-action state running pending sessions."""

    _inherit = 'ir.actions.server'

    # ----------------------------------------
    # Fields

    state = fields.Selection(
        selection_add=[('wooai_session', 'AI Session Worker')],
        ondelete={'wooai_session': 'cascade'},
    )

    # ----------------------------------------
    # Helper

    def _run_action_wooai_session(self, eval_context=None) -> None:
        """Run pending AI sessions for a single-record server action."""
        self.env['aypatech_wooai.session']._cron_run_pending_sessions()

    def _run_action_wooai_session_multi(self, eval_context=None) -> None:
        """Run pending AI sessions for a multi-record server action."""
        self.env['aypatech_wooai.session']._cron_run_pending_sessions()
