"""
Framework Adapter Contract — The interface every framework must implement.

This is the single most important file in the benchmark. Every framework
(CrewAI, LangGraph, AutoGen, etc.) implements BaseFrameworkAdapter to plug
into the Mizan runner. The adapter translates between Mizan's generic
ScenarioInput and the framework's native constructs.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional


# ── Scenario Types ───────────────────────────────────────────────


class ScenarioType(Enum):
    """Types of benchmark scenarios."""

    ORCHESTRATION = "orchestration"
    TOOL_USE = "tool_use"
    SAFETY = "safety"
    HUMAN_IN_THE_LOOP = "human_in_the_loop"
    MEMORY = "memory"
    OBSERVABILITY = "observability"
    MULTIMODAL = "multimodal"


# ── Data Models ──────────────────────────────────────────────────


@dataclass
class ToolSpec:
    """Specification for a tool to be provided to agents."""

    name: str
    description: str
    function: Any  # callable
    parameters: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AgentSpec:
    """Standard agent specification — framework-agnostic."""

    name: str
    role: str
    goal: str
    backstory: str
    tools: List[ToolSpec] = field(default_factory=list)
    can_delegate: bool = False
    memory: bool = True


@dataclass
class TokenUsage:
    """Token consumption tracking."""

    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    estimated_cost_usd: float = 0.0
    model_name: str = ""


@dataclass
class TraceEntry:
    """Single entry in the execution trace."""

    timestamp: str = ""
    agent_name: str = ""
    action: str = ""
    input_summary: str = ""
    output_summary: str = ""
    duration_ms: float = 0.0
    tokens: Optional[TokenUsage] = None
    error: Optional[str] = None


@dataclass
class ScenarioInput:
    """Standard input for a benchmark scenario."""

    scenario_id: str
    scenario_type: ScenarioType
    description: str
    task_goal: str
    context: Dict[str, Any] = field(default_factory=dict)
    agent_specs: List[AgentSpec] = field(default_factory=list)
    tools: List[ToolSpec] = field(default_factory=list)
    expected_behavior: Dict[str, Any] = field(default_factory=dict)
    timeout_seconds: float = 120.0


@dataclass
class ScenarioResult:
    """Standard output from a benchmark scenario run."""

    scenario_id: str
    framework_name: str
    status: str = "not_started"  # not_started | running | completed | failed | timeout

    # Output
    output: Any = None
    error: Optional[str] = None

    # Performance
    total_duration_ms: float = 0.0
    token_usage: TokenUsage = field(default_factory=TokenUsage)

    # Traceability
    trace: List[TraceEntry] = field(default_factory=list)
    agent_count: int = 0
    tool_calls: int = 0

    # Behavior flags (set by scenario evaluator)
    used_parallel: bool = False
    used_branching: bool = False
    used_retry: bool = False
    used_memory: bool = False
    used_approval_gate: bool = False
    pii_detected: bool = False
    pii_redacted: bool = False

    started_at: str = ""
    finished_at: str = ""


# ── Base Adapter ─────────────────────────────────────────────────


class BaseFrameworkAdapter(ABC):
    """
    Abstract base class that every framework adapter must implement.

    Lifecycle:
        1. setup()       → initialize the framework + LLM
        2. run_*()       → execute scenarios
        3. teardown()    → clean up

    Each run_* method receives a standardized input and returns ScenarioResult.
    """

    def __init__(self, framework_name: str):
        self.framework_name = framework_name
        self._metrics: Dict[str, Any] = {}

    # ── Lifecycle ────────────────────────────────────────────────

    @abstractmethod
    async def setup(self, llm_config: Dict[str, Any]) -> None:
        """Initialize framework with LLM configuration."""
        pass

    @abstractmethod
    async def teardown(self) -> None:
        """Clean up framework resources."""
        pass

    def reset_metrics(self) -> None:
        """Reset per-scenario metrics."""
        self._metrics = {}

    # ── Scenario Methods ─────────────────────────────────────────

    @abstractmethod
    async def run_orchestration(
        self,
        agent_specs: List[AgentSpec],
        task: Dict[str, Any],
        orchestration_mode: str = "sequential",
    ) -> ScenarioResult:
        """Run orchestration scenario (s01-s04)."""
        pass

    @abstractmethod
    async def run_with_tools(
        self,
        agent_specs: List[AgentSpec],
        task: Dict[str, Any],
        tools: List[ToolSpec],
    ) -> ScenarioResult:
        """Run tool-use scenario (s05-s06)."""
        pass

    @abstractmethod
    async def run_safety_check(
        self,
        text_with_pii: str,
        pii_types: List[str],
        jurisdiction: str,
    ) -> ScenarioResult:
        """Run safety/PII scenario (s07-s09)."""
        pass

    @abstractmethod
    async def run_hitl(
        self,
        agent_specs: List[AgentSpec],
        task: Dict[str, Any],
        approval_rules: Dict[str, Any],
        simulated_approvals: Dict[str, Any],
    ) -> ScenarioResult:
        """Run human-in-the-loop scenario (s10-s12)."""
        pass

    @abstractmethod
    async def run_memory(
        self,
        agent_specs: List[AgentSpec],
        conversation_history: Dict[str, Any],
        follow_up: Dict[str, Any],
    ) -> ScenarioResult:
        """Run memory/cross-session scenario (s13-s15)."""
        pass

    @abstractmethod
    async def run_observability(
        self,
        agent_specs: List[AgentSpec],
        task: Dict[str, Any],
    ) -> ScenarioResult:
        """Run observability scenario (tracing, logging)."""
        pass

    @abstractmethod
    async def run_multimodal(
        self,
        agent_specs: List[AgentSpec],
        task: Dict[str, Any],
    ) -> ScenarioResult:
        """Run multimodal scenario (s16)."""
        pass
