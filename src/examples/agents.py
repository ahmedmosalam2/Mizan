"""
Simple example implementations to demonstrate the core abstractions.

These serve as:
1. Reference implementation for framework adapters
2. Unit test fixtures
3. Documentation of how to implement the abstractions

The "Echo" agent is the simplest possible agent that validates the architecture.
"""

from typing import Dict, Any, Optional
from datetime import datetime

from ..core.base import (
    Agent, AgentCapabilities, AgentRole, AgentState,
    Tool, ToolExecutionResult, ToolParameter, ToolCategory,
    Message, MessageType,
)


# ═══════════════════════════════════════════════════════════════
# Simple Example Tools
# ═══════════════════════════════════════════════════════════════

class EchoTool(Tool):
    """Simplest possible tool: echoes input back."""
    
    def __init__(self):
        super().__init__(
            name="echo",
            description="Echo the input back (for testing)",
            category=ToolCategory.API_CALL,
            parameters=[
                ToolParameter(
                    name="message",
                    type="string",
                    description="Message to echo",
                    required=True,
                )
            ],
        )
    
    async def _execute_impl(self, **kwargs) -> ToolExecutionResult:
        """Implementation of echo tool."""
        message = kwargs.get("message", "")
        return ToolExecutionResult(
            success=True,
            data={"echoed": message},
            metadata={"execution_time_ms": 1},
        )


class CalculatorTool(Tool):
    """Simple calculator tool."""
    
    def __init__(self):
        super().__init__(
            name="calculator",
            description="Perform basic arithmetic",
            category=ToolCategory.CODE_EXECUTION,
            parameters=[
                ToolParameter(
                    name="expression",
                    type="string",
                    description="Math expression (e.g., '2+2')",
                    required=True,
                )
            ],
        )
    
    async def _execute_impl(self, **kwargs) -> ToolExecutionResult:
        """Implementation of calculator."""
        try:
            expression = kwargs.get("expression", "")
            result = eval(expression)  # TODO: Use safer math parser
            return ToolExecutionResult(
                success=True,
                data={"result": result},
            )
        except Exception as e:
            return ToolExecutionResult(
                success=False,
                error=str(e),
            )


# ═══════════════════════════════════════════════════════════════
# Simple Example Agents
# ═══════════════════════════════════════════════════════════════

class EchoAgent(Agent):
    """
    Simplest possible agent: receives a message, echoes it back.
    
    This demonstrates:
    - How to implement the Agent interface
    - Basic message handling
    - Tool invocation
    - State management
    """
    
    def __init__(self, agent_id: str = "echo_agent"):
        capabilities = AgentCapabilities(
            name="Echo Agent",
            description="Echoes messages back (for testing)",
            role=AgentRole.ORCHESTRATOR,
            tools={"echo", "calculator"},
        )
        
        tools = {
            "echo": EchoTool(),
            "calculator": CalculatorTool(),
        }
        
        super().__init__(
            agent_id=agent_id,
            capabilities=capabilities,
            allowed_tools=tools,
        )
        
        self._memory: Dict[str, Any] = {}
    
    async def process_message(self, message: Message) -> Message:
        """Process incoming message."""
        self._set_state(AgentState.THINKING)
        
        try:
            # Extract the task from the message
            content = message.content
            task_type = content.get("task_type", "echo")
            
            if task_type == "echo":
                # Echo the message back
                echoed_text = f"Echo from {self.agent_id}: {content.get('text', '')}"
                response_content = {"echoed": echoed_text}
            
            elif task_type == "calculate":
                # Call calculator tool
                result = await self.execute_tool(
                    "calculator",
                    expression=content.get("expression", "2+2"),
                )
                response_content = result.data if result.success else {"error": result.error}
            
            else:
                response_content = {"error": f"Unknown task type: {task_type}"}
            
            # Create response message
            response = message.create_response(
                response_type=MessageType.TASK_RESPONSE,
                sender_id=self.agent_id,
                content=response_content,
            )
            
            self._set_state(AgentState.COMPLETED)
            return response
            
        except Exception as e:
            self._set_state(AgentState.ERROR)
            return message.create_response(
                response_type=MessageType.ERROR,
                sender_id=self.agent_id,
                content={"error": str(e)},
            )
    
    async def execute_tool(self, tool_name: str, **kwargs) -> ToolExecutionResult:
        """Execute a tool."""
        self._set_state(AgentState.EXECUTING)
        
        if tool_name not in self.allowed_tools:
            return ToolExecutionResult(
                success=False,
                error=f"Tool {tool_name} not available",
            )
        
        tool = self.allowed_tools[tool_name]
        return await tool.execute(agent_id=self.agent_id, **kwargs)
    
    def get_memory_context(self, context_type: str = "short_term") -> Dict[str, Any]:
        """Get agent memory."""
        return self._memory.copy()
    
    def update_memory(self, key: str, value: Any, context_type: str = "short_term") -> None:
        """Update agent memory."""
        self._memory[key] = value


class CalculatorAgent(Agent):
    """Agent specialized in calculations."""
    
    def __init__(self, agent_id: str = "calc_agent"):
        capabilities = AgentCapabilities(
            name="Calculator Agent",
            description="Performs calculations",
            role=AgentRole.ANALYTICS,
            tools={"calculator"},
            max_iterations=5,
        )
        
        tools = {"calculator": CalculatorTool()}
        
        super().__init__(
            agent_id=agent_id,
            capabilities=capabilities,
            allowed_tools=tools,
        )
    
    async def process_message(self, message: Message) -> Message:
        """Process calculation requests."""
        self._set_state(AgentState.THINKING)
        
        try:
            expression = message.content.get("expression", "")
            
            result = await self.execute_tool(
                "calculator",
                expression=expression,
            )
            
            response = message.create_response(
                response_type=MessageType.TASK_RESPONSE,
                sender_id=self.agent_id,
                content=result.data if result.success else {"error": result.error},
            )
            
            self._set_state(AgentState.COMPLETED)
            return response
            
        except Exception as e:
            self._set_state(AgentState.ERROR)
            return message.create_response(
                response_type=MessageType.ERROR,
                sender_id=self.agent_id,
                content={"error": str(e)},
            )
    
    async def execute_tool(self, tool_name: str, **kwargs) -> ToolExecutionResult:
        """Execute tool."""
        self._set_state(AgentState.EXECUTING)
        
        if tool_name not in self.allowed_tools:
            return ToolExecutionResult(
                success=False,
                error=f"Tool {tool_name} not found",
            )
        
        tool = self.allowed_tools[tool_name]
        return await tool.execute(agent_id=self.agent_id, **kwargs)
    
    def get_memory_context(self, context_type: str = "short_term") -> Dict[str, Any]:
        """Get memory."""
        return {}
    
    def update_memory(self, key: str, value: Any, context_type: str = "short_term") -> None:
        """Update memory."""
        pass
