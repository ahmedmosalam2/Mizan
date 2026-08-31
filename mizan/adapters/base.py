"""
Adapter Base — The benchmark execution contract.

Defines:
    1. Structured per-dimension outputs (OrchestrationOutput, SafetyOutput, etc.)
    2. BenchmarkResult / ProbeResult
    3. Real RamadanScenario environment context (database connections, vector index, catalog, configs)
    4. BaseAdapter ABC implemented by each framework (CrewAI, LangGraph, AutoGen, etc.)
"""

from __future__ import annotations

import asyncio
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Literal, Optional

# ─────────────────────────────────────────────────────────────────────────────
# Probe Identifiers (7 Benchmark Dimensions)
# ─────────────────────────────────────────────────────────────────────────────

ProbeId = Literal[
    "orchestration",
    "tool_use",
    "safety",
    "hitl",
    "memory",
    "observability",
    "multimodal",
]

ALL_PROBES: List[ProbeId] = [
    "orchestration",
    "tool_use",
    "safety",
    "hitl",
    "memory",
    "observability",
    "multimodal",
]


# ─────────────────────────────────────────────────────────────────────────────
# Execution Trace
# ─────────────────────────────────────────────────────────────────────────────


@dataclass
class ToolCall:
    """A real tool invocation during agent execution."""
    tool_name: str
    input_params: Dict[str, Any]
    output: Any
    timestamp: str
    duration_ms: float
    success: bool
    agent_name: str = ""
    error: Optional[str] = None


@dataclass
class AgentStep:
    """One reasoning or action step by an agent."""
    agent_name: str
    step_type: Literal["thought", "tool_call", "message", "decision", "delegation"]
    content: str
    timestamp: str
    duration_ms: float
    tokens_used: int = 0
    tool_calls: List[ToolCall] = field(default_factory=list)


# ─────────────────────────────────────────────────────────────────────────────
# Per-Dimension Structured Outputs
# ─────────────────────────────────────────────────────────────────────────────


@dataclass
class OrchestrationOutput:
    """Dimension 1: Multi-Agent Orchestration & Planning."""
    agents_created: List[str] = field(default_factory=list)
    task_plan: List[Dict[str, Any]] = field(default_factory=list)
    execution_order: List[str] = field(default_factory=list)
    parallel_groups: List[List[str]] = field(default_factory=list)
    delegations: List[Dict[str, str]] = field(default_factory=list)
    retried_channels: List[str] = field(default_factory=list)
    fallbacks_applied: Dict[str, str] = field(default_factory=dict)
    campaign_plan: Optional[Dict[str, Any]] = None
    raw_response: Optional[str] = None


@dataclass
class ToolUseOutput:
    """Dimension 2: Real Tool Calling, RAG Vector Search & Code Execution."""
    rag_queries_made: List[str] = field(default_factory=list)
    products_retrieved: List[Dict[str, Any]] = field(default_factory=list)
    api_calls_made: List[Dict[str, Any]] = field(default_factory=list)
    code_executed: Optional[str] = None
    code_execution_result: Optional[Dict[str, Any]] = None
    arabic_content: Optional[str] = None
    english_content: Optional[str] = None
    target_market: Optional[str] = None


@dataclass
class SafetyOutput:
    """Dimension 3: Safety, Real PII Detection/Redaction & Consent Enforcement."""
    detections: Dict[str, List[str]] = field(default_factory=dict)
    redacted_texts: Dict[str, str] = field(default_factory=dict)
    jurisdiction_applied: Optional[str] = None
    audit_log_entries: List[Dict[str, Any]] = field(default_factory=list)
    customers_blocked: List[str] = field(default_factory=list)
    customers_allowed: List[str] = field(default_factory=list)


@dataclass
class HITLOutput:
    """Dimension 4: Human-in-the-Loop Approval Gates & State Pause/Resume."""
    gate_created: bool = False
    gate_id: Optional[str] = None
    workflow_paused: bool = False
    state_serialized: bool = False
    workflow_resumed: bool = False
    auto_approved_small_change: bool = False
    correct_threshold_applied: bool = False
    context_provided: Dict[str, Any] = field(default_factory=dict)


@dataclass
class MemoryOutput:
    """Dimension 5: Persistent & Cross-Session Memory."""
    recalled_product: Optional[str] = None
    recalled_price_sar: Optional[float] = None
    recalled_color: Optional[str] = None
    recalled_branch: Optional[str] = None
    re_asked_about: List[str] = field(default_factory=list)
    cross_session_linked: bool = False
    raw_agent_reply: Optional[str] = None


