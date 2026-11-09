from __future__ import annotations

from odoo.addons.aypatech_ai_agent.ai.providers.openai_compatible import (
    OpenAICompatibleProvider,
)


class OpenRouterProvider(OpenAICompatibleProvider):
    """OpenRouter: one Chat Completions endpoint gatewaying many model vendors.

    Model technical names follow OpenRouter's ``vendor/model`` convention
    (e.g. ``anthropic/claude-sonnet-4.5``, ``meta-llama/llama-3.3-70b``) —
    the model catalog seeds a representative cross-vendor set, but any
    OpenRouter-listed slug works as an override.
    """

    name = 'openrouter'
    label = 'OpenRouter'
    default_model = 'openai/gpt-4o-mini'
    default_url = 'https://openrouter.ai/api/v1'

    supports_web_search = False
    supports_vision = True

    def headers(self) -> dict:
        """Add OpenRouter's recommended attribution headers to the bearer auth."""
        headers = super().headers()
        headers['HTTP-Referer'] = 'https://www.aypatech.com'
        headers['X-Title'] = 'AypaTech AI Agent'
        return headers
