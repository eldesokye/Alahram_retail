from __future__ import annotations

from odoo.addons.aypatech_ai_agent.ai.providers.openai_compatible import (
    OpenAICompatibleProvider,
)


class GroqProvider(OpenAICompatibleProvider):
    """Groq's OpenAI-compatible Chat Completions API, served on its LPU hardware."""

    name = 'groq'
    label = 'Groq'
    default_model = 'llama-3.3-70b-versatile'
    default_url = 'https://api.groq.com/openai/v1'

    supports_web_search = False
    supports_vision = True
