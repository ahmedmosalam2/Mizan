"""
Core module: foundational abstractions for the multi-agent system.

This module provides framework-agnostic abstractions that all agents, tools,
and orchestrators must implement. Any framework adapter (CrewAI, LangGraph, Agno)
integrates by implementing these interfaces.

Structure:
- abstractions/: Core interfaces (Agent, Tool, Message, State, Orchestrator)
- observability.py: Tracing, logging, metrics
- services/: Framework-specific implementations
"""

from .base import (
    Agent,
    AgentRole,
    AgentState,
    Tool,
    ToolExecutionResult,
    Message,
    MessageType,
    SharedState,
    Orchestrator,
    ApprovalGate,
    GateStatus,
)
from .observability import (
    ObservabilityEvent,
    ObservabilityCollector,
    EventLevel,
    get_collector,
)

__all__ = [
    # Abstractions
    "Agent",
    "AgentRole",
    "AgentState",
    "Tool",
    "ToolExecutionResult",
    "Message",
    "MessageType",
    "SharedState",
    "Orchestrator",
    "ApprovalGate",
    "GateStatus",
    # Observability
    "ObservabilityEvent",
    "ObservabilityCollector",
    "EventLevel",
    "get_collector",
]
