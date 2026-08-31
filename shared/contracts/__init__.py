"""
Mizan Contracts — Abstract interfaces that every framework adapter must respect.

Import from here for convenience:
    from shared.contracts import Agent, Message, SharedState, Tool, Orchestrator
"""

from shared.contracts.agent import (
    Agent,
    AgentCapabilities,
    AgentRole,
    AgentState,
    AnalyticsAgent,
    ConversationalAgent,
    OrchestratorAgent,
)
from shared.contracts.message import (
    Message,
    MessagePriority,
    MessageType,
)
from shared.contracts.state import (
    SharedState,
    StateChange,
    StateOperation,
    StateSnapshot,
)
from shared.contracts.tool import (
    Tool,
    ToolCategory,
    ToolExecutionResult,
    ToolInvocation,
    ToolParameter,
)
from shared.contracts.gates import (
    ApprovalDecision,
    ApprovalGate,
    ApprovalManager,
    GateStatus,
)
from shared.contracts.orchestrator import (
    Orchestrator,
    SimpleOrchestrator,
    WorkflowExecution,
    WorkflowStatus,
)
from shared.contracts.adapter import (
    BaseFrameworkAdapter,
    ScenarioResult,
    AgentSpec,
    ToolSpec,
    ScenarioInput,
    TokenUsage,
    TraceEntry,
)

__all__ = [
    # Agent
    "Agent", "AgentCapabilities", "AgentRole", "AgentState",
    "AnalyticsAgent", "ConversationalAgent", "OrchestratorAgent",
    # Message
    "Message", "MessagePriority", "MessageType",
    # State
    "SharedState", "StateChange", "StateOperation", "StateSnapshot",
    # Tool
    "Tool", "ToolCategory", "ToolExecutionResult", "ToolInvocation", "ToolParameter",
    # Gates
    "ApprovalDecision", "ApprovalGate", "ApprovalManager", "GateStatus",
    # Orchestrator
    "Orchestrator", "SimpleOrchestrator", "WorkflowExecution", "WorkflowStatus",
    # Adapter
    "BaseFrameworkAdapter", "ScenarioResult", "AgentSpec", "ToolSpec",
    "ScenarioInput", "TokenUsage", "TraceEntry",
]
