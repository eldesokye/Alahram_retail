from __future__ import annotations

from odoo.addons.aypatech_ai_agent.ai.providers.openai_compatible import (
    OpenAICompatibleProvider,
)


class DeepSeekProvider(OpenAICompatibleProvider):
    """DeepSeek's Chat Completions API (OpenAI-compatible endpoint)."""

    name = 'deepseek'
    label = 'DeepSeek'
    default_model = 'deepseek-chat'
    default_url = 'https://api.deepseek.com/v1'

    supports_web_search = False
    supports_vision = False
