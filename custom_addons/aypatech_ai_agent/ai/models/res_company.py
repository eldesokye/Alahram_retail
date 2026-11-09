from __future__ import annotations

from odoo import api, fields, models


class ResCompany(models.Model):
    """Add company-level default AI provider and agent."""

    _inherit = 'res.company'

    # ----------------------------
    # Fields
    # ----------------------------

    wooai_default_provider_id = fields.Many2one(
        comodel_name='aypatech_wooai.provider',
        string='WooFusion AI Default Provider',
        help=(
            'Provider used when an agent does not specify one. '
            'Falls back to the first active provider if unset.'
        ),
        domain=[('active', '=', True)],
    )

    wooai_default_agent_id = fields.Many2one(
        comodel_name='aypatech_wooai.agent',
        string='WooFusion AI Default Agent',
        help=(
            'Agent used for new chat sessions when the user has not '
            'picked one. Falls back to the first active agent if unset.'
        ),
        domain=[('active', '=', True)],
    )

    # ----------------------------
    # Setup
    # ----------------------------

    @api.model
    def _wooai_ensure_defaults(self) -> None:
        """Give every company a default provider and agent, and every agent its partner.

        Called from data on install and on every upgrade, so databases that had the
        module before these defaults existed are set up too.
        """
        provider = self.env.ref('aypatech_ai_agent.ai_provider_openai', raise_if_not_found=False)
        agent = self.env.ref('aypatech_ai_agent.ai_agent_general', raise_if_not_found=False)
        companies = self.sudo().search([
            '|',
            ('wooai_default_provider_id', '=', False),
            ('wooai_default_agent_id', '=', False),
        ])
        for company in companies:
            vals = {}
            if provider and not company.wooai_default_provider_id:
                vals['wooai_default_provider_id'] = provider.id
            if agent and not company.wooai_default_agent_id:
                vals['wooai_default_agent_id'] = agent.id
            if vals:
                company.write(vals)
        # every agent posts in chatter through its own partner
        self.env['aypatech_wooai.agent'].with_context(active_test=False).search(
            [('partner_id', '=', False)]
        )._provision_partners()
        # the noupdate data below is skipped when an installed module is upgraded: fill in what is
        # missing, never overwrite what an administrator chose
        defaults = {
            'ai_provider_openai': 'model_gpt_5_4',
            'ai_provider_anthropic': 'model_claude_sonnet_4_6',
            'ai_provider_google': 'model_gemini_3_5_flash',
        }
        for provider_xmlid, model_xmlid in defaults.items():
            provider = self.env.ref('aypatech_ai_agent.' + provider_xmlid, raise_if_not_found=False)
            model = self.env.ref('aypatech_ai_agent.' + model_xmlid, raise_if_not_found=False)
            if provider and model and not provider.default_model_id:
                provider.sudo().default_model_id = model
        # these crons must run this module's session worker, whatever the data said when they were created
        cron_ids = self.env['ir.model.data'].sudo().search([
            ('module', '=', 'aypatech_ai_agent'), ('model', '=', 'ir.cron'),
        ]).mapped('res_id')
        self.env['ir.cron'].sudo().with_context(active_test=False).browse(cron_ids).exists().filtered(
            lambda cron: cron.state == 'ai_session'
        ).write({'state': 'wooai_session'})
        params = self.env['ir.config_parameter'].sudo()
        seeded = 'aypatech_ai_agent.wooai_sensitive_seeded'
        if not params.get_bool(seeded):
            self.env.ref('base.model_res_users').sudo().wooai_sensitive = True
            params.set_bool(seeded, True)
