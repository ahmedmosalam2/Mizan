"""
Core abstractions for the Multi-Agent Benchmarking Framework.

This module defines the interface contracts that all agents, tools, and orchestrators
must implement. These abstractions are framework-agnostic and enable seamless
switching between CrewAI, LangGraph, Agno, and other frameworks.

Design Principles:
- Single Responsibility: Each class has one reason to change
- Open/Closed: Easy to extend, hard to modify
- Liskov Substitution: Framework adapters are interchangeable
- Interface Segregation: Agents only depend on what they need
- Dependency Injection: Wired dependencies, not hard-coded
"""

from .agent import Agent, AgentRole, AgentState, AgentCapabilities
from .tool import Tool, ToolExecutionResult, ToolParameter, ToolCategory
from .message import Message, MessageType, MessagePriority
from .state import SharedState, StateOperation, StateChange
from .orchestrator import Orchestrator, WorkflowExecution, WorkflowStatus
from .gates import ApprovalGate, GateStatus, ApprovalManager, ApprovalDecision

__all__ = [
    "Agent",
    "AgentRole",
    "AgentState",
    "AgentCapabilities",
    "Tool",
    "ToolExecutionResult",
    "ToolParameter",
    "ToolCategory",
    "Message",
    "MessageType",
    "MessagePriority",
    "SharedState",
    "StateOperation",
    "StateChange",
    "Orchestrator",
    "WorkflowExecution",
    "WorkflowStatus",
    "ApprovalGate",
    "GateStatus",
    "ApprovalManager",
    "ApprovalDecision",
]
