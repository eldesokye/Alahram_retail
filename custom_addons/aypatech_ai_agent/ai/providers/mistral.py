from __future__ import annotations

from odoo.addons.aypatech_ai_agent.ai.providers.openai_compatible import (
    OpenAICompatibleProvider,
)


class MistralProvider(OpenAICompatibleProvider):
    """Mistral's Chat Completions API (OpenAI-compatible endpoint)."""

    name = 'mistral'
    label = 'Mistral'
    default_model = 'mistral-large-latest'
    default_url = 'https://api.mistral.ai/v1'

    supports_web_search = False
    supports_vision = True
