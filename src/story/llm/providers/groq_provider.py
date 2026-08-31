import os
from typing import Any, Dict, List
import litellm

from story.llm.providers.base_provider import BaseLLMProvider
from story.llm.LLMResponse import LLMResponse


class GroqProvider(BaseLLMProvider):
    """
    Groq Provider using litellm.
    """

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.api_key = self.api_key or os.getenv("GROQ_API_KEY", "")
        # Ensure litellm drops unsupported parameters like cache_breakpoint
        litellm.drop_params = True

    def _prepare_params(self, messages: List[Dict[str, str]], **kwargs) -> Dict[str, Any]:
        # Strip cache parameters if present in messages (Groq exception guard)
        clean_messages = []
        for msg in messages:
            if isinstance(msg, dict):
                clean_msg = msg.copy()
                clean_msg.pop("cache_breakpoint", None)
                clean_msg.pop("cache_control", None)
                clean_messages.append(clean_msg)
            else:
                clean_messages.append(msg)

        params = {
            "model": f"groq/{self.model}",
            "messages": clean_messages,
            "api_key": self.api_key,
            "temperature": kwargs.get("temperature", self.temperature),
            "max_tokens": kwargs.get("max_tokens", self.max_tokens),
        }
        return params

    def _process_response(self, response: Any) -> LLMResponse:
        content = response.choices[0].message.content or ""
        usage = getattr(response, "usage", None)
        prompt_tokens = usage.prompt_tokens if usage else 0
        completion_tokens = usage.completion_tokens if usage else 0
        total_tokens = usage.total_tokens if usage else 0

        return LLMResponse(
            content=content,
            model=self.model,
            provider="groq",
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total_tokens,
            finish_reason=response.choices[0].finish_reason or "stop",
            raw=response,
        )

    def complete(self, prompt: str, **kwargs) -> LLMResponse:
        messages = [{"role": "user", "content": prompt}]
        params = self._prepare_params(messages, **kwargs)
        response = litellm.completion(**params)
        return self._process_response(response)

    def chat(self, messages: List[Dict[str, str]], **kwargs) -> LLMResponse:
        params = self._prepare_params(messages, **kwargs)
        response = litellm.completion(**params)
        return self._process_response(response)

    async def complete_async(self, prompt: str, **kwargs) -> LLMResponse:
        messages = [{"role": "user", "content": prompt}]
        params = self._prepare_params(messages, **kwargs)
        response = await litellm.acompletion(**params)
        return self._process_response(response)

    async def chat_async(self, messages: List[Dict[str, str]], **kwargs) -> LLMResponse:
        params = self._prepare_params(messages, **kwargs)
        response = await litellm.acompletion(**params)
        return self._process_response(response)
