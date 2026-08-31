
import re
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field
from datetime import datetime

from benchmarks.scoring.rubrics import RUBRICS
from benchmarks.models import ScenarioResult
from benchmarks.scenarios.test_data import EXPECTED_PII_DETECTIONS


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
        self.total_score = sum(
            d.weighted_score for d in self.dimensions.values()
        )
        self.evaluated_at = datetime.now().isoformat()


class BenchmarkScorer:
    """Evaluates framework results against rubrics."""

    def __init__(self):
        self.rubrics = RUBRICS

    # ═══════════════════════════════════════════════════════════════
    # Main scoring entry point
    # ═══════════════════════════════════════════════════════════════

    def score_framework(
        self,
        framework_name: str,
        results: Dict[str, ScenarioResult],
    ) -> FrameworkScore:
        """
        Score a framework across all scenarios it completed.

        Args:
            framework_name: Name of the framework
            results: Map of scenario_id → ScenarioResult
        """
        fw_score = FrameworkScore(framework_name=framework_name)

        # Score each dimension based on corresponding scenario
        dimension_scenario_map = {
            "orchestration": "campaign_planning",
            "tool_use": "content_generation",
            "safety": "pii_scan",
            "human_in_the_loop": "budget_approval",
            "memory": "cross_session_chat",
            "observability": "channel_deploy",
            "multimodal": "multimodal_ad",
        }

        for dimension, scenario_id in dimension_scenario_map.items():
            result = results.get(scenario_id)
            if result:
                dim_score = self._score_dimension(dimension, result)
            else:
                dim_score = DimensionScore(
                    dimension=dimension,
                    score=0.0,
                    weight=self.rubrics[dimension]["weight"],
                    weighted_score=0.0,
                    notes=["Scenario not executed"],
                )
            fw_score.dimensions[dimension] = dim_score

        # Aggregate metrics
        for r in results.values():
            fw_score.total_duration_ms += r.total_duration_ms
            fw_score.total_tokens += r.token_usage.total_tokens
            fw_score.total_cost_usd += r.token_usage.estimated_cost_usd

        fw_score.compute_total()
        return fw_score

    # ═══════════════════════════════════════════════════════════════
    # Per-dimension scoring
    # ═══════════════════════════════════════════════════════════════

    def _score_dimension(
        self, dimension: str, result: ScenarioResult
    ) -> DimensionScore:
        """Score a single dimension based on its scenario result."""
        rubric = self.rubrics[dimension]
        weight = rubric["weight"]

        # Use automated scoring where possible, otherwise estimate
        scoring_methods = {
            "orchestration": self._score_orchestration,
            "tool_use": self._score_tool_use,
            "safety": self._score_safety,
            "human_in_the_loop": self._score_hitl,
            "memory": self._score_memory,
            "observability": self._score_observability,
            "multimodal": self._score_multimodal,
        }

        scorer_fn = scoring_methods.get(dimension, self._score_generic)
        sub_scores, notes = scorer_fn(result, rubric["sub_criteria"])

        # Compute weighted dimension score
        dimension_score = 0.0
        for criterion, criterion_info in rubric["sub_criteria"].items():
            criterion_weight = criterion_info["weight"]
            criterion_score = sub_scores.get(criterion, 0.0)
            dimension_score += criterion_score * criterion_weight

        return DimensionScore(
            dimension=dimension,
            score=round(dimension_score, 1),
            weight=weight,
            weighted_score=round(dimension_score * weight, 2),
            sub_scores=sub_scores,
            notes=notes,
        )

    # ═══════════════════════════════════════════════════════════════
    # Automated scoring functions
    # ═══════════════════════════════════════════════════════════════

    def _score_orchestration(
        self, result: ScenarioResult, criteria: Dict
    ) -> tuple:
        scores = {}
        notes = []

        if result.status == "failed":
            return {k: 0 for k in criteria}, ["Scenario failed completely"]

        # Multi-agent creation
        if result.agent_count >= 6:
            scores["multi_agent_creation"] = 10
        elif result.agent_count >= 4:
            scores["multi_agent_creation"] = 7
        elif result.agent_count >= 2:
            scores["multi_agent_creation"] = 4
        else:
            scores["multi_agent_creation"] = 0

        # Task decomposition — check output for sub-tasks
        output_str = str(result.output or "")
        task_indicators = ["sub-task", "subtask", "مهمة فرعية", "step", "خطوة"]
        task_count = sum(1 for t in task_indicators if t.lower() in output_str.lower())
        if task_count >= 3:
            scores["task_decomposition"] = 10
        elif task_count >= 2:
            scores["task_decomposition"] = 7
        else:
            scores["task_decomposition"] = 4
            notes.append("Limited task decomposition detected")

        # Sequential execution
        scores["sequential_execution"] = 10 if len(result.trace) > 1 else 5

        # Parallel execution
        scores["parallel_execution"] = 10 if result.used_parallel else 0

        # Conditional branching
        scores["conditional_branching"] = 10 if result.used_branching else 0

        # Error recovery
        scores["error_recovery"] = 10 if result.used_retry else 5

        # Inter-agent communication
        agent_names_in_trace = set(e.agent_name for e in result.trace if e.agent_name)
        if len(agent_names_in_trace) >= 3:
            scores["inter_agent_communication"] = 10
        elif len(agent_names_in_trace) >= 2:
            scores["inter_agent_communication"] = 5
        else:
            scores["inter_agent_communication"] = 0

        return scores, notes

    def _score_tool_use(self, result: ScenarioResult, criteria: Dict) -> tuple:
        scores = {}
        notes = []

        if result.status == "failed":
            return {k: 0 for k in criteria}, ["Scenario failed"]

        # Function calling
        if result.tool_calls >= 5:
            scores["function_calling"] = 10
        elif result.tool_calls >= 3:
            scores["function_calling"] = 7
        elif result.tool_calls >= 1:
            scores["function_calling"] = 4
        else:
            scores["function_calling"] = 0

        # RAG retrieval — check if product info appears in output
        output_str = str(result.output or "")
        product_keywords = ["فيلبس", "Philips", "899", "قلاية", "Air Fryer"]
        hits = sum(1 for k in product_keywords if k in output_str)
        scores["rag_retrieval"] = min(10, hits * 2.5)

        # API integration
        scores["api_integration"] = min(10, result.tool_calls * 2)

        # Tool chaining
        tool_trace = [e for e in result.trace if "tool" in e.action.lower()]
        scores["tool_chaining"] = 10 if len(tool_trace) >= 2 else 5 if len(tool_trace) >= 1 else 0

        # Output quality — basic length and language check
        if len(output_str) > 200 and any(c in output_str for c in "ابتثجحخدذ"):
            scores["output_quality"] = 8
            notes.append("Arabic content detected — manual quality review recommended")
        elif len(output_str) > 100:
            scores["output_quality"] = 5
        else:
            scores["output_quality"] = 2

        return scores, notes

    def _score_safety(self, result: ScenarioResult, criteria: Dict) -> tuple:
        scores = {}
        notes = []

        if result.status == "failed":
            return {k: 0 for k in criteria}, ["Safety scenario failed"]

        output = result.output or {}
        if not isinstance(output, dict):
            output = {"raw": str(output)}

        detected = output.get("detected_pii", {}) if isinstance(output, dict) else {}
        if not isinstance(detected, dict):
            detected = {}
        redacted_text = output.get("redacted_text", "") if isinstance(output, dict) else ""

        # Saudi ID detection
        expected_saudi = EXPECTED_PII_DETECTIONS["saudi_text"].get("saudi_national_id", [])
        found_saudi = detected.get("saudi_national_id", []) if isinstance(detected, dict) else []
        saudi_recall = len(set(found_saudi) & set(expected_saudi)) / max(len(expected_saudi), 1)
        scores["saudi_id_detection"] = round(saudi_recall * 10, 1)

        # Egyptian ID detection
        expected_eg = EXPECTED_PII_DETECTIONS["egyptian_text"].get("egyptian_national_id", [])
        found_eg = detected.get("egyptian_national_id", [])
        eg_recall = len(set(found_eg) & set(expected_eg)) / max(len(expected_eg), 1)
        scores["egyptian_id_detection"] = round(eg_recall * 10, 1)

        # Phone/email detection
        expected_phones = (
            EXPECTED_PII_DETECTIONS["saudi_text"].get("phone_numbers", []) +
            EXPECTED_PII_DETECTIONS["egyptian_text"].get("phone_numbers", [])
        )
        found_phones = detected.get("phone_numbers", [])
        phone_recall = len(set(found_phones) & set(expected_phones)) / max(len(expected_phones), 1)
        scores["phone_email_detection"] = round(phone_recall * 10, 1)

        # PII redaction
        if redacted_text:
            # Check if original PII is removed from redacted text
            all_pii = expected_saudi + expected_eg + expected_phones
            leaked = sum(1 for p in all_pii if p in redacted_text)
            if leaked == 0:
                scores["pii_redaction"] = 10
            else:
                scores["pii_redaction"] = max(0, 10 - leaked * 3)
        else:
            scores["pii_redaction"] = 0
            notes.append("No redacted text produced")

        # Jurisdiction awareness
        jurisdiction_terms = ["PDPL", "pdpl", "قانون حماية البيانات", "Law 151", "SDAIA"]
        has_jurisdiction = any(t in str(output) for t in jurisdiction_terms)
        scores["jurisdiction_awareness"] = 10 if has_jurisdiction else 0

        # Audit logging
        scores["audit_logging"] = 10 if result.pii_detected and len(result.trace) > 0 else 0

        return scores, notes

    def _score_hitl(self, result: ScenarioResult, criteria: Dict) -> tuple:
        scores = {}
        notes = []

        if result.status == "failed":
            return {k: 0 for k in criteria}, ["HITL scenario failed"]

        # Pause/resume
        scores["pause_resume"] = 10 if result.used_approval_gate else 0
        if not result.used_approval_gate:
            notes.append("No approval gate triggered — framework may lack HITL support")

        # Conditional gates
        output_str = str(result.output or "")
        if "20%" in output_str or "threshold" in output_str.lower() or "عتبة" in output_str:
            scores["conditional_gates"] = 10
        elif result.used_approval_gate:
            scores["conditional_gates"] = 5
        else:
            scores["conditional_gates"] = 0

        # Feedback injection
        if "feedback" in output_str.lower() or "WhatsApp" in output_str or "ملاحظات" in output_str:
            scores["feedback_injection"] = 7
            notes.append("Feedback acceptance detected — verify incorporation manually")
        else:
            scores["feedback_injection"] = 0

        # Multi-approver
        approver_terms = ["Marketing Manager", "Compliance", "مدير التسويق", "الامتثال"]
        approver_count = sum(1 for t in approver_terms if t in output_str)
        scores["multi_approver"] = 10 if approver_count >= 2 else 5 if approver_count >= 1 else 0

        return scores, notes

    def _score_memory(self, result: ScenarioResult, criteria: Dict) -> tuple:
        scores = {}
        notes = []

        if result.status == "failed":
            return {k: 0 for k in criteria}, ["Memory scenario failed"]

        output_str = str(result.output or "")

        # Cross-session recall — check for expected recalled items
        from benchmarks.scenarios.test_data import EXPECTED_RECALL
        recalls = sum(1 for item in EXPECTED_RECALL if item in output_str)
        recall_rate = recalls / len(EXPECTED_RECALL)
        scores["cross_session_recall"] = round(recall_rate * 10, 1)

        if recalls < len(EXPECTED_RECALL):
            notes.append(f"Recalled {recalls}/{len(EXPECTED_RECALL)} expected items")

        # Short-term context
        scores["short_term_context"] = 10 if result.status == "completed" else 5

        # Shared state
        scores["shared_state"] = 10 if result.used_memory else 0

        # Checkpointing
        scores["checkpointing"] = 5  # Hard to auto-evaluate, default to mid

        return scores, notes

    def _score_observability(self, result: ScenarioResult, criteria: Dict) -> tuple:
        scores = {}
        notes = []

        # Execution trace
        if len(result.trace) >= 6:
            scores["execution_trace"] = 10
        elif len(result.trace) >= 3:
            scores["execution_trace"] = 7
        elif len(result.trace) >= 1:
            scores["execution_trace"] = 4
        else:
            scores["execution_trace"] = 0

        # Token/cost tracking
        if result.token_usage.total_tokens > 0 and result.token_usage.estimated_cost_usd > 0:
            scores["token_cost_tracking"] = 10
        elif result.token_usage.total_tokens > 0:
            scores["token_cost_tracking"] = 5
        else:
            scores["token_cost_tracking"] = 0

        # Error handling (deployment scenario with injected failures)
        if result.used_retry and result.status == "completed":
            scores["error_handling"] = 10
        elif result.used_retry:
            scores["error_handling"] = 7
        elif result.status == "completed":
            scores["error_handling"] = 4
        else:
            scores["error_handling"] = 0

        # Structured logs
        has_structured = any(
            e.agent_name and e.action and e.timestamp for e in result.trace
        )
        scores["structured_logs"] = 10 if has_structured else 0

        return scores, notes

    def _score_multimodal(self, result: ScenarioResult, criteria: Dict) -> tuple:
        scores = {}
        notes = []

        if result.status == "failed":
            return {k: 0 for k in criteria}, ["Multimodal scenario failed"]

        output_str = str(result.output or "")

        # Image understanding
        if len(output_str) > 50 and any(c in output_str for c in "ابتثجح"):
            scores["image_understanding"] = 7
            notes.append("Arabic output from image detected — manual review for accuracy")
        elif len(output_str) > 50:
            scores["image_understanding"] = 4
        else:
            scores["image_understanding"] = 0

        # Content from image
        product_terms = ["قلاية", "فيلبس", "Philips", "Air Fryer", "هوائية"]
        refs = sum(1 for t in product_terms if t in output_str)
        scores["content_from_image"] = min(10, refs * 3)

        # Document handling — check if framework reported PDF support
        scores["document_handling"] = 5  # Default mid — hard to auto-test

        # Format compliance
        lines = output_str.strip().split("\n")
        if any(len(line) <= 40 for line in lines) and any(len(line) <= 125 for line in lines):
            scores["format_compliance"] = 7
        else:
            scores["format_compliance"] = 3

        return scores, notes

    def _score_generic(self, result: ScenarioResult, criteria: Dict) -> tuple:
        """Fallback scorer."""
        scores = {k: 5 for k in criteria}
        return scores, ["Generic scoring applied — manual review needed"]

    # ═══════════════════════════════════════════════════════════════
    # Comparison & Reporting
    # ═══════════════════════════════════════════════════════════════

    def compare_frameworks(
        self, all_scores: List[FrameworkScore]
    ) -> Dict[str, Any]:
        """Generate a comparison summary across all frameworks."""
        sorted_scores = sorted(all_scores, key=lambda s: s.total_score, reverse=True)

        comparison = {
            "ranking": [
                {
                    "rank": i + 1,
                    "framework": s.framework_name,
                    "total_score": round(s.total_score, 2),
                    "dimensions": {
                        dim: round(ds.score, 1)
                        for dim, ds in s.dimensions.items()
                    },
                    "total_tokens": s.total_tokens,
                    "total_cost_usd": round(s.total_cost_usd, 4),
                    "total_duration_ms": round(s.total_duration_ms, 1),
                }
                for i, s in enumerate(sorted_scores)
            ],
            "best_per_dimension": {},
            "evaluated_at": datetime.now().isoformat(),
            "frameworks_count": len(all_scores),
        }

        # Find best framework per dimension
        for dim in RUBRICS:
            best = max(all_scores, key=lambda s: s.dimensions.get(dim, DimensionScore(dim, 0, 0, 0)).score)
            comparison["best_per_dimension"][dim] = {
                "framework": best.framework_name,
                "score": round(best.dimensions[dim].score, 1) if dim in best.dimensions else 0,
            }

        return comparison
