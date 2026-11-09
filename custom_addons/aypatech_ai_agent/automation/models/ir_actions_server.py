from __future__ import annotations

from odoo import fields, models

from odoo.addons.aypatech_ai_agent.automation.tools.constants import (
    AGENT_DEFAULT_MAX_COST_EUR,
    AGENT_DEFAULT_MAX_LIFETIME_HOURS,
    AGENT_DEFAULT_MAX_RESUMES,
    AGENT_DEFAULT_MAX_TOTAL_TOKENS,
)
from odoo.addons.aypatech_ai_agent.automation.tools.dispatch import fire_action


class IrActionsServer(models.Model):
    """Add the ``ai_agent`` server-action state firing an AI agent."""

    _inherit = 'ir.actions.server'

    # Fields
    # --------------------------------------------------

    state = fields.Selection(
        selection_add=[('wooai_agent', 'Run AI Agent')],
        ondelete={'wooai_agent': 'cascade'},
    )

    agent_id = fields.Many2one(
        comodel_name='aypatech_wooai.agent',
        string='Agent',
        ondelete='restrict',
    )

    wooai_agent_prompt = fields.Text(
        string='Agent Prompt',
        help=(
            'Initial prompt sent to the agent on each fire. '
            'Rendered as an inline template with the evaluation context of '
            'the action (record, records, env, user), plus previous_session '
            '(previous_session.last_text and previous_session.tool_log) when '
            'the action chains after an earlier agent run.'
        ),
        translate=True,
    )

    wooai_agent_dispatch_mode = fields.Selection(
        selection=[
            ('single', 'Single'),
            ('per_record', 'Per Record'),
        ],
        string='Agent Dispatch Mode',
        help=(
            'Single spawns one session for the whole target recordset; '
            'Per Record spawns one session per resolved record so the agent '
            'runs independently against each.'
        ),
        default='single',
    )

    wooai_agent_record_source = fields.Selection(
        selection=[
            ('domain', 'Domain'),
            ('code', 'Python'),
        ],
        string='Agent Record Source',
        help=(
            'How target records are resolved when no records come from the '
            'trigger context: from a search domain or from safe-evaluated '
            'Python code.'
        ),
        default='domain',
    )

    wooai_agent_record_domain = fields.Char(
        string='Agent Record Domain',
        help=(
            'Search domain used to resolve target records when the record '
            'source is Domain. Evaluated against the action model.'
        ),
        default='[]',
    )

    wooai_agent_record_code = fields.Text(
        string='Agent Record Code',
        help=(
            'Python code (safe-evaluated). Must assign a recordset to the '
            '"records" variable. Context: env, now, today.'
        ),
    )

    wooai_agent_max_records_per_fire = fields.Integer(
        string='Agent Max Records Per Fire',
        help=(
            'Upper bound on the number of records processed in a single '
            'per-record fire. Excess records are skipped. Zero means no limit.'
        ),
        default=100,
    )

    wooai_agent_max_resumes = fields.Integer(
        string='Agent Max Resumes',
        help=(
            'Maximum number of times a spawned session may resume. Enforced '
            'when the session resumes through a schedule; zero falls '
            'back to the module-wide default.'
        ),
        default=0,
    )

    wooai_agent_max_lifetime_hours = fields.Integer(
        string='Agent Max Lifetime (hours)',
        help=(
            'Maximum wall-clock lifetime of a spawned session in hours. '
            'Enforced when the session resumes through a schedule; zero '
            'falls back to the module-wide default.'
        ),
        default=0,
    )

    wooai_agent_max_total_tokens = fields.Integer(
        string='Agent Max Total Tokens',
        help=(
            'Maximum total tokens a spawned session may consume. Enforced '
            'when the session resumes through a schedule; zero falls '
            'back to the module-wide default.'
        ),
        default=0,
    )

    wooai_agent_max_cost_eur = fields.Float(
        string='Agent Max Cost (EUR)',
        help=(
            'Maximum cumulative cost in EUR a spawned session may incur. '
            'Enforced when the session resumes through a schedule; zero '
            'falls back to the module-wide default.'
        ),
        default=0.0,
    )

    wooai_agent_chain_strategy = fields.Selection(
        selection=[
            ('none', 'None'),
            ('per_record', 'Per Record'),
        ],
        string='Agent Chain Strategy',
        help=(
            'Per Record links each new session to the prior session for the '
            'same record so the agent can recall its previous run; None starts '
            'every session fresh.'
        ),
        default='none',
    )

    # Helper
    # --------------------------------------------------

    def _wooai_agent_effective_caps(self) -> dict:
        """Return the action caps, falling back to module defaults when zero."""
        self.ensure_one()
        return {
            'max_resumes': self.wooai_agent_max_resumes or AGENT_DEFAULT_MAX_RESUMES,
            'max_lifetime_hours': (
                self.wooai_agent_max_lifetime_hours or AGENT_DEFAULT_MAX_LIFETIME_HOURS
            ),
            'max_total_tokens': (
                self.wooai_agent_max_total_tokens or AGENT_DEFAULT_MAX_TOTAL_TOKENS
            ),
            'max_cost_eur': self.wooai_agent_max_cost_eur or AGENT_DEFAULT_MAX_COST_EUR,
        }

    # Actions
    # --------------------------------------------------

    def _run_action_wooai_agent(self, eval_context: dict | None = None) -> bool:
        """Fire the configured AI agent for a single-record run.

        :return: ``False`` per the server-action runner contract; the spawned
            session ids are exposed via ``eval_context['__agent_spawned__']``
        """
        fire_action(self, eval_context or {})
        return False

    def _run_action_wooai_agent_multi(self, eval_context: dict | None = None) -> bool:
        """Fire the configured AI agent for a multi-record run.

        :return: ``False`` per the server-action runner contract; the spawned
            session ids are exposed via ``eval_context['__agent_spawned__']``
        """
        fire_action(self, eval_context or {})
        return False
