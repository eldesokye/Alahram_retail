from __future__ import annotations

from odoo import fields, models


class AIReportRun(models.Model):
    """One generated instance of a scheduled (or on-demand) AI report."""

    _name = 'aypatech_wooai.report.run'
    _description = 'AI Report'
    _order = 'id desc'

    name = fields.Char(required=True)
    company_id = fields.Many2one(comodel_name='res.company', required=True, default=lambda self: self.env.company, index=True)
    schedule_id = fields.Many2one(comodel_name='aypatech_wooai.report.schedule', ondelete='set null', index=True)
    agent_id = fields.Many2one(comodel_name='aypatech_wooai.agent', index=True)
    lang = fields.Char()
    state = fields.Selection(
        [('done', 'Ready'), ('sent', 'Sent'), ('failed', 'Failed')],
        default='done', required=True,
    )
    body_text = fields.Text(string='Agent Answer (Markdown)', readonly=True)
    body_html = fields.Html(sanitize=False, readonly=True)
    pdf_id = fields.Many2one(comodel_name='ir.attachment', string='PDF', readonly=True, ondelete='set null')
    pdf_error = fields.Char(readonly=True)
    sent_to = fields.Text(readonly=True)
    telegram_sent_to = fields.Text(readonly=True)
    sent_at = fields.Datetime(readonly=True)
    error = fields.Text(readonly=True)

    def action_resend(self) -> dict:
        """Re-deliver the existing PDF/HTML by e-mail and Telegram, without regenerating it."""
        from odoo.addons.aypatech_ai_agent.reports.services import builder
        for run in self:
            schedule = run.schedule_id
            if not schedule:
                continue
            by_lang = {}
            for _user, email, lang in schedule.recipients():
                if lang == run.lang or not run.lang:
                    by_lang.setdefault(lang, []).append(email)
            emails = by_lang.get(run.lang) or [e for emails in by_lang.values() for e in emails]
            if emails:
                builder.send_email(run, emails)
            if schedule.telegram_enabled:
                chat_ids = [c.strip() for c in (schedule.telegram_chat_ids or '').split(',') if c.strip()]
                sent = builder.send_telegram(run, schedule.sudo().telegram_bot_token, chat_ids)
                if sent:
                    run.write({'telegram_sent_to': ', '.join(sent)})
            run.write({'state': 'sent', 'sent_at': fields.Datetime.now()})
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'type': 'success',
                'title': self.env._('AI Report'),
                'message': self.env._('Report resent.'),
            },
        }
