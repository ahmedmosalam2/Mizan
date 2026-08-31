"""
Agent Contract — Abstract base class for all agents in the Mizan benchmark.

Every agent in the system (Campaign Commander, Content Architect, etc.)
implements this interface. Framework adapters wrap these agents in their
native constructs (CrewAI Agent, LangGraph Node, etc.).

Design principles:
    - Single async entry point: process_message()
    - Declares capabilities upfront (role, tools, data access)
    - Maintains memory (short-term context + long-term history)
    - State transitions are explicit and observable
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set


class AgentRole(Enum):
    """Predefined roles for the 6 Ramadan campaign agents."""

    ORCHESTRATOR = "orchestrator"
    CONTENT_GENERATOR = "content_generator"
    CHANNEL_DEPLOYER = "channel_deployer"
    ANALYTICS = "analytics"
    CUSTOMER_SERVICE = "customer_service"
    COMPLIANCE = "compliance"


class AgentState(Enum):
    """Observable lifecycle states for an agent."""

    IDLE = "idle"
    THINKING = "thinking"
    EXECUTING = "executing"
    WAITING_FOR_APPROVAL = "waiting_for_approval"
    ERROR = "error"
    COMPLETED = "completed"


@dataclass
class AgentCapabilities:
    """Declarative description of what an agent can do."""

    name: str
    description: str
    role: AgentRole
    tools: Set[str] = field(default_factory=set)
    allowed_data_access: Set[str] = field(default_factory=set)
    max_iterations: int = 10
    timeout_seconds: int = 300
    requires_approval_for: List[str] = field(default_factory=list)


class Agent(ABC):
    """
    Abstract base class for all agents.

    Contract:
        - process_message()  →  the single async entry point
        - execute_tool()     →  invoke a tool by name
        - get_memory_context / update_memory  →  memory management
    """

    def __init__(
        self,
        agent_id: str,
        capabilities: AgentCapabilities,
        allowed_tools: Optional[Dict[str, Any]] = None,
        on_state_change: Optional[Callable] = None,
    ):
        self.agent_id = agent_id
        self.capabilities = capabilities
        self.allowed_tools = allowed_tools or {}
        self.on_state_change = on_state_change

        self._state = AgentState.IDLE
        self._last_activity = datetime.now()
        self._task_history: List[Dict[str, Any]] = []
        self._current_task_id: Optional[str] = None

    # ── State management ─────────────────────────────────────────

    @property
    def state(self) -> AgentState:
        """Current internal state of the agent."""
        return self._state

    def _set_state(self, new_state: AgentState) -> None:
        """Update agent state and trigger callbacks."""
        old_state = self._state
        self._state = new_state
        self._last_activity = datetime.now()

        if self.on_state_change:
            self.on_state_change(
                agent_id=self.agent_id,
                old_state=old_state,
                new_state=new_state,
                timestamp=self._last_activity,
            )

    # ── Core contract ────────────────────────────────────────────

    @abstractmethod
    async def process_message(self, message: "Message") -> "Message":
        """Process an incoming message and return a response."""
        pass

    @abstractmethod
    async def execute_tool(self, tool_name: str, **kwargs) -> Any:
        """Execute a tool by name with the given parameters."""
        pass

    # ── Memory ───────────────────────────────────────────────────

    def get_memory_context(self, context_type: str = "short_term") -> Dict[str, Any]:
        """Retrieve agent's memory context (short_term or long_term)."""
        raise NotImplementedError(
            f"Agent {self.agent_id} must implement get_memory_context"
        )

    def update_memory(
        self, key: str, value: Any, context_type: str = "short_term"
    ) -> None:
        """Update agent's memory with new information."""
        raise NotImplementedError(
            f"Agent {self.agent_id} must implement update_memory"
        )

    def get_task_history(self, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """Retrieve historical tasks executed by this agent."""
        if limit:
            return self._task_history[-limit:]
        return self._task_history


# ── Specialized Agent Types ──────────────────────────────────────


class ConversationalAgent(Agent):
    """Agent designed for multi-turn conversations (e.g., Customer Engagement)."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._conversation_history: List[Dict[str, Any]] = []
        self._current_turn = 0

    async def process_conversation_turn(
        self,
        user_input: str,
        conversation_id: str,
    ) -> str:
        """Process a single turn in a conversation."""
        raise NotImplementedError


class AnalyticsAgent(Agent):
    """Agent for analytics and code execution (e.g., ROAS calculation)."""

    def __init__(self, *args, sandbox_enabled: bool = True, **kwargs):
        super().__init__(*args, **kwargs)
        self.sandbox_enabled = sandbox_enabled

    async def execute_analysis(
        self,
        analysis_type: str,
        data: Dict[str, Any],
        **params,
    ) -> Dict[str, Any]:
        """Execute an analysis task in a sandboxed environment."""
        raise NotImplementedError


class OrchestratorAgent(Agent):
    """Agent that orchestrates other agents (e.g., Campaign Commander)."""

    def __init__(
        self, *args, sub_agents: Optional[Dict[str, Agent]] = None, **kwargs
    ):
        super().__init__(*args, **kwargs)
        self.sub_agents = sub_agents or {}

    async def delegate_task(
        self,
        task_id: str,
        target_agent_id: str,
        task_context: Dict[str, Any],
    ) -> Any:
        """Delegate a task to a sub-agent."""
        raise NotImplementedError

    async def broadcast_state_update(self, state_update: Dict[str, Any]) -> None:
        """Broadcast shared state changes to all sub-agents."""
        raise NotImplementedError