@dataclass
class ObservabilityOutput:
    """Dimension 6: Distributed Tracing, Logs & Token Costs."""
    trace_complete: bool = False
    has_trace_ids: bool = False
    trace_covers_tool_calls: bool = False
    token_tracking_granularity: Literal["none", "aggregate", "per_probe", "per_agent", "per_call"] = "none"
    structured_logs: bool = False
    injected_errors_captured: List[str] = field(default_factory=list)


@dataclass
class MultimodalOutput:
    """Dimension 7: Multimodal Vision & Ad Copy Generation."""
    image_processed: bool = False
    product_identified: Optional[str] = None
    generated_ad_copy_ar: Optional[str] = None
    generated_ad_copy_en: Optional[str] = None
    references_visual_details: bool = False
    raw_output: Optional[str] = None


# ─────────────────────────────────────────────────────────────────────────────
# ProbeResult & BenchmarkResult
# ─────────────────────────────────────────────────────────────────────────────


@dataclass
class ProbeResult:
    """Execution result of a single benchmark dimension probe."""
    probe: ProbeId
    status: Literal["completed", "failed", "timeout", "skipped"]
    output: (
        OrchestrationOutput
        | ToolUseOutput
        | SafetyOutput
        | HITLOutput
        | MemoryOutput
        | ObservabilityOutput
        | MultimodalOutput
        | Dict[str, Any]
    )
    steps: List[AgentStep] = field(default_factory=list)
    tool_calls: List[ToolCall] = field(default_factory=list)
    duration_ms: float = 0.0
    tokens_used: int = 0
    cost_usd: float = 0.0
    error: Optional[str] = None


@dataclass
class BenchmarkResult:
    """Aggregated benchmark outcome for one framework across all probes."""
    framework_name: str
    run_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    llm_model: str = ""
    probes: Dict[str, ProbeResult] = field(default_factory=dict)
    total_duration_ms: float = 0.0
    total_tokens: int = 0
    total_cost_usd: float = 0.0
    started_at: str = ""
    finished_at: str = ""

    def add_probe(self, result: ProbeResult) -> None:
        self.probes[result.probe] = result
        self.total_duration_ms += result.duration_ms
        self.total_tokens += result.tokens_used
        self.total_cost_usd += result.cost_usd

    @property
    def probes_completed(self) -> int:
        return sum(1 for r in self.probes.values() if r.status == "completed")

    @property
    def probes_failed(self) -> int:
        return sum(1 for r in self.probes.values() if r.status in ("failed", "timeout"))


# ─────────────────────────────────────────────────────────────────────────────
# RamadanScenario — The Real Environment Context
# ─────────────────────────────────────────────────────────────────────────────


@dataclass
class RamadanScenario:
    """
    Scenario environment context provided to framework adapters.
    Contains real datasets, database connection paths, vector index paths, and LLM configuration.
    """
    campaign_brief: Dict[str, Any]
    products: List[Dict[str, Any]]
    customers: List[Dict[str, Any]]
    channels: List[Dict[str, Any]]
    session_history: Dict[str, Any]
    pii_texts: Dict[str, str]
    ground_truth: Dict[str, Any]
    llm_config: Dict[str, Any]
    db_path: str = "mizan_ramadan.db"
    probes_to_run: List[ProbeId] = field(default_factory=lambda: list(ALL_PROBES))
    probe_timeouts: Dict[str, int] = field(
        default_factory=lambda: {
            "orchestration": 180,
            "tool_use": 120,
            "safety": 60,
            "hitl": 120,
            "memory": 90,
            "observability": 30,
            "multimodal": 120,
        }
    )


# ─────────────────────────────────────────────────────────────────────────────
# BaseAdapter
# ─────────────────────────────────────────────────────────────────────────────


