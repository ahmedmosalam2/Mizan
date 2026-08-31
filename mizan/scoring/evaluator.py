"""
Benchmark Evaluator — Scores BenchmarkResult outputs against Ground Truth & Rubrics.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

from mizan.adapters.base import (
    BenchmarkResult,
    HITLOutput,
    MemoryOutput,
    MultimodalOutput,
    ObservabilityOutput,
    OrchestrationOutput,
    ProbeResult,
    SafetyOutput,
    ToolUseOutput,
)
from mizan.scoring.rubrics import RUBRICS


@dataclass
class DimensionScore:
    """Score for a single benchmark dimension."""
    dimension: str
    score: float  # 0.0 to 10.0
    weight: float
    weighted_score: float
    sub_scores: Dict[str, float] = field(default_factory=dict)
    feedback: List[str] = field(default_factory=list)


@dataclass
class EvaluationReport:
    """Complete evaluation report for a framework."""
    framework_name: str
    total_score: float = 0.0  # 0.0 to 10.0
    dimension_scores: Dict[str, DimensionScore] = field(default_factory=dict)
    total_duration_ms: float = 0.0
    total_tokens: int = 0
    total_cost_usd: float = 0.0
    probes_completed: int = 0
    probes_failed: int = 0
    evaluated_at: str = field(default_factory=lambda: datetime.now().isoformat())


class BenchmarkEvaluator:
    """Evaluates benchmark outcomes based on real evidence and ground truth."""

    def evaluate(self, result: BenchmarkResult, ground_truth: Dict[str, Any]) -> EvaluationReport:
        report = EvaluationReport(
            framework_name=result.framework_name,
            total_duration_ms=result.total_duration_ms,
            total_tokens=result.total_tokens,
            total_cost_usd=result.total_cost_usd,
            probes_completed=result.probes_completed,
            probes_failed=result.probes_failed,
        )

        dim_evaluators = {
            "orchestration": self._eval_orchestration,
            "tool_use": self._eval_tool_use,
            "safety": self._eval_safety,
            "hitl": self._eval_hitl,
            "memory": self._eval_memory,
            "observability": self._eval_observability,
            "multimodal": self._eval_multimodal,
        }

        total_weighted = 0.0
        for dim_name, rubric in RUBRICS.items():
            probe_key = "hitl" if dim_name == "human_in_the_loop" else dim_name
            probe_result = result.probes.get(probe_key)

            if not probe_result or probe_result.status in ("failed", "timeout", "skipped"):
                dim_score = DimensionScore(
                    dimension=dim_name,
                    score=0.0,
                    weight=rubric["weight"],
                    weighted_score=0.0,
                    feedback=[f"Probe status: {probe_result.status if probe_result else 'not_run'}"],
                )
            else:
                eval_fn = dim_evaluators.get(probe_key, self._eval_generic)
                dim_score = eval_fn(probe_result, ground_truth.get(probe_key, {}), rubric)

            report.dimension_scores[dim_name] = dim_score
            total_weighted += dim_score.weighted_score

        report.total_score = round(total_weighted, 2)
        return report

    # ── Dimension 1: Orchestration ───────────────────────────────────────────

    def _eval_orchestration(self, probe: ProbeResult, gt: Dict[str, Any], rubric: Dict[str, Any]) -> DimensionScore:
        out: OrchestrationOutput = probe.output if isinstance(probe.output, OrchestrationOutput) else OrchestrationOutput()
        sub_scores = {}
        feedback = []

        # 1. multi_agent_creation (up to 10)
        agent_cnt = len(out.agents_created)
        sub_scores["multi_agent_creation"] = min(10.0, agent_cnt * 1.67)

        # 2. task_decomposition (up to 10)
        tasks_cnt = len(out.task_plan)
        sub_scores["task_decomposition"] = 10.0 if tasks_cnt >= 4 else (tasks_cnt * 2.5)

        # 3. sequential_execution (up to 10)
        sub_scores["sequential_execution"] = 10.0 if len(out.execution_order) >= 2 else 5.0

        # 4. parallel_execution (up to 10)
        parallel_cnt = len(out.parallel_groups)
        sub_scores["parallel_execution"] = 10.0 if parallel_cnt >= 1 else 0.0

        # 5. conditional_branching (up to 10)
        sub_scores["conditional_branching"] = 10.0 if len(out.fallbacks_applied) > 0 else 0.0

        # 6. error_recovery (up to 10)
        sub_scores["error_recovery"] = 10.0 if len(out.retried_channels) > 0 else 0.0

        # 7. inter_agent_communication (up to 10)
        sub_scores["inter_agent_communication"] = 10.0 if len(out.delegations) > 0 else 5.0

        # Weighted calculation
        total = sum(sub_scores[k] * rubric["sub_criteria"][k]["weight"] for k in sub_scores)
        return DimensionScore(
            dimension="orchestration",
            score=round(total, 2),
            weight=rubric["weight"],
            weighted_score=round(total * rubric["weight"], 2),
            sub_scores=sub_scores,
            feedback=feedback,
        )

    # ── Dimension 2: Tool Use ────────────────────────────────────────────────

    def _eval_tool_use(self, probe: ProbeResult, gt: Dict[str, Any], rubric: Dict[str, Any]) -> DimensionScore:
        out: ToolUseOutput = probe.output if isinstance(probe.output, ToolUseOutput) else ToolUseOutput()
        sub_scores = {}

        # 1. function_calling
        calls_cnt = len(probe.tool_calls)
        sub_scores["function_calling"] = min(10.0, calls_cnt * 3.3)

        # 2. rag_retrieval
        retrieved_cnt = len(out.products_retrieved)
        sub_scores["rag_retrieval"] = 10.0 if retrieved_cnt > 0 else 0.0

        # 3. api_integration
        sub_scores["api_integration"] = 10.0 if len(out.api_calls_made) > 0 else 5.0

        # 4. tool_chaining
        sub_scores["tool_chaining"] = 10.0 if (retrieved_cnt > 0 and len(out.api_calls_made) > 0) else 5.0

        # 5. output_quality
        has_ar = bool(out.arabic_content and len(out.arabic_content) > 20)
        has_en = bool(out.english_content and len(out.english_content) > 20)
        sub_scores["output_quality"] = 10.0 if (has_ar and has_en) else (7.0 if has_ar else 3.0)

        total = sum(sub_scores[k] * rubric["sub_criteria"][k]["weight"] for k in sub_scores)
        return DimensionScore(
            dimension="tool_use",
            score=round(total, 2),
            weight=rubric["weight"],
            weighted_score=round(total * rubric["weight"], 2),
            sub_scores=sub_scores,
        )

    # ── Dimension 3: Safety & Privacy ────────────────────────────────────────

    def _eval_safety(self, probe: ProbeResult, gt: Dict[str, Any], rubric: Dict[str, Any]) -> DimensionScore:
        out: SafetyOutput = probe.output if isinstance(probe.output, SafetyOutput) else SafetyOutput()
        sub_scores = {}

        # 1. saudi_id_detection
        sa_detected = set(out.detections.get("saudi_national_id", []))
        gt_sa = set(gt.get("must_detect_ksa_ids", []))
        sub_scores["saudi_id_detection"] = 10.0 if (gt_sa and gt_sa.issubset(sa_detected)) else (5.0 if sa_detected else 0.0)

        # 2. egyptian_id_detection
        eg_detected = set(out.detections.get("egyptian_national_id", []))
        gt_eg = set(gt.get("must_detect_eg_ids", []))
        sub_scores["egyptian_id_detection"] = 10.0 if (gt_eg and gt_eg.issubset(eg_detected)) else (5.0 if eg_detected else 0.0)

        # 3. phone_email_detection
        phones = len(out.detections.get("phone", []))
        emails = len(out.detections.get("email", []))
        sub_scores["phone_email_detection"] = 10.0 if (phones >= 2 and emails >= 2) else 5.0

        # 4. pii_redaction
        has_redactions = any("[REDACTED" in t for t in out.redacted_texts.values())
        sub_scores["pii_redaction"] = 10.0 if has_redactions else 0.0

        # 5. jurisdiction_awareness
        sub_scores["jurisdiction_awareness"] = 10.0 if out.jurisdiction_applied else 5.0

        # 6. audit_logging
        sub_scores["audit_logging"] = 10.0 if len(out.audit_log_entries) > 0 else 0.0

        total = sum(sub_scores[k] * rubric["sub_criteria"][k]["weight"] for k in sub_scores)
        return DimensionScore(
            dimension="safety",
            score=round(total, 2),
            weight=rubric["weight"],
            weighted_score=round(total * rubric["weight"], 2),
            sub_scores=sub_scores,
        )

    # ── Dimension 4: Human-in-the-Loop ───────────────────────────────────────

    def _eval_hitl(self, probe: ProbeResult, gt: Dict[str, Any], rubric: Dict[str, Any]) -> DimensionScore:
        out: HITLOutput = probe.output if isinstance(probe.output, HITLOutput) else HITLOutput()
        sub_scores = {}

        sub_scores["pause_resume"] = 10.0 if (out.gate_created and out.workflow_resumed) else (5.0 if out.gate_created else 0.0)
        sub_scores["conditional_gates"] = 10.0 if (out.auto_approved_small_change and out.correct_threshold_applied) else 5.0
        sub_scores["feedback_injection"] = 10.0 if out.workflow_resumed else 5.0
        sub_scores["multi_approver"] = 10.0 if bool(out.context_provided) else 5.0

        total = sum(sub_scores[k] * rubric["sub_criteria"][k]["weight"] for k in sub_scores)
        return DimensionScore(
            dimension="human_in_the_loop",
            score=round(total, 2),
            weight=rubric["weight"],
            weighted_score=round(total * rubric["weight"], 2),
            sub_scores=sub_scores,
        )

    # ── Dimension 5: Memory & State ──────────────────────────────────────────

    def _eval_memory(self, probe: ProbeResult, gt: Dict[str, Any], rubric: Dict[str, Any]) -> DimensionScore:
        out: MemoryOutput = probe.output if isinstance(probe.output, MemoryOutput) else MemoryOutput()
        sub_scores = {}

        recalled_p = bool(out.recalled_product and ("فيليبس" in out.recalled_product or "airfryer" in out.recalled_product.lower()))
        recalled_pr = bool(out.recalled_price_sar and abs(out.recalled_price_sar - 764.0) < 1.0)
        recalled_col = bool(out.recalled_color and ("أبيض" in out.recalled_color or "white" in out.recalled_color.lower()))
        recalled_br = bool(out.recalled_branch and ("الرياض" in out.recalled_branch or "riyadh" in out.recalled_branch.lower()))

        recall_score = sum([recalled_p, recalled_pr, recalled_col, recalled_br]) * 2.5
        sub_scores["cross_session_recall"] = recall_score
        sub_scores["short_term_context"] = 10.0 if out.cross_session_linked else 5.0
        sub_scores["shared_state"] = 10.0 if recall_score >= 7.5 else 5.0
        sub_scores["checkpointing"] = 10.0 if len(out.re_asked_about) == 0 else 0.0

        total = sum(sub_scores[k] * rubric["sub_criteria"][k]["weight"] for k in sub_scores)
        return DimensionScore(
            dimension="memory",
            score=round(total, 2),
            weight=rubric["weight"],
            weighted_score=round(total * rubric["weight"], 2),
            sub_scores=sub_scores,
        )

    # ── Dimension 6: Observability ───────────────────────────────────────────

    def _eval_observability(self, probe: ProbeResult, gt: Dict[str, Any], rubric: Dict[str, Any]) -> DimensionScore:
        out: ObservabilityOutput = probe.output if isinstance(probe.output, ObservabilityOutput) else ObservabilityOutput()
        sub_scores = {}

        sub_scores["execution_trace"] = 10.0 if out.trace_complete else 5.0
        sub_scores["token_cost_tracking"] = 10.0 if out.token_tracking_granularity in ("per_call", "per_agent", "per_probe") else 5.0
        sub_scores["error_handling"] = 10.0 if out.trace_covers_tool_calls else 5.0
        sub_scores["structured_logs"] = 10.0 if out.structured_logs else 5.0

        total = sum(sub_scores[k] * rubric["sub_criteria"][k]["weight"] for k in sub_scores)
        return DimensionScore(
            dimension="observability",
            score=round(total, 2),
            weight=rubric["weight"],
            weighted_score=round(total * rubric["weight"], 2),
            sub_scores=sub_scores,
        )

    # ── Dimension 7: Multimodal ──────────────────────────────────────────────

    def _eval_multimodal(self, probe: ProbeResult, gt: Dict[str, Any], rubric: Dict[str, Any]) -> DimensionScore:
        out: MultimodalOutput = probe.output if isinstance(probe.output, MultimodalOutput) else MultimodalOutput()
        sub_scores = {}

        sub_scores["image_understanding"] = 10.0 if out.image_processed else 5.0
        sub_scores["content_from_image"] = 10.0 if (out.generated_ad_copy_ar and len(out.generated_ad_copy_ar) > 20) else 0.0
        sub_scores["document_handling"] = 10.0 if out.product_identified else 5.0
        sub_scores["format_compliance"] = 10.0 if out.references_visual_details else 5.0

        total = sum(sub_scores[k] * rubric["sub_criteria"][k]["weight"] for k in sub_scores)
        return DimensionScore(
            dimension="multimodal",
            score=round(total, 2),
            weight=rubric["weight"],
            weighted_score=round(total * rubric["weight"], 2),
            sub_scores=sub_scores,
        )

    def _eval_generic(self, probe: ProbeResult, gt: Dict[str, Any], rubric: Dict[str, Any]) -> DimensionScore:
        return DimensionScore(
            dimension=probe.probe,
            score=5.0 if probe.status == "completed" else 0.0,
            weight=rubric["weight"],
            weighted_score=5.0 * rubric["weight"] if probe.status == "completed" else 0.0,
        )
