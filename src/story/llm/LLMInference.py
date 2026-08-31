from typing import Any, Dict, List, Optional
from story.llm.LLMProviderFactory import LLMProviderFactory
from story.llm.LLMResponse import LLMResponse


class LLMInference:
    """
    High-level entry point for LLM operations in the story layer.
    Allows completing prompts or running chats using a simple, unified interface.
    """

    def __init__(self, provider: str, model: str, **kwargs):
        self.config = {
            "provider": provider,
            "model": model,
            **kwargs
        }
        self.provider_client = LLMProviderFactory.create(self.config)

    def complete(self, prompt: str, **kwargs) -> LLMResponse:
        """Synchronously complete a prompt."""
        return self.provider_client.complete(prompt, **kwargs)

    def chat(self, messages: List[Dict[str, str]], **kwargs) -> LLMResponse:
        """Synchronously chat with a list of messages."""
        return self.provider_client.chat(messages, **kwargs)

    async def complete_async(self, prompt: str, **kwargs) -> LLMResponse:
        """Asynchronously complete a prompt."""
        return await self.provider_client.complete_async(prompt, **kwargs)

    async def chat_async(self, messages: List[Dict[str, str]], **kwargs) -> LLMResponse:
        """Asynchronously chat with a list of messages."""
        return await self.provider_client.chat_async(messages, **kwargs)
