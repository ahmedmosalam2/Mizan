"""Agent Result Model - Unified response format for all agents."""

from typing import Any, Dict, Optional, List
from pydantic import BaseModel, Field
from enum import Enum
from datetime import datetime


class ResultStatus(str, Enum):
    """Status of agent execution."""
    SUCCESS = "success"
    FAILURE = "failure"
    PARTIAL = "partial"
    PENDING = "pending"


class AgentResult(BaseModel):
    """Unified result format from agent execution."""
    
    # Identification
    agent_name: str = Field(..., description="Name of the agent that produced this result")
    task_id: str = Field(..., description="Unique ID of the task being executed")
    
    # Status
    status: ResultStatus = Field(default=ResultStatus.SUCCESS)
    
    # Output
    data: Any = Field(default=None, description="Primary output data")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")
    
    # Error handling
    error: Optional[str] = Field(default=None, description="Error message if failed")
    error_type: Optional[str] = Field(default=None, description="Type of error")
    errors: List[Dict[str, Any]] = Field(default_factory=list, description="Detailed error list")
    
    # Performance metrics
    execution_time_ms: float = Field(default=0.0, description="Execution time in milliseconds")
    tokens_used: Optional[int] = Field(default=None, description="LLM tokens used")
    
    # Traceability
    created_at: datetime = Field(default_factory=datetime.now)
    agent_version: str = Field(default="1.0.0")
    
    # Next steps
    next_agent: Optional[str] = Field(default=None, description="Name of next agent to run")
    can_continue: bool = Field(default=True, description="Whether pipeline can continue")
    
    class Config:
        use_enum_values = True


class AgentResultBuilder:
    """Builder for creating AgentResult with fluent API."""
    
    def __init__(self, agent_name: str, task_id: str):
        self.result = AgentResult(agent_name=agent_name, task_id=task_id)
    
    def success(self, data: Any) -> "AgentResultBuilder":
        """Mark result as success."""
        self.result.status = ResultStatus.SUCCESS
        self.result.data = data
        return self
    
    def partial(self, data: Any) -> "AgentResultBuilder":
        """Mark result as partial success."""
        self.result.status = ResultStatus.PARTIAL
        self.result.data = data
        return self
    
    def failure(self, error: str, error_type: str = "Unknown") -> "AgentResultBuilder":
        """Mark result as failure."""
        self.result.status = ResultStatus.FAILURE
        self.result.error = error
        self.result.error_type = error_type
        return self
    
    def with_metadata(self, key: str, value: Any) -> "AgentResultBuilder":
        """Add metadata."""
        self.result.metadata[key] = value
        return self
    
    def with_execution_time(self, ms: float) -> "AgentResultBuilder":
        """Set execution time."""
        self.result.execution_time_ms = ms
        return self
    
    def with_tokens(self, tokens: int) -> "AgentResultBuilder":
        """Set tokens used."""
        self.result.tokens_used = tokens
        return self
    
    def next_step(self, agent_name: str, can_continue: bool = True) -> "AgentResultBuilder":
        """Set next agent in pipeline."""
        self.result.next_agent = agent_name
        self.result.can_continue = can_continue
        return self
    
    def add_error(self, message: str, **details) -> "AgentResultBuilder":
        """Add error details."""
        error_dict = {"message": message, **details}
        self.result.errors.append(error_dict)
        return self
    
    def build(self) -> AgentResult:
        """Build final result."""
        return self.result
