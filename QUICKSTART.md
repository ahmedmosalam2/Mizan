# Quick Start Guide - Multi-Agent Framework

Get up and running in 5 minutes.

## 1. Install Dependencies

```bash
cd d:\Mizan

# Create virtual environment
python -m venv venv
.\venv\Scripts\activate

# Install dev dependencies
pip install -r requirements.txt
pip install pytest pytest-asyncio
```

## 2. Run Example Tests

```bash
# Run all core tests
pytest src/tests/test_core.py -v

# Run specific test
pytest src/tests/test_core.py::test_message_creation -v

# Run with output
pytest src/tests/test_core.py -v -s
```

## 3. Run Example Workflows

```bash
# Simple echo workflow
python -c "
import asyncio
from src.examples.workflows import run_echo_workflow
result = asyncio.run(run_echo_workflow())
import json
print(json.dumps(result, indent=2, default=str))
"

# Calculation workflow
python -c "
import asyncio
from src.examples.workflows import run_calculation_workflow
result = asyncio.run(run_calculation_workflow('100 + 50'))
import json
print(json.dumps(result, indent=2, default=str))
"

# Sequential workflow (echo → calculator)
python -c "
import asyncio
from src.examples.workflows import run_sequential_workflow
result = asyncio.run(run_sequential_workflow())
import json
print(json.dumps(result, indent=2, default=str))
"

# Parallel workflow (two calculations in parallel)
python -c "
import asyncio
from src.examples.workflows import run_parallel_workflow
result = asyncio.run(run_parallel_workflow())
import json
print(json.dumps(result, indent=2, default=str))
"

# Error handling
python -c "
import asyncio
from src.examples.workflows import run_error_handling_workflow
result = asyncio.run(run_error_handling_workflow())
import json
print(json.dumps(result, indent=2, default=str))
"
```

## 4. Understand the Core Abstractions

Read these files in order:

1. **`ARCHITECTURE.md`** - High-level philosophy and design
2. **`src/core/abstractions/message.py`** - How agents communicate
3. **`src/core/abstractions/agent.py`** - How agents think
4. **`src/core/abstractions/tool.py`** - What agents can do
5. **`src/core/abstractions/state.py`** - How state is shared
6. **`src/examples/agents.py`** - Concrete agent implementations
7. **`src/examples/workflows.py`** - How to orchestrate agents

## 5. Create Your First Agent

Create `src/agents/my_first_agent.py`:

```python
from src.core.abstractions import Agent, AgentCapabilities, AgentRole, Message
from src.core.abstractions import Tool, ToolExecutionResult, ToolParameter, ToolCategory

class MyTool(Tool):
    def __init__(self):
        super().__init__(
            name="my_tool",
            description="Does something useful",
            category=ToolCategory.API_CALL,
            parameters=[
                ToolParameter(
                    name="input",
                    type="string",
                    description="Input to process",
                    required=True,
                )
            ]
        )
    
    async def _execute_impl(self, **kwargs) -> ToolExecutionResult:
        input_val = kwargs.get("input", "")
        result = f"Processed: {input_val}"
        return ToolExecutionResult(
            success=True,
            data={"output": result}
        )


class MyAgent(Agent):
    def __init__(self):
        capabilities = AgentCapabilities(
            name="My Agent",
            description="My custom agent",
            role=AgentRole.ORCHESTRATOR,
            tools={"my_tool"}
        )
        
        super().__init__(
            agent_id="my_agent_1",
            capabilities=capabilities,
            allowed_tools={"my_tool": MyTool()}
        )
    
    async def process_message(self, message: Message) -> Message:
        # Process the message
        response_content = {"result": "success"}
        
        # Return response
        return message.create_response(
            response_type=MessageType.TASK_RESPONSE,
            sender_id=self.agent_id,
            content=response_content
        )
    
    async def execute_tool(self, tool_name: str, **kwargs) -> ToolExecutionResult:
        if tool_name not in self.allowed_tools:
            return ToolExecutionResult(
                success=False,
                error=f"Tool {tool_name} not found"
            )
        
        tool = self.allowed_tools[tool_name]
        return await tool.execute(agent_id=self.agent_id, **kwargs)
    
    def get_memory_context(self, context_type: str = "short_term"):
        return {}
    
    def update_memory(self, key: str, value, context_type: str = "short_term"):
        pass
```

