from __future__ import annotations

from odoo import api, fields, models
from odoo.fields import Domain

from odoo.addons.mail.tools.discuss import Store


class ResPartner(models.Model):
    """Mark the contacts standing in for an AI agent."""

    _inherit = 'res.partner'

    # --------------------------------------------------------
    # Fields
    # --------------------------------------------------------

    wooai_agent_ids = fields.One2many(
        comodel_name='aypatech_wooai.agent',
        inverse_name='partner_id',
        string='AI Agents',
        help='Agents this contact stands in for in the chatter.',
    )

    # --------------------------------------------------------
    # Helper
    # --------------------------------------------------------

    def _wooai_agent_partners(self) -> models.BaseModel:
        """Return the contacts of this set that stand in for an agent.

        Archived and mention-disabled agents count: their contact must be kept
        out of a message's recipients just the same, or mentioning one mails a
        contact that has no address and enrols it as a follower.
        """
        agents = self.env['aypatech_wooai.agent'].sudo().with_context(active_test=False)
        return self.browse(
            agents.search([('partner_id', 'in', self.ids)]).partner_id.ids
        )

    def _wooai_mentionable_agents(self) -> models.BaseModel:
        """Return the agents of this set that answer a mention."""
        return (
            self.env['aypatech_wooai.agent']
            .sudo()
            .search(
                [
                    *self._wooai_mentionable_agent_domain(),
                    ('partner_id', 'in', self.ids),
                ]
            )
        )

    @api.model
    def _wooai_mentionable_agent_domain(self) -> list:
        """Return the domain of the agents a mention can actually reach.

        Suggesting an agent and answering as one must agree: an agent offered
        in the dropdown that then never replies is worse than one that is not
        offered at all.
        """
        return [('active', '=', True), ('mention_enabled', '=', True)]

    @api.model
    def _wooai_agent_partner_ids(self) -> list[int]:
        """Return the ids of the contacts standing in for a reachable agent.

        Resolved through ``aypatech_wooai.agent`` rather than the ``wooai_agent_ids``
        one2many, which hides archived agents and would let their contact pass
        for an ordinary one.
        """
        agents = (
            self.env['aypatech_wooai.agent'].sudo().search(self._wooai_mentionable_agent_domain())
        )
        return agents.partner_id.ids

    # --------------------------------------------------------
    # ORM methods
    # --------------------------------------------------------

    def _store_mention_fields(self, res: Store.FieldList) -> None:
        """Tell the client which suggested contacts are agents, so it can badge them.

        Resolved against the agent ids rather than the ``wooai_agent_ids``
        one2many, which active-filters and would report an archived agent's
        contact as an ordinary one.
        """
        super()._store_mention_fields(res)
        agent_ids = set(self._wooai_agent_partner_ids())
        res.attr('is_ai_agent', lambda partner: partner.id in agent_ids)

    @api.readonly
    @api.model
    def get_mention_suggestions_from_channel(self, channel_id: int, search: str, limit: int = 8):
        """Offer the agents in a Discuss conversation too, not only its members.

        The base method suggests members and nobody else, and an agent joins
        nothing. Its term is spelled out again here rather than reused: the
        base domain admits active contacts only, and a stand-in contact is
        archived on purpose. This is the one composer agents are offered in.
        """
        result = super().get_mention_suggestions_from_channel(channel_id, search, limit)
        if not isinstance(result, Store):
            return result
        term = Domain('name', 'ilike', search) | Domain('email', 'ilike', search)
        agents = self.with_context(active_test=False).search(
            term & Domain('id', 'in', self._wooai_agent_partner_ids()),
            limit=limit,
        )
        if agents:
            result.add(
                agents,
                lambda res: (
                    res.from_method('_store_partner_fields'),
                    res.from_method('_store_mention_fields'),
                ),
            )
        return result
