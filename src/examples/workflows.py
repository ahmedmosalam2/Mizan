from typing import Dict, Any, Optional
from datetime import datetime

from ..core.abstractions import (
    Message, MessageType,
    Orchestrator,
    WorkflowExecution, WorkflowStatus,
)
from .agents import EchoAgent, CalculatorAgent


async def run_echo_workflow() -> Dict[str, Any]:
    """
    Simplest workflow: send a message to an agent, get response back.
    
    This tests:
    - Message creation
    - Agent message processing
    - Response handling
    
    Returns:
        Results dict
    """
    # Create agent
    agent = EchoAgent(agent_id="test_echo_agent")
    
    # Create input message
    message = Message(
        message_type=MessageType.TASK_REQUEST,
        sender_id="test_runner",
        recipient_id=agent.agent_id,
        content={
            "task_type": "echo",
            "text": "Hello, Echo Agent!",
        },
    )
    
    # Process message
    response = await agent.process_message(message)
    
    # Return results
    return {
        "request": message.to_dict(),
        "response": response.to_dict(),
        "agent_state": agent.state.value,
    }


async def run_calculation_workflow(expression: str) -> Dict[str, Any]:
    """
    Simple calculation workflow.
    
    This tests:
    - Tool execution
    - Error handling
    
    Args:
        expression: Math expression to evaluate
    
    Returns:
        Results dict
    """
    agent = CalculatorAgent(agent_id="test_calc_agent")
    
    message = Message(
        message_type=MessageType.TASK_REQUEST,
        sender_id="test_runner",
        recipient_id=agent.agent_id,
        content={"expression": expression},
    )
    
    response = await agent.process_message(message)
    
    return {
        "expression": expression,
        "result": response.content.get("result"),
        "success": "error" not in response.content,
    }


async def run_sequential_workflow() -> Dict[str, Any]:
    """
    Test sequential execution of multiple agents.
    
    Agent1 (Echo) -> produces output -> Agent2 (Calculator) -> processes result
    
    This tests:
    - Inter-agent communication
    - Message chaining
    - State passing
    
    Returns:
        Results dict
    """
    echo_agent = EchoAgent(agent_id="echo_1")
    calc_agent = CalculatorAgent(agent_id="calc_1")
    
    # Step 1: Echo agent echoes a calculation
    msg1 = Message(
        message_type=MessageType.TASK_REQUEST,
        sender_id="workflow",
        recipient_id=echo_agent.agent_id,
        content={"task_type": "echo", "text": "10 + 5"},
        trace_id="seq_workflow_1",
    )
    
    response1 = await echo_agent.process_message(msg1)
    
    # Step 2: Extract echoed text and send to calculator
    echoed_text = response1.content.get("echoed", "")
    # Extract just the expression part
    expression = echoed_text.split(": ")[-1] if ": " in echoed_text else echoed_text
    
    msg2 = Message(
        message_type=MessageType.TASK_REQUEST,
        sender_id="workflow",
        recipient_id=calc_agent.agent_id,
        content={"expression": expression},
        trace_id="seq_workflow_1",
        parent_message_id=response1.message_id,
    )
    
    response2 = await calc_agent.process_message(msg2)
    
    return {
        "step1_echo": response1.content,
        "step2_calculation": response2.content,
        "trace_id": msg2.trace_id,
    }


async def run_parallel_workflow() -> Dict[str, Any]:
    """
    Test parallel execution of multiple agents.
    
    Agent1 calculates: 10 + 5
    Agent2 calculates: 20 * 3
    (Both run in parallel)
    
    This tests:
    - Concurrent agent execution
    - Shared state (if applicable)
    
    Returns:
        Results dict
    """
    import asyncio
    
    agent1 = CalculatorAgent(agent_id="calc_parallel_1")
    agent2 = CalculatorAgent(agent_id="calc_parallel_2")
    
    msg1 = Message(
        message_type=MessageType.TASK_REQUEST,
        sender_id="workflow",
        recipient_id=agent1.agent_id,
        content={"expression": "10 + 5"},
        trace_id="parallel_workflow",
    )
    
    msg2 = Message(
        message_type=MessageType.TASK_REQUEST,
        sender_id="workflow",
        recipient_id=agent2.agent_id,
        content={"expression": "20 * 3"},
        trace_id="parallel_workflow",
    )
    
    # Execute both in parallel
    response1, response2 = await asyncio.gather(
        agent1.process_message(msg1),
        agent2.process_message(msg2),
    )
    
    return {
        "agent1_result": response1.content,
        "agent2_result": response2.content,
        "trace_id": msg1.trace_id,
    }


async def run_error_handling_workflow() -> Dict[str, Any]:
    """
    Test error handling and resilience.
    
    This tests:
    - Invalid input handling
    - Error messages
    - Graceful failure
    
    Returns:
        Results dict
    """
    agent = CalculatorAgent(agent_id="calc_error_test")
    
    # Invalid expression
    message = Message(
        message_type=MessageType.TASK_REQUEST,
        sender_id="test_runner",
        recipient_id=agent.agent_id,
        content={"expression": "1 / 0"},  # Division by zero
    )
    
    response = await agent.process_message(message)
    
    return {
        "request": message.content,
        "response": response.content,
        "has_error": "error" in response.content,
    }
