from __future__ import annotations

from .base import ProviderBase
from .openai import OpenAIProvider
from .anthropic import AnthropicProvider
from .google import GoogleProvider
from .openai_compatible import OpenAICompatibleProvider
from .groq import GroqProvider
from .mistral import MistralProvider
from .xai import XAIProvider
from .deepseek import DeepSeekProvider
from .openrouter import OpenRouterProvider
from .ollama import OllamaProvider


REGISTRY = {
    cls.name: cls
    for cls in (
        OpenAIProvider,
        AnthropicProvider,
        GoogleProvider,
        GroqProvider,
        MistralProvider,
        XAIProvider,
        DeepSeekProvider,
        OpenRouterProvider,
        OllamaProvider,
    )
}
