from __future__ import annotations

from odoo.addons.aypatech_ai_agent.ai.providers.openai_compatible import (
    OpenAICompatibleProvider,
)


class OllamaProvider(OpenAICompatibleProvider):
    """Ollama's local/offline OpenAI-compatible Chat Completions API.

    No API key is required; point ``base_url`` at the local (or LAN) Ollama
    server, e.g. ``http://localhost:11434/v1``. Model names are whatever the
    admin has pulled locally (``ollama pull llama3.1``); the catalog seeds a
    few common defaults as a starting point, not a hard allowlist.
    """

    name = 'ollama'
    label = 'Ollama (Local)'
    default_model = 'llama3.1'
    default_url = 'http://localhost:11434/v1'

    supports_web_search = False
    supports_vision = True

    @property
    def api_key(self) -> str:
        """Ollama needs no authentication; never raise for a missing key."""
        return self._api_key or 'ollama'

    def headers(self) -> dict:
        """Return plain JSON headers; a local server requires no bearer token."""
        return {'Content-Type': 'application/json'}
