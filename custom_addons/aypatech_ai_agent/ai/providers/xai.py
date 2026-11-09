from __future__ import annotations

from odoo.addons.aypatech_ai_agent.ai.providers.openai_compatible import (
    OpenAICompatibleProvider,
)


class XAIProvider(OpenAICompatibleProvider):
    """xAI's Grok Chat Completions API (OpenAI-compatible endpoint)."""

    name = 'xai'
    label = 'xAI (Grok)'
    default_model = 'grok-4'
    default_url = 'https://api.x.ai/v1'

    supports_web_search = False
    supports_vision = True
    supports_reasoning_effort = True

    reasoning_error_tokens = ('reasoning', 'effort', 'reasoning_effort')
