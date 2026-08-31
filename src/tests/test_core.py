"""
Unit tests for core abstractions and example implementations.

Tests validate:
1. Agent interface compliance
2. Tool execution and error handling
3. Message passing and tracing
4. State management (SharedState)
5. Approval gates
6. Orchestration patterns
"""

import pytest
import asyncio
from datetime import datetime, timedelta

from ..core.base import (
    Agent, AgentRole, AgentState,
    Message, MessageType, MessagePriority,
    SharedState, StateOperation, StateChange,
    ApprovalGate, ApprovalManager, GateStatus, ApprovalDecision,
)
from ..examples.agents import EchoAgent, CalculatorAgent, EchoTool, CalculatorTool


# ═══════════════════════════════════════════════════════════════
# Message Tests
# ═══════════════════════════════════════════════════════════════

def test_message_creation():
    """Test basic message creation."""
    msg = Message(
        message_type=MessageType.TASK_REQUEST,
        sender_id="agent1",
        recipient_id="agent2",
        content={"task": "test"},
    )
    
    assert msg.sender_id == "agent1"
    assert msg.recipient_id == "agent2"
    assert msg.message_id is not None
    assert msg.trace_id is not None
    assert msg.parent_message_id is None


def test_message_serialization():
    """Test message to_dict and from_dict."""
    msg = Message(
        message_type=MessageType.TOOL_CALL,
        sender_id="agent1",
        content={"tool": "echo"},
    )
    
    # Serialize
    data = msg.to_dict()
    assert data["sender_id"] == "agent1"
    assert data["message_type"] == "tool_call"
    
    # Deserialize
    restored = Message.from_dict(data)
    assert restored.sender_id == msg.sender_id
    assert restored.message_type == msg.message_type


def test_message_response_creation():
    """Test creating a response message."""
    original = Message(
        message_type=MessageType.TASK_REQUEST,
        sender_id="agent1",
        recipient_id="agent2",
        content={"task": "calculate"},
    )
    
    response = original.create_response(
        response_type=MessageType.TASK_RESPONSE,
        sender_id="agent2",
        content={"result": 42},
    )
    
    assert response.parent_message_id == original.message_id
    assert response.trace_id == original.trace_id
    assert response.recipient_id == original.sender_id
    assert response.sender_id == "agent2"


# ═══════════════════════════════════════════════════════════════
# SharedState Tests
# ═══════════════════════════════════════════════════════════════

def test_shared_state_basic():
    """Test basic state get/set."""
    state = SharedState(initial_data={"counter": 0})
    
    assert state.get("counter") == 0
    
    state.set("counter", 5, actor_id="agent1")
    assert state.get("counter") == 5


def test_shared_state_increment():
    """Test state increment operation."""
    state = SharedState(initial_data={"count": 10})
    
    state.increment("count", 5, actor_id="agent1")
    assert state.get("count") == 15
    
    state.increment("count", -3, actor_id="agent1")
    assert state.get("count") == 12


def test_shared_state_append():
    """Test state append operation."""
    state = SharedState(initial_data={"items": []})
    
    state.append("items", "item1", actor_id="agent1")
    state.append("items", "item2", actor_id="agent1")
    
    items = state.get("items")
    assert len(items) == 2
    assert items[0] == "item1"


def test_shared_state_versioning():
    """Test state versioning and history."""
    state = SharedState(initial_data={"x": 0})
    
    state.set("x", 1, actor_id="agent1")
    state.set("x", 2, actor_id="agent2")
    
    history = state.get_history(key="x")
    assert len(history) == 2
    assert history[0].new_value == 1
    assert history[1].new_value == 2


def test_shared_state_checkpoint():
    """Test state checkpointing for resilience."""
    state = SharedState(initial_data={"status": "running"})
    state.set("count", 5, actor_id="agent1")
    
    # Checkpoint
    checkpoint = state.checkpoint()
    assert checkpoint["version"] > 0
    assert checkpoint["data"]["status"] == "running"
    
    # Restore from checkpoint
    restored = SharedState.from_checkpoint(checkpoint)
    assert restored.get("status") == "running"
    assert restored.get("count") == 5


# ═══════════════════════════════════════════════════════════════
# Tool Tests
# ═══════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_echo_tool():
    """Test echo tool execution."""
    tool = EchoTool()
    
    result = await tool.execute(
        agent_id="test_agent",
        message="Hello",
    )
    
    assert result.success is True
    assert result.data["echoed"] == "Hello"


