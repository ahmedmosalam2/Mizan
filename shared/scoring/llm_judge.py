"""
LLM Judge — Uses an LLM to evaluate quality of Arabic content and dialect accuracy.

This is a subjective scorer that uses a judge LLM to rate:
    - Arabic dialect accuracy (Gulf vs Egyptian vs MSA)
    - Cultural appropriateness (Ramadan sensitivity)
    - Content quality (grammar, coherence, creativity)
    - Agreement logging for inter-rater reliability
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class JudgeVerdict:
    """Single verdict from the LLM judge."""

    criterion: str
    score: float  # 0-10
    rationale: str
    confidence: float = 0.0  # 0-1, how confident the judge is


@dataclass
class JudgeResult:
    """Complete judging result for a piece of content."""

    content_id: str
    verdicts: List[JudgeVerdict] = field(default_factory=list)
    overall_score: float = 0.0
    judge_model: str = ""
    judge_prompt_version: str = ""

    def compute_overall(self) -> float:
        """Average of all verdict scores."""
        if not self.verdicts:
            return 0.0
        self.overall_score = sum(v.score for v in self.verdicts) / len(self.verdicts)
        return self.overall_score


# ── Judge prompts ────────────────────────────────────────────────

DIALECT_JUDGE_PROMPT = """أنت مقيّم لغوي. قيّم النص التالي على مقياس 0-10:

النص:
{content}

اللهجة المطلوبة: {target_dialect}
السوق: {market}

معايير التقييم:
1. دقة اللهجة (0-10): هل النص باللهجة المطلوبة؟
2. الملاءمة الثقافية (0-10): هل يراعي حساسيات السوق والمناسبة؟
3. الجودة اللغوية (0-10): القواعد، التماسك، الإبداع
4. الملاءمة التسويقية (0-10): هل يصلح كإعلان؟

أجب بـ JSON:
{{
    "dialect_accuracy": {{"score": X, "rationale": "..."}},
    "cultural_fit": {{"score": X, "rationale": "..."}},
    "language_quality": {{"score": X, "rationale": "..."}},
    "marketing_fit": {{"score": X, "rationale": "..."}}
}}"""


async def judge_arabic_content(
    content: str,
    target_dialect: str = "gulf_arabic",
    market: str = "KSA",
    llm_call_fn: Optional[Any] = None,
) -> JudgeResult:
    """
    Use an LLM to judge Arabic content quality.

    Args:
        content: The Arabic text to evaluate
        target_dialect: Expected dialect (gulf_arabic, egyptian, msa)
        market: Target market (KSA, EG)
        llm_call_fn: Async function to call the judge LLM

    Returns:
        JudgeResult with per-criterion verdicts
    """
    result = JudgeResult(content_id=f"judge_{hash(content) % 10000}")

    if llm_call_fn is None:
        # Return placeholder scores if no LLM available
        for criterion in ["dialect_accuracy", "cultural_fit", "language_quality", "marketing_fit"]:
            result.verdicts.append(
                JudgeVerdict(
                    criterion=criterion,
                    score=5.0,
                    rationale="LLM judge not configured",
                    confidence=0.0,
                )
            )
        result.compute_overall()
        return result

    prompt = DIALECT_JUDGE_PROMPT.format(
        content=content,
        target_dialect=target_dialect,
        market=market,
    )

    try:
        import json
        response = await llm_call_fn(prompt)
        scores = json.loads(response)

        for criterion, data in scores.items():
            result.verdicts.append(
                JudgeVerdict(
                    criterion=criterion,
                    score=float(data.get("score", 5.0)),
                    rationale=data.get("rationale", ""),
                    confidence=0.8,
                )
            )
    except Exception:
        for criterion in ["dialect_accuracy", "cultural_fit", "language_quality", "marketing_fit"]:
            result.verdicts.append(
                JudgeVerdict(criterion=criterion, score=5.0, rationale="Judge parse error")
            )

    result.compute_overall()
    return result
