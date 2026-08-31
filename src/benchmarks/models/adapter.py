from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field
from datetime import datetime

from benchmarks.models.enums import ScenarioType


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
class ScenarioResult:
    """Standard output from a benchmark scenario run."""
    scenario_id: str
    framework_name: str
    status: str = "not_started"  # not_started | running | completed | failed | timeout
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


class BaseFrameworkAdapter(ABC):
    """
    Abstract base class that every framework adapter must implement.

    This is the ONLY interface Mizan uses to interact with any framework.
    Each method maps to one of the 7 benchmark dimensions.
    """

    def __init__(self, framework_name: str, config: Optional[Dict] = None):
        self.framework_name = framework_name
        self.config = config or {}
        self._token_usage = TokenUsage()
        self._trace: List[TraceEntry] = []
        self._is_setup = False

    # ═══════════════════════════════════════════════════════════════
    # Lifecycle
    # ═══════════════════════════════════════════════════════════════

    @abstractmethod
    async def setup(self, llm_config: Dict[str, Any]) -> None:
        """
        Initialize the framework with LLM configuration.

        Args:
            llm_config: {"provider": "groq", "model": "...", "api_key": "..."}
        """
        ...

    @abstractmethod
    async def teardown(self) -> None:
        """Clean up framework resources."""
        ...

    # ═══════════════════════════════════════════════════════════════
    # Dimension 1: Agent Orchestration
    # ═══════════════════════════════════════════════════════════════

    @abstractmethod
    async def run_orchestration(
        self,
        agent_specs: List[AgentSpec],
        task: Dict[str, Any],
        orchestration_mode: str = "sequential",  # sequential | parallel | hierarchical
    ) -> ScenarioResult:
        """
        Test multi-agent orchestration capabilities.
        """
        ...

    # ═══════════════════════════════════════════════════════════════
    # Dimension 2: Tool Use
    # ═══════════════════════════════════════════════════════════════

    @abstractmethod
    async def run_with_tools(
        self,
        agent_specs: List[AgentSpec],
        task: Dict[str, Any],
        tools: List[ToolSpec],
    ) -> ScenarioResult:
        """
        Test tool calling, RAG, and external API integration.
        """
        ...

    # ═══════════════════════════════════════════════════════════════
    # Dimension 3: Safety & Privacy
    # ═══════════════════════════════════════════════════════════════

    @abstractmethod
    async def run_safety_check(
        self,
        text_with_pii: str,
        pii_types: List[str],
        jurisdiction: str,  # "KSA" | "EG" | "both"
    ) -> ScenarioResult:
        """
        Test PII detection, content filtering, and compliance.
        """
        ...

    # ═══════════════════════════════════════════════════════════════
    # Dimension 4: Human-in-the-Loop
    # ═══════════════════════════════════════════════════════════════

    @abstractmethod
    async def run_with_approval(
        self,
        agent_specs: List[AgentSpec],
        task: Dict[str, Any],
        approval_rules: Dict[str, Any],
        simulated_approvals: List[Dict[str, Any]],
    ) -> ScenarioResult:
        """
        Test human approval gates and workflow pausing.
        """
        ...

    # ═══════════════════════════════════════════════════════════════
    # Dimension 5: Memory & State
    # ═══════════════════════════════════════════════════════════════

    @abstractmethod
    async def run_with_memory(
        self,
        conversation_history: List[Dict[str, str]],
        follow_up_query: str,
        expected_recall: List[str],
    ) -> ScenarioResult:
        """
        Test cross-session memory and shared state.
        """
        ...

    # ═══════════════════════════════════════════════════════════════
    # Dimension 6: Observability
    # ═══════════════════════════════════════════════════════════════

    @abstractmethod
    async def run_with_tracing(
        self,
        agent_specs: List[AgentSpec],
        task: Dict[str, Any],
        inject_failure: Optional[Dict[str, Any]] = None,
    ) -> ScenarioResult:
        """
        Test tracing, error handling, and cost tracking.
        """
        ...

    # ═══════════════════════════════════════════════════════════════
    # Dimension 7: Multimodal
    # ═══════════════════════════════════════════════════════════════

    @abstractmethod
    async def run_multimodal(
        self,
        image_path: Optional[str],
        document_path: Optional[str],
        task: Dict[str, Any],
    ) -> ScenarioResult:
        """
        Test image understanding and document handling.
        """
        ...

    # ═══════════════════════════════════════════════════════════════
    # Utility Methods (shared by all adapters)
    # ═══════════════════════════════════════════════════════════════

    async def call_llm_gateway(
        self,
        prompt: str,
        scenario: Optional[str] = None,
        system_instruction: str = "",
        provider: Optional[str] = None,
        model: Optional[str] = None,
    ) -> str:
        """
        Call the centralized LLM Gateway middleware.
        Provides caching, multi-provider failover, and automatic token tracking.
        """
        from core.services.llm_gateway import LLMGateway, GatewayChatRequest

        if not hasattr(self, "_gateway"):
            self._gateway = LLMGateway()

        request = GatewayChatRequest(
            prompt=prompt,
            scenario=scenario,
            system_instruction=system_instruction,
            provider=provider or self.config.get("provider"),
            model=model or self.config.get("model"),
        )

        response = await self._gateway.chat(request)

        # Track tokens automatically
        self.update_tokens(
            prompt=response.tokens.get("input", 0),
            completion=response.tokens.get("output", 0),
            model=response.model,
        )
        self._token_usage.estimated_cost_usd += response.cost_usd

        return response.text

    def add_trace(self, entry: TraceEntry) -> None:
        """Add an entry to the execution trace."""
        if not entry.timestamp:
            entry.timestamp = datetime.now().isoformat()
        self._trace.append(entry)

    def get_trace(self) -> List[TraceEntry]:
        """Get the full execution trace."""
        return self._trace.copy()

    def update_tokens(self, prompt: int = 0, completion: int = 0,
                      model: str = "", cost_per_1m: float = 0.0) -> None:
        """Update cumulative token usage."""
        self._token_usage.prompt_tokens += prompt
        self._token_usage.completion_tokens += completion
        self._token_usage.total_tokens += (prompt + completion)
        if model:
            self._token_usage.model_name = model
        if cost_per_1m > 0:
            self._token_usage.estimated_cost_usd += (
                (prompt + completion) / 1_000_000 * cost_per_1m
            )

    def get_token_usage(self) -> TokenUsage:
        """Get cumulative token usage."""
        return self._token_usage

    def reset_metrics(self) -> None:
        """Reset trace and token counters between scenarios."""
        self._trace = []
        self._token_usage = TokenUsage()

    def _make_result(self, scenario_id: str, **kwargs) -> ScenarioResult:
        """Helper to create a ScenarioResult with common fields filled."""
        return ScenarioResult(
            scenario_id=scenario_id,
            framework_name=self.framework_name,
            token_usage=self.get_token_usage(),
            trace=self.get_trace(),
            **kwargs,
        )