class BaseAdapter(ABC):
    """Abstract base class implemented by each multi-agent framework."""
    framework_name: str = "base"

    async def setup(self, llm_config: Dict[str, Any]) -> None:
        """Initialize framework runtime and LLM clients."""
        pass

    async def teardown(self) -> None:
        """Clean up active processes and resources."""
        pass

    async def run(self, scenario: RamadanScenario) -> BenchmarkResult:
        """Run all requested probes through the framework."""
        result = BenchmarkResult(
            framework_name=self.framework_name,
            llm_model=scenario.llm_config.get("model", ""),
            started_at=datetime.now().isoformat(),
        )

        probe_methods = {
            "orchestration": self.run_orchestration,
            "tool_use": self.run_tool_use,
            "safety": self.run_safety,
            "hitl": self.run_hitl,
            "memory": self.run_memory,
            "multimodal": self.run_multimodal,
        }

        for probe_id in scenario.probes_to_run:
            if probe_id == "observability":
                continue
            if probe_id in probe_methods:
                method = probe_methods[probe_id]
                timeout = scenario.probe_timeouts.get(probe_id, 120)
                probe_res = await self._run_with_timeout(probe_id, method, scenario, timeout)
                result.add_probe(probe_res)

        if "observability" in scenario.probes_to_run:
            obs = self._evaluate_observability_from_trace(result)
            result.add_probe(obs)

        result.finished_at = datetime.now().isoformat()
        return result

    @abstractmethod
    async def run_orchestration(self, scenario: RamadanScenario) -> ProbeResult:
        """Execute real multi-agent task planning and execution flow."""
        pass

    @abstractmethod
    async def run_tool_use(self, scenario: RamadanScenario) -> ProbeResult:
        """Execute real vector RAG search, code analytics and content generation."""
        pass

    @abstractmethod
    async def run_safety(self, scenario: RamadanScenario) -> ProbeResult:
        """Execute real PII entity extraction/redaction and consent enforcement."""
        pass

    @abstractmethod
    async def run_hitl(self, scenario: RamadanScenario) -> ProbeResult:
        """Execute real human approval gate and conditional pause/resume flow."""
        pass

    @abstractmethod
    async def run_memory(self, scenario: RamadanScenario) -> ProbeResult:
        """Execute real cross-session conversation retrieval and customer memory recall."""
        pass

    @abstractmethod
    async def run_multimodal(self, scenario: RamadanScenario) -> ProbeResult:
        """Execute real image input analysis and vision-based ad generation."""
        pass

    async def _run_with_timeout(
        self,
        probe_id: ProbeId,
        method,
        scenario: RamadanScenario,
        timeout: int,
    ) -> ProbeResult:
        import time
        start = time.perf_counter()
        try:
            return await asyncio.wait_for(method(scenario), timeout=timeout)
        except asyncio.TimeoutError:
            elapsed = (time.perf_counter() - start) * 1000
            return ProbeResult(
                probe=probe_id,
                status="timeout",
                output={},
                duration_ms=elapsed,
                error=f"Probe exceeded {timeout}s timeout",
            )
        except NotImplementedError:
            return ProbeResult(
                probe=probe_id,
                status="skipped",
                output={},
                error="Not implemented",
            )
        except Exception as exc:
            elapsed = (time.perf_counter() - start) * 1000
            return ProbeResult(
                probe=probe_id,
                status="failed",
                output={},
                duration_ms=elapsed,
                error=f"{type(exc).__name__}: {exc}",
            )

    def _evaluate_observability_from_trace(self, result: BenchmarkResult) -> ProbeResult:
        import time
        start = time.perf_counter()
        all_steps = []
        all_tool_calls = []

        for p_id, p_res in result.probes.items():
            if p_id == "observability":
                continue
            all_steps.extend(p_res.steps)
            all_tool_calls.extend(p_res.tool_calls)

        has_trace = len(all_steps) > 0 or len(all_tool_calls) > 0
        token_granularity: Literal["none", "aggregate", "per_probe", "per_agent", "per_call"] = "aggregate"
        tokens_per_step = [s.tokens_used for s in all_steps if s.tokens_used > 0]
        if len(tokens_per_step) == len(all_steps) and len(all_steps) > 0:
            token_granularity = "per_call"
        elif tokens_per_step:
            token_granularity = "per_probe"

        output = ObservabilityOutput(
            trace_complete=has_trace,
            has_trace_ids=has_trace,
            trace_covers_tool_calls=len(all_tool_calls) > 0,
            token_tracking_granularity=token_granularity,
            structured_logs=True,
        )

        elapsed = (time.perf_counter() - start) * 1000
        return ProbeResult(
            probe="observability",
            status="completed",
            output=output,
            steps=all_steps,
            tool_calls=all_tool_calls,
            duration_ms=elapsed,
        )
