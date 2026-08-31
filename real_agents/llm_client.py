"""
LLM Client — Thin wrapper around litellm with token/cost tracking.

Every call is tracked: tokens in, tokens out, cost, latency.
No magic, no hiding — you see exactly what the LLM costs you.
"""

import time
import json
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

import litellm

# Suppress litellm's noisy logs
litellm.suppress_debug_info = True


@dataclass
class LLMCall:
    """Record of a single LLM call."""
    model: str
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    cost_usd: float
    latency_ms: float
    success: bool
    error: Optional[str] = None


@dataclass
class LLMStats:
    """Accumulated stats across multiple calls."""
    calls: List[LLMCall] = field(default_factory=list)
    total_tokens: int = 0
    total_cost_usd: float = 0.0
    total_latency_ms: float = 0.0

    def add(self, call: LLMCall):
        self.calls.append(call)
        self.total_tokens += call.total_tokens
        self.total_cost_usd += call.cost_usd
        self.total_latency_ms += call.latency_ms

    def summary(self) -> Dict[str, Any]:
        return {
            "total_calls": len(self.calls),
            "total_tokens": self.total_tokens,
            "total_cost_usd": round(self.total_cost_usd, 6),
            "total_latency_ms": round(self.total_latency_ms, 1),
            "avg_latency_ms": round(self.total_latency_ms / max(len(self.calls), 1), 1),
            "errors": sum(1 for c in self.calls if not c.success),
        }


class LLMClient:
    """
    Simple LLM client with tracking.

    Usage:
        client = LLMClient(model="openrouter/google/gemini-2.5-flash", api_key="sk-...")
        response = client.chat("اكتب إعلان عن iPhone 15")
        print(response)
        print(client.stats.summary())
    """

    def __init__(
        self,
        model: str = "openrouter/google/gemini-2.5-flash",
        api_key: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
    ):
        self.model = model
        self.api_key = api_key
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.stats = LLMStats()

    def chat(
        self,
        user_message: str,
        system_prompt: str = "",
        temperature: Optional[float] = None,
        json_mode: bool = False,
    ) -> str:
        """Send a message to the LLM and return the response text."""

        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": user_message})

        kwargs = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature if temperature is not None else self.temperature,
            "max_tokens": self.max_tokens,
        }
        if self.api_key:
            kwargs["api_key"] = self.api_key

        if self.model.startswith("ollama/"):
            kwargs["api_base"] = "http://localhost:11434"
            kwargs["num_gpu"] = 0
            kwargs["num_ctx"] = 2048

        if json_mode:
            kwargs["response_format"] = {"type": "json_object"}

        start = time.time()
        try:
            response = litellm.completion(**kwargs)
            latency = (time.time() - start) * 1000

            usage = response.usage
            try:
                cost = litellm.completion_cost(completion_response=response) if usage else 0.0
            except Exception:
                # Cost calculation can fail for some models
                cost = 0.0

            call = LLMCall(
                model=self.model,
                prompt_tokens=usage.prompt_tokens if usage else 0,
                completion_tokens=usage.completion_tokens if usage else 0,
                total_tokens=usage.total_tokens if usage else 0,
                cost_usd=cost,
                latency_ms=latency,
                success=True,
            )
            self.stats.add(call)

            return response.choices[0].message.content or ""

        except Exception as exc:
            latency = (time.time() - start) * 1000
            print(f"[LLM ERROR] {exc}")
            call = LLMCall(
                model=self.model,
                prompt_tokens=0,
                completion_tokens=0,
                total_tokens=0,
                cost_usd=0.0,
                latency_ms=latency,
                success=False,
                error=str(exc),
            )
            self.stats.add(call)
            raise

    def chat_json(
        self,
        user_message: str,
        system_prompt: str = "",
        temperature: Optional[float] = None,
    ) -> Dict[str, Any]:
        """Send a message and parse the response as JSON."""
        raw = self.chat(user_message, system_prompt, temperature, json_mode=True)

        # Try to extract JSON from the response
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            # Try to find JSON in the response
            start = raw.find("{")
            end = raw.rfind("}") + 1
            if start != -1 and end > start:
                return json.loads(raw[start:end])
            raise ValueError(f"Could not parse JSON from response: {raw[:200]}")

    def reset_stats(self):
        """Reset accumulated stats."""
        self.stats = LLMStats()
