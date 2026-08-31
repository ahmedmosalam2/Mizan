"""
Benchmark Scorer — Evaluates framework results against the 7-dimension rubrics.

Takes ScenarioResult objects and produces DimensionScore / FrameworkScore
for leaderboard comparison.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

from shared.contracts.adapter import ScenarioResult
from shared.scoring.rubrics import RUBRICS


@dataclass
class DimensionScore:
    """Score for a single dimension."""

    dimension: str
    score: float  # 0-10
    weight: float
    weighted_score: float  # score * weight
    sub_scores: Dict[str, float] = field(default_factory=dict)
    notes: List[str] = field(default_factory=list)


@dataclass
class FrameworkScore:
    """Complete score for one framework across all dimensions."""

    framework_name: str
    dimensions: Dict[str, DimensionScore] = field(default_factory=dict)
    total_score: float = 0.0  # weighted average, 0-10
    total_duration_ms: float = 0.0
    total_tokens: int = 0
    total_cost_usd: float = 0.0
    evaluated_at: str = ""

    def compute_total(self):
        """Compute weighted total from dimension scores."""
        self.total_score = sum(d.weighted_score for d in self.dimensions.values())
        self.evaluated_at = datetime.now().isoformat()


class BenchmarkScorer:
    """Evaluates framework results against rubrics."""

    def __init__(self):
        self.rubrics = RUBRICS

    # ── Scenario → Dimension mapping ─────────────────────────────

    DIMENSION_SCENARIO_MAP = {
        "orchestration": "campaign_planning",
        "tool_use": "content_generation",
        "safety": "pii_scan",
        "human_in_the_loop": "budget_approval",
        "memory": "cross_session_chat",
        "observability": "channel_deploy",
        "multimodal": "multimodal_ad",
    }

    def score_framework(
        self,
        framework_name: str,
        results: Dict[str, ScenarioResult],
    ) -> FrameworkScore:
        """Score a framework across all scenarios it completed."""
        fw_score = FrameworkScore(framework_name=framework_name)

        for dimension, scenario_id in self.DIMENSION_SCENARIO_MAP.items():
            result = results.get(scenario_id)
            if result:
                dim_score = self._score_dimension(dimension, result)
                fw_score.dimensions[dimension] = dim_score

                # Accumulate totals
                fw_score.total_duration_ms += result.total_duration_ms
                fw_score.total_tokens += result.token_usage.total_tokens
                fw_score.total_cost_usd += result.token_usage.estimated_cost_usd

        fw_score.compute_total()
        return fw_score

    def compare_frameworks(
        self, scores: List[FrameworkScore]
    ) -> Dict[str, FrameworkScore]:
        """Compare multiple frameworks and return sorted by score."""
        return {
            s.framework_name: s
            for s in sorted(scores, key=lambda s: s.total_score, reverse=True)
        }

    # ── Dimension scoring ────────────────────────────────────────

    def _score_dimension(
        self, dimension: str, result: ScenarioResult
    ) -> DimensionScore:
        """Score a single dimension based on scenario result."""
        rubric = self.rubrics.get(dimension, {})
        weight = rubric.get("weight", 0)
        sub_criteria = rubric.get("sub_criteria", {})

        sub_scores = {}
        notes = []
        total = 0.0

        for criterion_name, criterion in sub_criteria.items():
            score = self._evaluate_criterion(dimension, criterion_name, result)
            sub_scores[criterion_name] = score
            total += score * criterion["weight"]

        dim_score = DimensionScore(
            dimension=dimension,
            score=total,
            weight=weight,
            weighted_score=total * weight,
            sub_scores=sub_scores,
            notes=notes,
        )
        return dim_score

    def _evaluate_criterion(
        self, dimension: str, criterion: str, result: ScenarioResult
    ) -> float:
        """
        Evaluate a single sub-criterion.

        This uses heuristic checks on ScenarioResult flags.
        For more sophisticated evaluation, use llm_judge.py.
        """
        if result.status in ("failed", "timeout"):
            return 0.0

        # ── Orchestration ────────────────────────────────────────
        if dimension == "orchestration":
            if criterion == "multi_agent_creation":
                return min(10, result.agent_count * 2)
            elif criterion == "task_decomposition":
                return 7.0 if result.agent_count >= 3 else 4.0
            elif criterion == "parallel_execution":
                return 10.0 if result.used_parallel else 0.0
            elif criterion == "conditional_branching":
                return 10.0 if result.used_branching else 0.0
            elif criterion == "error_recovery":
                return 10.0 if result.used_retry else 0.0

        # ── Tool Use ────────────────────────────────────────────
        elif dimension == "tool_use":
            if criterion == "function_calling":
                return min(10, result.tool_calls * 2.5)
            elif criterion == "output_quality":
                return 7.0 if result.output else 0.0

        # ── Safety ──────────────────────────────────────────────
        elif dimension == "safety":
            if criterion in ("saudi_id_detection", "egyptian_id_detection"):
                return 10.0 if result.pii_detected else 0.0
            elif criterion == "pii_redaction":
                return 10.0 if result.pii_redacted else 0.0

        # ── HITL ────────────────────────────────────────────────
        elif dimension == "human_in_the_loop":
            if criterion == "pause_resume":
                return 10.0 if result.used_approval_gate else 0.0

        # ── Memory ──────────────────────────────────────────────
        elif dimension == "memory":
            if criterion == "cross_session_recall":
                return 7.0 if result.used_memory else 0.0

        # ── Observability ───────────────────────────────────────
        elif dimension == "observability":
            if criterion == "execution_trace":
                return min(10, len(result.trace) * 2)

        # Default: 5.0 for completed scenarios
        return 5.0 if result.status == "completed" else 0.0
