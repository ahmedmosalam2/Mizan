"""Agent Context - Shared state and communication between agents."""

from typing import Any, Dict, Optional, List
from pydantic import BaseModel, Field
from datetime import datetime
from copy import deepcopy


class AgentContext(BaseModel):
    """Context shared between agents during orchestrated execution."""
    
  
    workflow_id: str = Field(..., description="Unique workflow ID")
    task_id: str = Field(..., description="Current task ID")
    
    # Shared state
    shared_data: Dict[str, Any] = Field(default_factory=dict, description="Data shared across agents")
    step_count: int = Field(default=0, description="Number of agents executed")
    
    # Agent communication
    messages: List[Dict[str, Any]] = Field(default_factory=list, description="Message history")
    
    # Campaign/Domain context
    campaign_id: Optional[str] = Field(default=None)
    market: Optional[str] = Field(default=None)
    
    # Control
    execution_stopped: bool = Field(default=False)
    error_count: int = Field(default=0)
    max_errors: int = Field(default=3)
    
    # Timestamps
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    
    class Config:
        use_enum_values = True
    
    # ============== Public API ==============
    
    def set_data(self, key: str, value: Any) -> None:
        """Set shared data."""
        self.shared_data[key] = value
        self._update_timestamp()
    
    def get_data(self, key: str, default: Any = None) -> Any:
        """Get shared data."""
        return self.shared_data.get(key, default)
    
    def get_all_data(self) -> Dict[str, Any]:
        """Get all shared data."""
        return deepcopy(self.shared_data)
    
    def add_message(self, agent_name: str, message_type: str, content: Any) -> None:
        """Add message to history."""
        self.messages.append({
            "agent": agent_name,
            "type": message_type,
            "content": content,
            "timestamp": datetime.now().isoformat()
        })
        self._update_timestamp()
    
    def get_messages(self, agent_name: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get messages, optionally filtered by agent."""
        if agent_name:
            return [m for m in self.messages if m.get("agent") == agent_name]
        return deepcopy(self.messages)
    
    def increment_step(self) -> None:
        """Increment step counter."""
        self.step_count += 1
        self._update_timestamp()
    
    def increment_errors(self) -> bool:
        """Increment error count. Returns True if max errors exceeded."""
        self.error_count += 1
        self._update_timestamp()
        return self.error_count >= self.max_errors
    
    def should_stop(self) -> bool:
        """Check if execution should stop."""
        return self.execution_stopped or self.error_count >= self.max_errors
    
    def stop_execution(self, reason: str = "") -> None:
        """Stop execution."""
        self.execution_stopped = True
        self.add_message("system", "control", f"Execution stopped: {reason}")
        self._update_timestamp()
    
    def clone(self) -> "AgentContext":
        """Create a copy of context."""
        return AgentContext(**self.dict())
    
    # ============== Private ==============
    
    def _update_timestamp(self) -> None:
        """Update the updated_at timestamp."""
        self.updated_at = datetime.now()