@pytest.mark.asyncio
async def test_calculator_tool():
    """Test calculator tool."""
    tool = CalculatorTool()
    
    result = await tool.execute(
        agent_id="test_agent",
        expression="2 + 2",
    )
    
    assert result.success is True
    assert result.data["result"] == 4


@pytest.mark.asyncio
async def test_calculator_tool_error():
    """Test calculator error handling."""
    tool = CalculatorTool()
    
    result = await tool.execute(
        agent_id="test_agent",
        expression="1 / 0",  # Division by zero
    )
    
    assert result.success is False
    assert result.error is not None


@pytest.mark.asyncio
async def test_tool_parameter_validation():
    """Test parameter validation."""
    tool = EchoTool()
    
    # Missing required parameter
    result = await tool.execute(agent_id="test_agent")  # No 'message' parameter
    
    # Should fail validation
    assert result.success is False


# ═══════════════════════════════════════════════════════════════
# Agent Tests
# ═══════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_echo_agent_basic():
    """Test echo agent message processing."""
    agent = EchoAgent()
    
    msg = Message(
        message_type=MessageType.TASK_REQUEST,
        sender_id="test",
        recipient_id=agent.agent_id,
        content={"task_type": "echo", "text": "Hello Agent"},
    )
    
    response = await agent.process_message(msg)
    
    assert response.parent_message_id == msg.message_id
    assert "echoed" in response.content
    assert agent.state == AgentState.COMPLETED


@pytest.mark.asyncio
async def test_calculator_agent():
    """Test calculator agent."""
    agent = CalculatorAgent()
    
    msg = Message(
        message_type=MessageType.TASK_REQUEST,
        sender_id="test",
        recipient_id=agent.agent_id,
        content={"expression": "10 + 5"},
    )
    
    response = await agent.process_message(msg)
    
    assert response.content.get("result") == 15


@pytest.mark.asyncio
async def test_agent_state_transitions():
    """Test agent state machine."""
    agent = EchoAgent()
    
    assert agent.state == AgentState.IDLE
    
    msg = Message(
        message_type=MessageType.TASK_REQUEST,
        sender_id="test",
        recipient_id=agent.agent_id,
        content={"task_type": "echo", "text": "test"},
    )
    
    response = await agent.process_message(msg)
    
    assert agent.state == AgentState.COMPLETED


# ═══════════════════════════════════════════════════════════════
# Approval Gate Tests
# ═══════════════════════════════════════════════════════════════

def test_approval_gate_creation():
    """Test approval gate creation."""
    gate = ApprovalGate(
        gate_type="content_review",
        action_description="Review campaign content",
        required_approvers={"manager", "compliance"},
    )
    
    assert gate.status == GateStatus.PENDING
    assert len(gate.required_approvers) == 2


def test_approval_gate_decision():
    """Test recording approval decisions."""
    gate = ApprovalGate(
        gate_type="budget",
        action_description="Approve budget",
        required_approvers={"manager"},
        require_unanimous=True,
    )
    
    assert gate.status == GateStatus.PENDING
    
    gate.add_decision("manager", ApprovalDecision.APPROVED)
    
    assert gate.status == GateStatus.APPROVED


def test_approval_gate_rejection():
    """Test rejection overrides approval."""
    gate = ApprovalGate(
        gate_type="content",
        action_description="Content approval",
        required_approvers={"manager", "compliance"},
        require_unanimous=True,
    )
    
    gate.add_decision("manager", ApprovalDecision.APPROVED)
    gate.add_decision("compliance", ApprovalDecision.REJECTED, comment="Contains PII")
    
    assert gate.status == GateStatus.REJECTED


def test_approval_manager():
    """Test approval manager."""
    manager = ApprovalManager()
    
    gate = manager.create_gate(
        gate_type="budget",
        action_description="Budget change",
        required_approvers={"manager"},
    )
    
    assert gate.gate_id in manager.gates
    assert len(manager.get_pending_gates()) == 1
    
    manager.record_decision(gate.gate_id, "manager", ApprovalDecision.APPROVED)
    
    assert len(manager.get_pending_gates()) == 0


# ═══════════════════════════════════════════════════════════════
# Run tests
# ═══════════════════════════════════════════════════════════════

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
