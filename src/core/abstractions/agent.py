"""
Agent abstraction - the base contract for all agents in the system.

An Agent is an autonomous entity that:
1. Receives messages (observations/context)
2. Makes decisions based on its role and available tools
3. Takes actions (tool calls, delegations, or escalations)
4. Produces outputs (messages, state changes, events)

All agents, regardless of underlying framework, must implement this interface.
"""

from enum import Enum
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Callable, Set
from abc import ABC, abstractmethod
from datetime import datetime


class AgentRole(Enum):
    """Well-defined roles for agents in the multi-agent system."""
    ORCHESTRATOR = "orchestrator"           # Campaign Commander
    CONTENT_GENERATOR = "content_generator" # Content Architect
    CHANNEL_DEPLOYER = "channel_deployer"  # Channel Deployer
    ANALYTICS = "analytics"                 # Analytics & Optimization
    CUSTOMER_SERVICE = "customer_service"   # Customer Engagement
    COMPLIANCE = "compliance"               # Compliance Guardian


class AgentState(Enum):
    """Internal state of an agent's lifecycle."""
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
    tools: Set[str] = field(default_factory=set)           # Tool names available to this agent
    allowed_data_access: Set[str] = field(default_factory=set)  # What data can this agent read/write?
    max_iterations: int = 10                                # Prevent infinite loops
    timeout_seconds: int = 300                              # Max time for a single task
    requires_approval_for: List[str] = field(default_factory=list)  # Actions needing human approval


class Agent(ABC):
    """
    Abstract base class for all agents.
    
    Implements Liskov Substitution: any agent subclass can replace another
    without breaking the orchestrator.
    """
    
    def __init__(
        self,
        agent_id: str,
        capabilities: AgentCapabilities,
        allowed_tools: Optional[Dict[str, Any]] = None,
        on_state_change: Optional[Callable] = None,
    ):
        """
        Initialize an agent.
        
        Args:
            agent_id: Unique identifier for this agent instance
            capabilities: What this agent can do
            allowed_tools: Mapping of tool_name -> Tool instance
            on_state_change: Callback when agent state changes
        """
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
        """
        Core decision-making loop. An agent receives a message and must produce
        a response message.
        
        This is the main contract. Implementation varies by framework:
        - CrewAI: Uses CrewAI Task/Agent delegation
        - LangGraph: Uses state graph transitions
        - Agno: Uses async/await patterns
        
        But the signature is always: Message -> Message
        
        Args:
            message: Input message (observation, context, instruction)
        
        Returns:
            Output message (decision, action, or delegation)
        """
        pass
    
    @abstractmethod
    async def execute_tool(self, tool_name: str, **kwargs) -> Any:
        """
        Execute a tool by name with given parameters.
        
        Validates:
        1. Tool exists in allowed_tools
        2. Agent has permission to use this tool
        3. Parameters are valid
        
        Args:
            tool_name: Name of the tool to execute
            **kwargs: Parameters for the tool
        
        Returns:
            Result of tool execution
        
        Raises:
            ValueError: If tool not found or not permitted
            Exception: If tool execution fails
        """
        pass
    
    def get_memory_context(self, context_type: str = "short_term") -> Dict[str, Any]:
        """
        Retrieve memory context for decision-making.
        
        Args:
            context_type: "short_term" (current task), "long_term" (history), or "shared" (orchestrator state)
        
        Returns:
            Relevant context for this agent
        """
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
    """
    Specialized agent for conversational tasks (e.g., Customer Engagement).
    
    Adds conversation state management and turn-based interaction patterns.
    """
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._conversation_history: List[Dict[str, Any]] = []
        self._current_turn = 0
    
    async def process_conversation_turn(
        self,
        user_input: str,
        conversation_id: str,
    ) -> str:
        """
        Process a single conversation turn.
        
        Args:
            user_input: User's message
            conversation_id: Unique conversation ID
        
        Returns:
            Agent's response
        """
        raise NotImplementedError


class AnalyticsAgent(Agent):
    """
    Specialized agent for analytics and data processing tasks.
    
    Handles code execution, statistical analysis, and metric computation.
    """
    
    def __init__(self, *args, sandbox_enabled: bool = True, **kwargs):
        super().__init__(*args, **kwargs)
        self.sandbox_enabled = sandbox_enabled
    
    async def execute_analysis(
        self,
        analysis_type: str,
        data: Dict[str, Any],
        **params
    ) -> Dict[str, Any]:
        """
        Execute a specific analysis.
        
        Args:
            analysis_type: Type of analysis (e.g., "roas_calculation", "statistical_test")
            data: Input data for analysis
            **params: Analysis-specific parameters
        
        Returns:
            Analysis results
        """
        raise NotImplementedError


class OrchestratorAgent(Agent):
    """
    Specialized agent that manages other agents.
    
    Implements hierarchical orchestration:
    - Task decomposition
    - Delegation to sub-agents
    - Event aggregation
    - State synchronization
    """
    
    def __init__(self, *args, sub_agents: Optional[Dict[str, Agent]] = None, **kwargs):
        super().__init__(*args, **kwargs)
        self.sub_agents = sub_agents or {}
    
    async def delegate_task(
        self,
        task_id: str,
        target_agent_id: str,
        task_context: Dict[str, Any],
    ) -> Any:
        """
        Delegate a task to a sub-agent and wait for result.
        
        Args:
            task_id: Unique task ID
            target_agent_id: ID of agent to delegate to
            task_context: Task definition and context
        
        Returns:
            Result from sub-agent
        """
        raise NotImplementedError
    
    async def broadcast_state_update(self, state_update: Dict[str, Any]) -> None:
        """Broadcast shared state changes to all sub-agents."""
        raise NotImplementedError
