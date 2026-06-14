"""
Orchestrator abstraction - defines how agents are coordinated.

An orchestrator is responsible for:
1. Routing messages between agents
2. Managing task execution flow (sequential, parallel, conditional)
3. Maintaining shared state
4. Handling approvals and escalations
5. Error recovery and retries
6. Observability (tracing, logging, metrics)

This is the "glue" that makes a multi-agent system coherent, independent of
the underlying framework (CrewAI, LangGraph, Agno, etc.)
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Callable, Any, Set
from enum import Enum
from datetime import datetime
import uuid

from .agent import Agent, AgentRole
from .message import Message, MessageType
from .state import SharedState
from .gates import ApprovalManager, ApprovalGate


class WorkflowStatus(Enum):
    """Status of a workflow execution."""
    IDLE = "idle"
    RUNNING = "running"
    PAUSED = "paused"
    WAITING_FOR_APPROVAL = "waiting_for_approval"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class WorkflowExecution:
    """Represents a single workflow execution."""
    workflow_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    workflow_type: str = ""
    status: WorkflowStatus = WorkflowStatus.IDLE
    created_at: datetime = field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    input_context: Dict[str, Any] = field(default_factory=dict)
    output: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    
    # Tracing
    trace_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    messages: List[Message] = field(default_factory=list)
    
    def is_complete(self) -> bool:
        """Check if workflow has finished (successfully or not)."""
        return self.status in [
            WorkflowStatus.COMPLETED,
            WorkflowStatus.FAILED,
            WorkflowStatus.CANCELLED,
        ]


class Orchestrator(ABC):
    """
    Abstract base for orchestrators.
    
    Implementations (CrewAI, LangGraph, Agno adapters) inherit from this and
    implement the abstract methods to delegate to their framework-specific logic.
    
    This ensures all orchestrators have the same interface and can be swapped.
    """
    
    def __init__(
        self,
        orchestrator_id: str,
        agents: Dict[str, Agent],
        shared_state: Optional[SharedState] = None,
        approval_manager: Optional[ApprovalManager] = None,
    ):
        """
        Initialize orchestrator.
        
        Args:
            orchestrator_id: Unique ID for this orchestrator instance
            agents: Mapping of agent_id -> Agent instance
            shared_state: Shared state (if None, creates a new one)
            approval_manager: Approval gate manager (if None, creates a new one)
        """
        self.orchestrator_id = orchestrator_id
        self.agents = agents
        self.shared_state = shared_state or SharedState()
        self.approval_manager = approval_manager or ApprovalManager()
        
        self._executions: Dict[str, WorkflowExecution] = {}
        self._message_queue: List[Message] = []
        self._on_message: Optional[Callable] = None
        self._on_approval_needed: Optional[Callable] = None
    
    @abstractmethod
    async def execute_workflow(
        self,
        workflow_type: str,
        input_context: Dict[str, Any],
    ) -> WorkflowExecution:
        """
        Execute a workflow.
        
        Args:
            workflow_type: Type of workflow (e.g., "campaign_launch")
            input_context: Input parameters for the workflow
        
        Returns:
            WorkflowExecution with results
        """
        pass
    
    @abstractmethod
    async def delegate_task(
        self,
        task_id: str,
        target_agent_id: str,
        task_context: Dict[str, Any],
    ) -> Any:
        """
        Delegate a task to a specific agent.
        
        Args:
            task_id: Unique task ID
            target_agent_id: ID of agent to delegate to
            task_context: Task definition and context
        
        Returns:
            Result from agent
        """
        pass
    
    @abstractmethod
    async def route_message(self, message: Message) -> Optional[Message]:
        """
        Route a message to appropriate recipient and wait for response.
        
        Args:
            message: Message to route
        
        Returns:
            Response message
        """
        pass
    
    def broadcast_state_update(self, state_update: Dict[str, Any]) -> None:
        """
        Broadcast a state update to all agents.
        
        Args:
            state_update: State changes to propagate
        """
        pass
    
    def create_approval_gate(
        self,
        gate_type: str,
        action_description: str,
        required_approvers: Set[str],
        context: Optional[Dict[str, Any]] = None,
    ) -> ApprovalGate:
        """
        Create an approval gate for human decision.
        
        Args:
            gate_type: Type of gate
            action_description: Description of what needs approval
            required_approvers: Set of user IDs who must approve
            context: Additional context
        
        Returns:
            ApprovalGate instance
        """
        gate = self.approval_manager.create_gate(
            gate_type=gate_type,
            action_description=action_description,
            required_approvers=required_approvers,
            context=context,
        )
        
        if self._on_approval_needed:
            self._on_approval_needed(gate)
        
        return gate
    
    def get_execution(self, workflow_id: str) -> Optional[WorkflowExecution]:
        """Get a workflow execution by ID."""
        return self._executions.get(workflow_id)
    
    def get_agent_by_role(self, role: AgentRole) -> Optional[Agent]:
        """Find an agent by its role."""
        for agent in self.agents.values():
            if agent.capabilities.role == role:
                return agent
        return None
    
    def set_message_callback(self, callback: Callable[[Message], None]) -> None:
        """Set callback for message events."""
        self._on_message = callback
    
    def set_approval_callback(self, callback: Callable[[ApprovalGate], None]) -> None:
        """Set callback for approval gates."""
        self._on_approval_needed = callback


class SimpleOrchestrator(Orchestrator):
    """
    Simple reference implementation of Orchestrator.
    
    This shows how to implement the contract without relying on any framework.
    Real implementations (CrewAIOrchestrator, LangGraphOrchestrator, etc.) will
    delegate to their respective frameworks while maintaining this interface.
    """
    
    async def execute_workflow(
        self,
        workflow_type: str,
        input_context: Dict[str, Any],
    ) -> WorkflowExecution:
        """Execute workflow using sequential agent calls."""
        execution = WorkflowExecution(
            workflow_type=workflow_type,
            input_context=input_context,
            trace_id=str(uuid.uuid4()),
        )
        
        self._executions[execution.workflow_id] = execution
        execution.status = WorkflowStatus.RUNNING
        execution.started_at = datetime.now()
        
        try:
            # Orchestrator agent (if exists) drives the workflow
            orchestrator_agent = self.get_agent_by_role(AgentRole.ORCHESTRATOR)
            if orchestrator_agent:
                # Send initial task to orchestrator
                initial_message = Message(
                    message_type=MessageType.TASK_REQUEST,
                    sender_id=self.orchestrator_id,
                    recipient_id=orchestrator_agent.agent_id,
                    content={
                        "workflow_type": workflow_type,
                        "input_context": input_context,
                    },
                    trace_id=execution.trace_id,
                )
                
                response = await orchestrator_agent.process_message(initial_message)
                execution.messages.append(initial_message)
                execution.messages.append(response)
                execution.output = response.content
            
            execution.status = WorkflowStatus.COMPLETED
            
        except Exception as e:
            execution.status = WorkflowStatus.FAILED
            execution.error = str(e)
        
        finally:
            execution.completed_at = datetime.now()
        
        return execution
    
    async def delegate_task(
        self,
        task_id: str,
        target_agent_id: str,
        task_context: Dict[str, Any],
    ) -> Any:
        """Delegate task to agent."""
        agent = self.agents.get(target_agent_id)
        if not agent:
            raise ValueError(f"Agent {target_agent_id} not found")
        
        message = Message(
            message_type=MessageType.TASK_REQUEST,
            sender_id=self.orchestrator_id,
            recipient_id=target_agent_id,
            content={
                "task_id": task_id,
                "task_context": task_context,
            },
        )
        
        response = await agent.process_message(message)
        return response.content
    
    async def route_message(self, message: Message) -> Optional[Message]:
        """Route message to recipient."""
        if not message.recipient_id:
            return None
        
        agent = self.agents.get(message.recipient_id)
        if not agent:
            return None
        
        return await agent.process_message(message)
