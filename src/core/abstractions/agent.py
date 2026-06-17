from enum import Enum
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Callable, Set
from abc import ABC, abstractmethod
from datetime import datetime


class AgentRole(Enum):
    
    ORCHESTRATOR = "orchestrator"          
    CONTENT_GENERATOR = "content_generator" 
    CHANNEL_DEPLOYER = "channel_deployer"  
    ANALYTICS = "analytics"                 
    CUSTOMER_SERVICE = "customer_service" 
    COMPLIANCE = "compliance"               



class AgentState(Enum):
    
    IDLE = "idle"
    THINKING = "thinking"
    EXECUTING = "executing"
    WAITING_FOR_APPROVAL = "waiting_for_approval"
    ERROR = "error"
    COMPLETED = "completed"


@dataclass
class AgentCapabilities:

    name: str
    description: str
    role: AgentRole
    tools: Set[str] = field(default_factory=set)           
    allowed_data_access: Set[str] = field(default_factory=set)  
    max_iterations: int = 10                                
    timeout_seconds: int = 300                            
    requires_approval_for: List[str] = field(default_factory=list)  


class Agent(ABC):

    
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
    
    @abstractmethod
    async def process_message(self, message: "Message") -> "Message":

        pass
    
    @abstractmethod
    async def execute_tool(self, tool_name: str, **kwargs) -> Any:

        pass
    
    def get_memory_context(self, context_type: str = "short_term") -> Dict[str, Any]:

        raise NotImplementedError(f"Agent {self.agent_id} must implement get_memory_context")
    
    def update_memory(self, key: str, value: Any, context_type: str = "short_term") -> None:
        """Update agent's memory with new information."""
        raise NotImplementedError(f"Agent {self.agent_id} must implement update_memory")
    
    def get_task_history(self, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """Retrieve historical tasks executed by this agent."""
        if limit:
            return self._task_history[-limit:]
        return self._task_history


class ConversationalAgent(Agent):

    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._conversation_history: List[Dict[str, Any]] = []
        self._current_turn = 0
    
    async def process_conversation_turn(
        self,
        user_input: str,
        conversation_id: str,
    ) -> str:

        raise NotImplementedError


class AnalyticsAgent(Agent):

    
    def __init__(self, *args, sandbox_enabled: bool = True, **kwargs):
        super().__init__(*args, **kwargs)
        self.sandbox_enabled = sandbox_enabled
    
    async def execute_analysis(
        self,
        analysis_type: str,
        data: Dict[str, Any],
        **params
    ) -> Dict[str, Any]:

        raise NotImplementedError


class OrchestratorAgent(Agent):

    
    def __init__(self, *args, sub_agents: Optional[Dict[str, Agent]] = None, **kwargs):
        super().__init__(*args, **kwargs)
        self.sub_agents = sub_agents or {}
    
    async def delegate_task(
        self,
        task_id: str,
        target_agent_id: str,
        task_context: Dict[str, Any],
    ) -> Any:

        raise NotImplementedError
    
    async def broadcast_state_update(self, state_update: Dict[str, Any]) -> None:
        """Broadcast shared state changes to all sub-agents."""
        raise NotImplementedError
