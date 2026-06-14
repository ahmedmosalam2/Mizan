"""
Message abstraction - standardized communication between agents.

All inter-agent communication flows through messages. This ensures:
1. Traceability: every message is logged with timestamp and IDs
2. Serialization: messages can be stored, replayed, or transmitted
3. Type safety: structured message types prevent misunderstandings
4. Observability: end-to-end message tracing
"""

from dataclasses import dataclass, field, asdict
from typing import Any, Dict, Optional, List
from enum import Enum
from datetime import datetime
import uuid


class MessageType(Enum):
    """Types of messages in the system."""
    # Agent lifecycle
    TASK_REQUEST = "task_request"
    TASK_RESPONSE = "task_response"
    TASK_DELEGATION = "task_delegation"
    
    # Tool interactions
    TOOL_CALL = "tool_call"
    TOOL_RESULT = "tool_result"
    
    # Approvals and gates
    APPROVAL_REQUEST = "approval_request"
    APPROVAL_RESPONSE = "approval_response"
    
    # Events
    EVENT = "event"
    
    # State synchronization
    STATE_UPDATE = "state_update"
    STATE_QUERY = "state_query"
    
    # Human interactions
    HUMAN_INPUT = "human_input"
    ESCALATION = "escalation"
    
    # Control
    ERROR = "error"
    HEARTBEAT = "heartbeat"


class MessagePriority(Enum):
    """Message priority for queueing and processing."""
    LOW = 0
    NORMAL = 1
    HIGH = 2
    CRITICAL = 3


@dataclass
class Message:
    """
    Core message structure for inter-agent communication.
    
    Attributes:
        message_id: Unique message identifier (for tracing)
        message_type: Type of message
        sender_id: ID of agent/component sending this message
        recipient_id: ID of agent/component receiving this message (None = broadcast)
        content: Main payload
        context: Additional context (conversation ID, workflow ID, etc.)
        priority: Processing priority
        timestamp: When message was created
        trace_id: For distributed tracing across agents
        parent_message_id: If this is a response, ID of the message it responds to
        metadata: Additional observability data
    """
    
    message_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    message_type: MessageType = MessageType.TASK_REQUEST
    sender_id: str = ""
    recipient_id: Optional[str] = None  # None = broadcast
    content: Dict[str, Any] = field(default_factory=dict)
    context: Dict[str, Any] = field(default_factory=dict)
    priority: MessagePriority = MessagePriority.NORMAL
    timestamp: datetime = field(default_factory=datetime.now)
    trace_id: Optional[str] = None  # For distributed tracing
    parent_message_id: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        """Generate trace_id if not provided."""
        if self.trace_id is None:
            self.trace_id = str(uuid.uuid4())
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize message to dict."""
        return {
            "message_id": self.message_id,
            "message_type": self.message_type.value,
            "sender_id": self.sender_id,
            "recipient_id": self.recipient_id,
            "content": self.content,
            "context": self.context,
            "priority": self.priority.value,
            "timestamp": self.timestamp.isoformat(),
            "trace_id": self.trace_id,
            "parent_message_id": self.parent_message_id,
            "metadata": self.metadata,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Message":
        """Deserialize message from dict."""
        data_copy = data.copy()
        
        # Convert string enums back to enums
        if isinstance(data_copy.get("message_type"), str):
            data_copy["message_type"] = MessageType(data_copy["message_type"])
        if isinstance(data_copy.get("priority"), int):
            data_copy["priority"] = MessagePriority(data_copy["priority"])
        
        # Convert timestamp string back to datetime
        if isinstance(data_copy.get("timestamp"), str):
            data_copy["timestamp"] = datetime.fromisoformat(data_copy["timestamp"])
        
        return cls(**data_copy)
    
    def create_response(
        self,
        response_type: MessageType,
        sender_id: str,
        content: Dict[str, Any],
    ) -> "Message":
        """
        Create a response message to this message.
        
        Args:
            response_type: Type of response
            sender_id: ID of the responding agent
            content: Response content
        
        Returns:
            New Message with proper linkage
        """
        return Message(
            message_type=response_type,
            sender_id=sender_id,
            recipient_id=self.sender_id,  # Response goes back to sender
            content=content,
            context=self.context,  # Preserve context
            trace_id=self.trace_id,  # Same trace
            parent_message_id=self.message_id,
        )


# Concrete message types

@dataclass
class TaskRequestMessage(Message):
    """Message requesting an agent to perform a task."""
    message_type: MessageType = field(default=MessageType.TASK_REQUEST, init=False)
    
    def __post_init__(self):
        super().__post_init__()
        # content should have: task_id, task_description, parameters


@dataclass
class TaskResponseMessage(Message):
    """Message with result of a completed task."""
    message_type: MessageType = field(default=MessageType.TASK_RESPONSE, init=False)
    
    def __post_init__(self):
        super().__post_init__()
        # content should have: task_id, result, success, error (if any)


@dataclass
class ToolCallMessage(Message):
    """Message representing a tool invocation."""
    message_type: MessageType = field(default=MessageType.TOOL_CALL, init=False)
    
    def __post_init__(self):
        super().__post_init__()
        # content should have: tool_name, parameters


@dataclass
class ToolResultMessage(Message):
    """Message with result of a tool execution."""
    message_type: MessageType = field(default=MessageType.TOOL_RESULT, init=False)
    
    def __post_init__(self):
        super().__post_init__()
        # content should have: tool_name, result (ToolExecutionResult)


@dataclass
class ApprovalRequestMessage(Message):
    """Message requesting human approval for an action."""
    message_type: MessageType = field(default=MessageType.APPROVAL_REQUEST, init=False)
    
    def __post_init__(self):
        super().__post_init__()
        # content should have: action_description, required_approvers, context


@dataclass
class ApprovalResponseMessage(Message):
    """Message with human approval decision."""
    message_type: MessageType = field(default=MessageType.APPROVAL_RESPONSE, init=False)
    
    def __post_init__(self):
        super().__post_init__()
        # content should have: approved, approver_id, decision_rationale


@dataclass
class EventMessage(Message):
    """Message representing a system event."""
    message_type: MessageType = field(default=MessageType.EVENT, init=False)
    
    def __post_init__(self):
        super().__post_init__()
        # content should have: event_type, event_data


@dataclass
class StateUpdateMessage(Message):
    """Message updating shared state."""
    message_type: MessageType = field(default=MessageType.STATE_UPDATE, init=False)
    
    def __post_init__(self):
        super().__post_init__()
        # content should have: state_key, state_value, operation (set/increment/append)


@dataclass
class ErrorMessage(Message):
    """Message reporting an error."""
    message_type: MessageType = field(default=MessageType.ERROR, init=False)
    
    def __post_init__(self):
        super().__post_init__()
        # content should have: error_code, error_description, stack_trace (optional)
