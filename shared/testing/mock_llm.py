"""
Mock LLM — Deterministic LLM responses for testing without API keys.

Returns canned responses based on keywords in the prompt.
Tracks token usage for cost assertions.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class MockLLMResponse:
    """A mock LLM response."""

    content: str
    prompt_tokens: int = 0
    completion_tokens: int = 0
    model: str = "mock-llm-v1"


class MockLLM:
    """
    Deterministic mock LLM for testing.

    Usage:
        llm = MockLLM()
        response = await llm.generate("اكتب إعلان لمنتج")
        assert "منتج" in response.content
    """

    def __init__(self, seed: int = 42):
        self.seed = seed
        self.call_history: List[Dict[str, Any]] = []
        self._custom_responses: Dict[str, str] = {}

    def set_response(self, keyword: str, response: str) -> None:
        """Set a custom response for prompts containing keyword."""
        self._custom_responses[keyword] = response

    async def generate(
        self,
        prompt: str,
        temperature: float = 0.7,
        max_tokens: int = 1024,
    ) -> MockLLMResponse:
        """Generate a mock response based on prompt keywords."""
        self.call_history.append({
            "prompt": prompt[:200],
            "temperature": temperature,
            "max_tokens": max_tokens,
        })

        # Check custom responses first
        for keyword, response in self._custom_responses.items():
            if keyword in prompt:
                return MockLLMResponse(
                    content=response,
                    prompt_tokens=len(prompt.split()),
                    completion_tokens=len(response.split()),
                )

        # Default responses based on scenario keywords
        content = self._get_default_response(prompt)
        return MockLLMResponse(
            content=content,
            prompt_tokens=len(prompt.split()),
            completion_tokens=len(content.split()),
        )

    def _get_default_response(self, prompt: str) -> str:
        """Generate default response based on prompt content."""
        prompt_lower = prompt.lower()

        if "campaign" in prompt_lower or "حملة" in prompt:
            return (
                '{"campaign_name": "رمضان كريم 2025", '
                '"agent_assignments": {"content": "إعلانات", "deployer": "نشر"}, '
                '"channel_plan": {"meta": {"budget": 50000}}, '
                '"content_requirements": ["عربي خليجي", "إنجليزي"], '
                '"kpis": {"KSA": "ROAS > 3x"}, '
                '"compliance_checklist": ["PDPL", "consent"]}'
            )

        if "pii" in prompt_lower or "خصوصية" in prompt:
            return (
                '{"detected_pii": {"saudi_id": ["1234567890"], "phone": ["+966501234567"]}, '
                '"redacted_text": "تم إخفاء البيانات", '
                '"risk_level": "critical", '
                '"jurisdiction_applied": "KSA"}'
            )

        if "إعلان" in prompt or "ad copy" in prompt_lower:
            return (
                "🌙 رمضان كريم! خصم 30% على منتجاتنا المميزة. "
                "تسوّق الحين واستمتع بأفضل العروض. "
                "السعر: 299 ريال بدل 429 ريال. اطلب الحين!"
            )

        if "تحليل" in prompt or "roas" in prompt_lower:
            return (
                '{"meta_roas": 4.2, "snapchat_roas": 1.5, '
                '"recommendation": "نقل 50% من ميزانية Snapchat لـ Meta", '
                '"requires_approval": true}'
            )

        if "عميل" in prompt or "customer" in prompt_lower:
            return (
                "أهلاً وسهلاً! أتذكر إنك كنت مهتم بالـ Samsung Galaxy S24 "
                "باللون الأزرق. السعر بعد الخصم 2,999 ريال. "
                "تبي أحجزلك واحد؟"
            )

        return "تم تنفيذ المهمة بنجاح."

    @property
    def total_calls(self) -> int:
        """Total number of LLM calls made."""
        return len(self.call_history)

    @property
    def total_tokens(self) -> int:
        """Approximate total tokens used."""
        return sum(
            c.get("max_tokens", 0)
            for c in self.call_history
        )
