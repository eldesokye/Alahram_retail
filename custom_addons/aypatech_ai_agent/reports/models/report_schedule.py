from __future__ import annotations

import logging
from datetime import datetime, time, timedelta

import pytz

from odoo import api, fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

FREQUENCIES = [('daily', 'Every Day'), ('weekly', 'Every Week'), ('monthly', 'Every Month')]
WEEKDAYS = [('0', 'Monday'), ('1', 'Tuesday'), ('2', 'Wednesday'), ('3', 'Thursday'),
            ('4', 'Friday'), ('5', 'Saturday'), ('6', 'Sunday')]


class AIReportSchedule(models.Model):
    """A recurring (or one-off) agent run delivered as a formatted report.

    Runs the agent with a fixed prompt on a schedule, renders its answer as
    a letter-headed document, and delivers it by e-mail and/or Telegram.
    """

    _name = 'aypatech_wooai.report.schedule'
    _description = 'AI Report Schedule'
    _order = 'next_run, id'

    name = fields.Char(required=True)
    active = fields.Boolean(default=True)
    company_id = fields.Many2one(
        comodel_name='res.company',
        required=True,
        default=lambda self: self.env.company,
        index=True,
    )
    agent_id = fields.Many2one(
        comodel_name='aypatech_wooai.agent',
        string='Agent',
        required=True,
        help='The agent that produces the report content each run.',
    )
    prompt = fields.Text(
        required=True,
        help='The instruction sent to the agent at the start of every run.',
    )

    frequency = fields.Selection(FREQUENCIES, required=True, default='weekly')
    weekday = fields.Selection(WEEKDAYS, default='0', help='Day of the week, for weekly reports.')
    monthday = fields.Integer('Day of the Month', default=1, help='1 to 28, for monthly reports.')
    hour = fields.Integer(default=8, help='Hour of the day, in the time zone below.')
    tz = fields.Selection(
        '_tz_selection', 'Time Zone', required=True,
        default=lambda self: self.env.user.tz or self.env.company.partner_id.tz or 'UTC',
    )

    user_ids = fields.Many2many(
        comodel_name='res.users',
        string='Send to Users',
        help="Each user gets the report by e-mail, in their own language.",
    )
    emails = fields.Char('Other E-mail Addresses', help='Separated by commas.')
    lang = fields.Selection(
        '_lang_selection', 'Language for Other Addresses',
        default=lambda self: self.env.company.partner_id.lang or self.env.lang or 'en_US',
    )

    telegram_enabled = fields.Boolean(string='Send by Telegram')
    telegram_bot_token = fields.Char(
        string='Telegram Bot Token',
        groups='base.group_system',
        help='From @BotFather. Only used when Send by Telegram is checked.',
    )
    telegram_chat_ids = fields.Char(
        string='Telegram Chat IDs',
        help='Comma-separated chat or channel ids the bot can message.',
    )

    active_runs_count = fields.Integer(compute='_compute_runs_count')
    run_ids = fields.One2many(comodel_name='aypatech_wooai.report.run', inverse_name='schedule_id')
    next_run = fields.Datetime(readonly=True, copy=False, index=True)
    last_run = fields.Datetime(readonly=True, copy=False)

    _monthday_range = models.Constraint('CHECK(monthday BETWEEN 1 AND 28)', 'The day of the month must be 1 to 28.')
    _hour_range = models.Constraint('CHECK(hour BETWEEN 0 AND 23)', 'The hour must be 0 to 23.')

    @api.model
    def _lang_selection(self):
        return self.env['res.lang'].get_installed()

    @api.model
    def _tz_selection(self):
        return [(tz, tz) for tz in pytz.common_timezones]

    @api.depends('run_ids')
    def _compute_runs_count(self) -> None:
        for schedule in self:
            schedule.active_runs_count = len(schedule.run_ids)

    def _compute_next(self, after=None):
        self.ensure_one()
        after = after or fields.Datetime.now()
        zone = pytz.timezone(self.tz or 'UTC')
        local = pytz.utc.localize(after).astimezone(zone)
        day = local.date()
        for _step in range(0, 400):
            if self.frequency == 'daily' or \
                    (self.frequency == 'weekly' and day.weekday() == int(self.weekday or 0)) or \
                    (self.frequency == 'monthly' and day.day == (self.monthday or 1)):
                moment = zone.localize(datetime.combine(day, time(self.hour or 0)))
                if moment > local:
                    return moment.astimezone(pytz.utc).replace(tzinfo=None)
            day += timedelta(days=1)
        raise UserError(self.env._('This schedule never runs.'))

    @api.model_create_multi
    def create(self, vals_list):
        schedules = super().create(vals_list)
        for schedule in schedules:
            schedule.next_run = schedule._compute_next()
        return schedules

    def write(self, vals):
        result = super().write(vals)
        if {'frequency', 'weekday', 'monthday', 'hour', 'tz', 'active'} & set(vals):
            for schedule in self.filtered('active'):
                schedule.next_run = schedule._compute_next()
        return result

    def recipients(self):
        self.ensure_one()
        out = [(user, user.email_formatted, user.lang or self.lang) for user in self.user_ids if user.email]
        for email in (self.emails or '').replace(';', ',').split(','):
            if email.strip():
                out.append((None, email.strip(), self.lang))
        return out

    def run_now(self):
        from odoo.addons.aypatech_ai_agent.reports.services import builder
        runs = self.env['aypatech_wooai.report.run']
        for schedule in self:
            runs |= builder.send_schedule(schedule)
            schedule.sudo().last_run = fields.Datetime.now()
        return runs

    def action_run_now(self) -> dict:
        self.run_now()
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'type': 'success',
                'title': self.env._('AI Report'),
                'message': self.env._('The report ran. See the Runs tab.'),
                'next': {'type': 'ir.actions.client', 'tag': 'soft_reload'},
            },
        }

    @api.model
    def _cron_run_schedules(self) -> None:
        now = fields.Datetime.now()
        for schedule in self.sudo().search([('next_run', '<=', now)]):
            try:
                with self.env.cr.savepoint():
                    schedule.with_company(schedule.company_id).run_now()
            except Exception:  # noqa: BLE001 — one schedule's failure must not block the rest
                _logger.exception('report schedule %s failed', schedule.id)
            schedule.next_run = schedule._compute_next(now)
            self.env.cr.commit()
