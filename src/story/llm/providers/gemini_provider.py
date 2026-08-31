import os
from typing import Any, Dict, List
import litellm

from story.llm.providers.base_provider import BaseLLMProvider
from story.llm.LLMResponse import LLMResponse


class GeminiProvider(BaseLLMProvider):
    """
    Google Gemini Provider using litellm.
    """

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.api_key = self.api_key or os.getenv("GEMINI_API_KEY", "") or os.getenv("GOOGLE_API_KEY", "")

    def _prepare_params(self, messages: List[Dict[str, str]], **kwargs) -> Dict[str, Any]:
        model_name = self.model
        if not model_name.startswith("gemini/"):
            model_name = f"gemini/{model_name}"

        params = {
            "model": model_name,
            "messages": messages,
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
            provider="gemini",
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
