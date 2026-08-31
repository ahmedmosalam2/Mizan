from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from story.llm.LLMResponse import LLMResponse


class BaseLLMProvider(ABC):
    """
    Base class for all LLM providers in the story layer.
    """

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.model = config.get("model")
        self.api_key = config.get("api_key") or ""
        self.temperature = config.get("temperature", 0.7)
        self.max_tokens = config.get("max_tokens", 2048)

    @abstractmethod
    def complete(self, prompt: str, **kwargs) -> LLMResponse:
        """Single prompt completion."""
        pass

    @abstractmethod
    def chat(self, messages: List[Dict[str, str]], **kwargs) -> LLMResponse:
        """Multi-turn chat completion."""
        pass

    @abstractmethod
    async def complete_async(self, prompt: str, **kwargs) -> LLMResponse:
        """Async single prompt completion."""
        pass

    @abstractmethod
    async def chat_async(self, messages: List[Dict[str, str]], **kwargs) -> LLMResponse:
        """Async multi-turn chat completion."""
        pass