Then use it:
```python
import asyncio
from src.core.abstractions import Message, MessageType
from my_agents import MyAgent

async def main():
    agent = MyAgent()
    
    msg = Message(
        message_type=MessageType.TASK_REQUEST,
        sender_id="test",
        recipient_id=agent.agent_id,
        content={"task": "process", "input": "hello"}
    )
    
    response = await agent.process_message(msg)
    print(response.to_dict())

asyncio.run(main())
```

## 6. Next: Implement Campaign Agents

Once you're comfortable with the basics, implement the Ramadan campaign agents:

- **Campaign Commander** - `src/agents/campaign_commander.py`
- **Content Architect** - `src/agents/content_architect.py`
- **Channel Deployer** - `src/agents/channel_deployer.py`
- **Analytics Engine** - `src/agents/analytics_engine.py`
- **Customer Engagement** - `src/agents/customer_engagement.py`
- **Compliance Guardian** - `src/agents/compliance_guardian.py`

See `ARCHITECTURE.md` for design details on each.

## 7. Framework Adapters

After all agents are implemented, create framework adapters:

```
src/frameworks/
├── crewai_adapter.py     # CrewAI implementation
├── langgraph_adapter.py  # LangGraph implementation
└── agno_adapter.py       # Agno implementation
```

Each adapter implements the `Orchestrator` interface and delegates to the framework's API.

## 8. Run Benchmarks

```bash
# Run benchmark against all frameworks
python src/benchmarks/runner.py \
    --scenario campaign_launch \
    --frameworks crewai langgraph agno \
    --output benchmark_results.json
```

## Troubleshooting

### "ModuleNotFoundError: No module named 'src'"

Make sure you're running from the project root (`d:\Mizan`):
```bash
cd d:\Mizan
python -m pytest src/tests/test_core.py
```

NOT from inside `src/` directory.

### Tests fail with "RuntimeError: no running event loop"

Tests must use `@pytest.mark.asyncio` decorator:
```python
@pytest.mark.asyncio
async def test_my_async_function():
    ...
```

### "Tool execution failed after 3 retries"

Check:
1. Tool parameters are correct
2. Required parameters are provided
3. No syntax errors in tool implementation

## Key Commands Cheatsheet

```bash
# Tests
pytest src/tests/test_core.py -v           # Run all tests
pytest -k "message" -v                     # Run tests matching "message"
pytest --collect-only                      # List all tests

# Linting
black src/                                 # Format code
pylint src/                                # Check code style
mypy src/                                  # Type checking

# Documentation
# (Generate from ARCHITECTURE.md and docstrings)
```

## Architecture at a Glance

```
Message → Agent → Tool → Result → Message (cycle repeats)
   ↓
trace_id (all messages linked)
   ↓
SharedState (all agents read/write same state)
   ↓
Orchestrator (coordinates agents)
   ↓
ApprovalGate (pauses for human decision)
   ↓
Observability (logs everything for debugging)
```

## Files to Know

| File | Purpose |
|------|---------|
| `ARCHITECTURE.md` | Philosophy and design patterns |
| `src/core/abstractions/*.py` | Core interfaces |
| `src/core/config.py` | Configuration |
| `src/core/observability.py` | Tracing and logging |
| `src/examples/agents.py` | Reference agent implementations |
| `src/examples/workflows.py` | Example workflows |
| `src/tests/test_core.py` | Unit tests |
| `src/agents/*.py` | Your custom agents (to be created) |
| `src/frameworks/*adapter.py` | Framework integrations (to be created) |

---

**Next**: Pick an agent (Content Architect is simpler to start) and begin implementation!
