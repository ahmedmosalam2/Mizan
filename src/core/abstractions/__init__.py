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

from .agent import Agent, AgentRole, AgentState
from .tool import Tool, ToolExecutionResult
from .message import Message, MessageType
from .state import SharedState
from .orchestrator import Orchestrator
from .gates import ApprovalGate, GateStatus

__all__ = [
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
]
