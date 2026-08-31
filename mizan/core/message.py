"""
Core Message & Trajectory Event Models for Mizan.

Defines the structured execution trajectory stream recorded during agent runs.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class MessageType(str, Enum):
    THOUGHT = "thought"
    TOOL_CALL = "tool_call"
    TOOL_RESPONSE = "tool_response"
    AGENT_MESSAGE = "agent_message"
    DECISION = "decision"
    DELEGATION = "delegation"
    HITL_PROMPT = "hitl_prompt"
    HITL_RESPONSE = "hitl_response"


class ToolCallRecord(BaseModel):
    """Execution record of a single tool invocation."""
    call_id: str
    tool_name: str
    input_args: Dict[str, Any] = Field(default_factory=dict)
    output_data: Any = None
    duration_ms: float = 0.0
    success: bool = True
    error_message: Optional[str] = None
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat())


class AgentMessage(BaseModel):
    """A single discrete step or message in an agent execution trajectory."""
    message_id: str
    run_id: str
    agent_name: str
    message_type: MessageType
    content: str
    tool_calls: List[ToolCallRecord] = Field(default_factory=list)
    tokens_used: int = 0
    duration_ms: float = 0.0
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat())
    metadata: Dict[str, Any] = Field(default_factory=dict)
