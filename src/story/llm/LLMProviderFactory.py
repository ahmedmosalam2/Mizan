"""
LLMProviderFactory — builds the right provider client from config.
"""
import os
from typing import Any, Dict, Optional

from story.llm.LLMEnums import LLMProvider
from story.llm.providers.groq_provider import GroqProvider
from story.llm.providers.openrouter_provider import OpenRouterProvider
from story.llm.providers.gemini_provider import GeminiProvider
from story.llm.providers.mock_provider import MockProvider


_PROVIDER_MAP = {
    LLMProvider.GROQ:       GroqProvider,
    LLMProvider.OPENROUTER: OpenRouterProvider,
    LLMProvider.GEMINI:     GeminiProvider,
    LLMProvider.MOCK:       MockProvider,
}


class LLMProviderFactory:
    """
    بيرجع provider instance بناءً على الـ config.

    Usage:
        provider = LLMProviderFactory.create({"provider": "groq", "model": "llama-3.3-70b-versatile"})
        response = provider.complete("اكتب إعلاناً لرمضان")
    """

    @staticmethod
    def create(config: Dict[str, Any]):
        provider_name = config.get("provider", "groq").lower()
        try:
            provider_enum = LLMProvider(provider_name)
        except ValueError:
            raise ValueError(
                f"Unknown LLM provider: '{provider_name}'. "
                f"Available: {[p.value for p in LLMProvider]}"
            )

        provider_cls = _PROVIDER_MAP.get(provider_enum)
        if not provider_cls:
            raise NotImplementedError(f"Provider '{provider_name}' is registered but not implemented yet.")

        return provider_cls(config)

    @staticmethod
    def available_providers():
        return [p.value for p in _PROVIDER_MAP.keys()]
