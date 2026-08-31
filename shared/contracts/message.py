"""
Message Contract — Inter-agent communication protocol.

Every interaction between agents flows through Message objects.
Messages are typed (TASK_REQUEST, TOOL_CALL, APPROVAL_REQUEST, etc.)
to make routing explicit and debuggable.

Design:
    - message_id   → unique identifier for tracing
    - trace_id     → links all messages in a workflow
    - parent_id    → conversation threading
    - message_type → explicit type (not implicit JSON)
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, Optional
import uuid


class MessageType(Enum):
    """Explicit message types for inter-agent communication."""

    # Task delegation
    TASK_REQUEST = "task_request"
    TASK_RESPONSE = "task_response"
    TASK_DELEGATION = "task_delegation"

    # Tool usage
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
    """Priority levels for message routing."""

    LOW = 0
    NORMAL = 1
    HIGH = 2
    CRITICAL = 3


@dataclass
class Message:
    """
    Core message object for all inter-agent communication.

    Usage:
        msg = Message(
            message_type=MessageType.TASK_REQUEST,
            sender_id="commander",
            recipient_id="content_architect",
            content={"task": "Generate ad copy for SKU-101"},
        )
    """

    message_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    message_type: MessageType = MessageType.TASK_REQUEST
    sender_id: str = ""
    recipient_id: Optional[str] = None  # None = broadcast
    content: Dict[str, Any] = field(default_factory=dict)
    context: Dict[str, Any] = field(default_factory=dict)
    priority: MessagePriority = MessagePriority.NORMAL
    timestamp: datetime = field(default_factory=datetime.now)
    trace_id: Optional[str] = None
    parent_message_id: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        """Generate trace_id if not provided."""
        if self.trace_id is None:
            self.trace_id = str(uuid.uuid4())

    def to_dict(self) -> Dict[str, Any]:
        """Serialize message to dict for storage/transmission."""
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

        if isinstance(data_copy.get("message_type"), str):
            data_copy["message_type"] = MessageType(data_copy["message_type"])
        if isinstance(data_copy.get("priority"), int):
            data_copy["priority"] = MessagePriority(data_copy["priority"])
        if isinstance(data_copy.get("timestamp"), str):
            data_copy["timestamp"] = datetime.fromisoformat(data_copy["timestamp"])

        return cls(**data_copy)

    def create_response(
        self,
        response_type: MessageType,
        sender_id: str,
        content: Dict[str, Any],
    ) -> "Message":
        """Create a response message that preserves trace and context."""
        return Message(
            message_type=response_type,
            sender_id=sender_id,
            recipient_id=self.sender_id,
            content=content,
            context=self.context,
            trace_id=self.trace_id,
            parent_message_id=self.message_id,
        )
