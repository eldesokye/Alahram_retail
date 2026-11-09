from __future__ import annotations

from odoo import api, fields, models
from odoo.exceptions import UserError


class ResConfigSettings(models.TransientModel):
    """Expose AI provider, agent, and runtime limits in the settings."""

    _inherit = 'res.config.settings'

    # ------------------------------------
    # Fields
    # ------------------------------------

    wooai_provider_id = fields.Many2one(
        related='company_id.wooai_default_provider_id',
        readonly=False,
    )

    wooai_agent_id = fields.Many2one(
        related='company_id.wooai_default_agent_id',
        readonly=False,
    )

    wooai_api_key = fields.Char(
        string='API Key',
        help="Write-only: never read back once saved.",
    )

    wooai_has_key = fields.Boolean(
        compute='_compute_wooai_provider_state',
    )

    wooai_test_ok = fields.Boolean(
        compute='_compute_wooai_provider_state',
    )

    wooai_test_message = fields.Char(
        compute='_compute_wooai_provider_state',
    )

    wooai_tested_at = fields.Datetime(
        compute='_compute_wooai_provider_state',
    )

    wooai_model_id = fields.Many2one(
        comodel_name='aypatech_wooai.model',
        string='Model',
        domain="[('provider_id', '=', wooai_provider_id)]",
        compute='_compute_wooai_model_id',
        readonly=False,
        store=True,
    )

    # ------------------------------------
    # Compute
    # ------------------------------------

    @api.depends('wooai_provider_id')
    def _compute_wooai_model_id(self) -> None:
        """Default the model picker to the provider's current default model."""
        for settings in self:
            settings.wooai_model_id = settings.wooai_provider_id.default_model_id

    @api.depends('wooai_provider_id')
    def _compute_wooai_provider_state(self) -> None:
        """Reflect the provider's stored key presence and last test outcome."""
        for settings in self:
            provider = settings.wooai_provider_id.sudo()
            settings.wooai_has_key = bool(provider.api_key)
            settings.wooai_test_ok = provider.last_test_ok
            settings.wooai_test_message = provider.last_test_message
            settings.wooai_tested_at = provider.last_tested_at

    # ------------------------------------
    # Actions
    # ------------------------------------

    def set_values(self) -> None:
        """Persist the quick-setup API key and default model onto the provider."""
        super().set_values()
        provider = self.wooai_provider_id.sudo()
        if not provider:
            return
        vals = {}
        if self.wooai_api_key and self.wooai_api_key.strip():
            vals['api_key'] = self.wooai_api_key.strip()
        if self.wooai_model_id and self.wooai_model_id != provider.default_model_id:
            vals['default_model_id'] = self.wooai_model_id.id
        if vals:
            provider.write({**vals, 'active': True})
        self.wooai_api_key = False

    def action_wooai_test_connection(self) -> dict:
        """Save pending changes, test the provider, and notify the result."""
        self.execute()
        provider = self.env.company.wooai_default_provider_id
        if not provider:
            raise UserError(self.env._('Choose an AI provider first.'))
        ok, message = provider.test_connection()
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'type': 'success' if ok else 'danger',
                'title': self.env._('AI Provider'),
                'message': message,
                'sticky': not ok,
                'next': {'type': 'ir.actions.client', 'tag': 'soft_reload'},
            },
        }

    def action_wooai_clear_key(self) -> dict:
        """Remove the provider's stored API key."""
        self.execute()
        provider = self.env.company.wooai_default_provider_id.sudo()
        if provider and provider.api_key:
            provider.write({'api_key': False})
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'type': 'success',
                'title': self.env._('AI Provider'),
                'message': self.env._('API key removed.'),
                'next': {'type': 'ir.actions.client', 'tag': 'soft_reload'},
            },
        }

    wooai_max_iterations = fields.Integer(
        string='WooFusion AI Max Iterations',
        help=(
            'Maximum number of LLM rounds per worker slice. The model is '
            'warned shortly before the limit so it can wrap up.'
        ),
        config_parameter='aypatech_ai_agent.wooai_max_iterations',
        default=20,
    )

    wooai_slice_wallclock_seconds = fields.Integer(
        string='WooFusion AI Slice Wallclock (s)',
        help=(
            'Maximum seconds a single worker slice may run before the turn '
            'is checkpointed and resumed by a fresh worker. Capped by the '
            'cron time limit.'
        ),
        config_parameter='aypatech_ai_agent.wooai_slice_wallclock_seconds',
        default=600,
    )

    wooai_turn_wallclock_seconds = fields.Integer(
        string='WooFusion AI Turn Wallclock (s)',
        help=(
            'Maximum total seconds a single user turn may run across all '
            'worker slices before it stops with an error.'
        ),
        config_parameter='aypatech_ai_agent.wooai_turn_wallclock_seconds',
        default=3600,
    )

    wooai_turn_cost_limit = fields.Float(
        string='WooFusion AI Turn Cost Limit',
        help=(
            'Maximum amount a single user turn may spend, in the price '
            'currency of the model. The model is warned at 80% and the '
            'turn stops with an error when the limit is reached. Set 0 '
            'to disable.'
        ),
        config_parameter='aypatech_ai_agent.wooai_turn_cost_limit',
    )

    wooai_session_retention_enabled = fields.Boolean(
        string='WooFusion AI Chat Retention',
        help=(
            'Let the scheduled cleanup delete finished chats once they are '
            'old enough. A chat that is still running is never touched.'
        ),
        config_parameter='aypatech_ai_agent.wooai_session_retention_enabled',
    )

    wooai_session_retention_days = fields.Integer(
        string='WooFusion AI Retention Days',
        help='Days a finished chat is kept before the cleanup deletes it.',
        config_parameter='aypatech_ai_agent.wooai_session_retention_days',
        default=90,
    )

    wooai_client_action_timeout = fields.Integer(
        string='WooFusion AI Client Action Timeout (s)',
        help=(
            'Seconds a chat waits for the browser to carry out an action it '
            'asked for before the cleanup answers for it and lets the turn '
            'go on. Zero waits for good.'
        ),
        config_parameter='aypatech_ai_agent.wooai_client_action_timeout',
        default=600,
    )
