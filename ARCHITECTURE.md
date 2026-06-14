# Multi-Agent Benchmarking Framework - Architecture

**Mission**: Build a production-grade reference architecture for multi-agent systems that is framework-agnostic, extensible, and measurable.

---

## Philosophy: Why This Architecture?

This architecture embodies three core principles:

### 1. **Framework-Agnostic Abstractions**
No framework (CrewAI, LangGraph, Agno) should ever dictate your system design. Instead:
- Define **abstract interfaces** that frameworks must implement (Agent, Tool, Orchestrator)
- Write business logic against these interfaces, not framework-specific APIs
- Swap frameworks by implementing new adapters, not rewriting code

**Payoff**: When you discover CrewAI's orchestration is too rigid for your use case, you switch to LangGraph without rebuilding your agents.

### 2. **Explicit Over Implicit**
Clear contracts make systems debuggable:
- Message types are explicit (TASK_REQUEST, TOOL_CALL, APPROVAL_REQUEST) — not implicit HTTP requests
- State transitions are explicit (IDLE → THINKING → EXECUTING → COMPLETED)
- Approval gates are first-class citizens, not hacks on top of agent logic
- Tool parameters are schema-validated before execution

**Payoff**: When a bug occurs ("why did the customer get an Egyptian-dialect message in Saudi Arabia?"), you can trace it through explicit message routing, state snapshots, and approval records.

### 3. **Observability by Design**
Every action is traced:
- Distributed tracing across agents (trace_id links all messages in a workflow)
- Token/cost tracking per LLM call (to spot runaway AI expenses)
- State versioning and replay (for debugging, replay failed workflows)
- Approval audit trail (for compliance)

**Payoff**: No guessing why the system behaved unexpectedly. Every decision and its context is logged.

---

## Architecture Layers

```
┌─────────────────────────────────────────────────────┐
│  Framework Adapters (CrewAI, LangGraph, Agno)      │
│  Implement abstract interfaces for specific FW      │
├─────────────────────────────────────────────────────┤
│  Agents (Campaign Commander, Content Architect)    │
│  Business logic that knows how to orchestrate       │
├─────────────────────────────────────────────────────┤
│  Core Abstractions (Agent, Tool, Message, State)   │
│  Framework-agnostic contracts                      │
├─────────────────────────────────────────────────────┤
│  Observability (Tracing, Logging, Metrics)         │
│  Every action is recorded                          │
├─────────────────────────────────────────────────────┤
│  Services (LLM Gateway, RAG, Compliance)           │
│  Shared utilities (caching, cost tracking)         │
└─────────────────────────────────────────────────────┘
```

---

## Core Abstractions

### `Agent` - An autonomous decision-maker

**Contract**:
```python
async def process_message(self, message: Message) -> Message
```

**Principles**:
- Pure function: same input → same output (deterministic by design)
- Single async entry point for all work
- Declares capabilities (role, tools, data access) upfront
- Maintains memory (short-term context + long-term history)

**Examples**:
- **Campaign Commander**: Orchestrator agent that decomposes Ramadan campaign tasks
- **Content Architect**: Generator agent that creates ad copy and product descriptions
- **Channel Deployer**: API agent that pushes campaigns to Meta/Google/TikTok
- **Analytics Engine**: Analyzer agent that computes ROAS and recommends budget shifts
- **Customer Engagement**: Conversational agent handling WhatsApp inquiries
- **Compliance Guardian**: Validator agent detecting PII and consent violations

### `Tool` - A capability agents can invoke

**Contract**:
```python
async def execute(self, agent_id: str, **kwargs) -> ToolExecutionResult
```

**Principles**:
- Stateless (or minimal state)
- Idempotent (safe to retry)
- Schema-validated parameters
- Observable (every invocation logged with tokens/latency/cost)

**Examples**:
- **API Tools**: Meta Ads API, Salla API, Fawry payment gateway
- **RAG Tools**: Product catalog retrieval, customer history search
- **LLM Tools**: Content generation, sentiment analysis, entity extraction
- **Code Execution**: Analytics calculations, A/B test significance testing
- **Compliance Tools**: PII detection, consent validation, audit logging

### `Message` - Inter-agent communication protocol

**Design**:
```python
Message(
    message_id = unique_uuid,        # For tracing
    trace_id = workflow_trace_id,    # Links all messages in workflow
    parent_message_id = prev_msg,    # Conversation threading
    message_type = TASK_REQUEST,     # Explicit type (vs generic JSON)
    sender_id = "agent1",
    recipient_id = "agent2",         # None = broadcast
    content = {...},                 # Payload
)
```

**Message Types**:
- `TASK_REQUEST` / `TASK_RESPONSE`: Agent-to-agent work delegation
- `TOOL_CALL` / `TOOL_RESULT`: Tool invocation and result
- `APPROVAL_REQUEST` / `APPROVAL_RESPONSE`: Human-in-the-loop gates
- `STATE_UPDATE`: Shared state synchronization
- `EVENT`: System events (e.g., KPI threshold breached)
- `ERROR`: Error propagation

### `SharedState` - Synchronized workflow state

**Design**:
- **MVCC (Multi-Version Concurrency Control)**: Multiple agents can read simultaneously while writes are atomic
- **Immutable snapshots**: Each version is immutable (for replay/debugging)
- **History tracking**: Every change logged with actor, timestamp, rationale
- **Checkpointing**: State can be saved/restored for crash recovery

**Example**:
```python
# Campaign Commander broadcasts:
state.set("saudi_meta_budget_spent", 15000, actor_id="campaign_commander")

# Analytics Engine reads:
spent = state.get("saudi_meta_budget_spent")  # Sees 15000

# If crashed and restarted:
checkpoint = state.checkpoint()  # Serialize state
# ... restore from checkpoint without re-running workflow
```

### `Orchestrator` - Workflow conductor

**Contract**:
```python
async def execute_workflow(
    self,
    workflow_type: str,
    input_context: Dict[str, Any],
) -> WorkflowExecution
```

**Responsibilities**:
- Route messages between agents
- Manage task execution (sequential, parallel, conditional)
- Create approval gates
- Maintain shared state
- Error recovery and retries
- Observability collection

**Framework adapters implement this**:
- `CrewAIOrchestrator`: Delegates to CrewAI's task execution
- `LangGraphOrchestrator`: Uses LangGraph state graph
- `AgnoOrchestrator`: Uses Agno's async/await patterns
- `SimpleOrchestrator`: Reference implementation (sequential only)

---

## Design Patterns

### 1. **Chain of Responsibility** (Approval Gates)

When Campaign Commander wants to shift 30% of budget from Snapchat to Meta:
1. Creates ApprovalGate with `required_approvers = {"marketing_manager"}`
2. Workflow pauses
3. Marketing manager reviews context and approves/rejects
4. Workflow resumes

```python
gate = orchestrator.create_approval_gate(
    gate_type="budget_reallocation",
    action_description="Shift SAR 15,000 from Snapchat to Meta",
    required_approvers={"marketing_manager"},
    context={"old_budget": {...}, "new_budget": {...}},
)

# Workflow waits...

manager.record_decision(gate.gate_id, "marketing_manager", ApprovalDecision.APPROVED)

# Workflow resumes
```

### 2. **Strategy Pattern** (Framework Selection)

Business logic is framework-agnostic:
```python
# Same campaign logic works with any orchestrator
campaign_logic = CampaignWorkflow(agents=[commander, content, deployer, analytics])

# Swap orchestrators by changing one line:
result_crewai = await CrewAIOrchestrator(...).execute_workflow(...)
result_langgraph = await LangGraphOrchestrator(...).execute_workflow(...)
result_agno = await AgnoOrchestrator(...).execute_workflow(...)

# All produce identical results (deterministic)
assert result_crewai.output == result_langgraph.output
```

### 3. **Observer Pattern** (Events)

Analytics Engine monitors KPI thresholds:
```python
# Observable event emitted when threshold breached
orchestrator.on_event("KPI_THRESHOLD_BREACHED", {
    "channel": "saudi_meta",
    "metric": "cpa",
    "current_value": 45,
    "threshold": 25,
})

# Campaign Commander listens and reacts
campaign_commander.handle_event(...)  # Might pause campaign, escalate, etc.
```

### 4. **Builder Pattern** (Workflow Construction)

```python
workflow = (
    WorkflowBuilder()
    .add_agent(campaign_commander)
    .add_agent(content_architect)
    .add_approval_gate("content_review", required_approvers={"compliance"})
    .add_parallel_tasks([
        ("saudi_campaign", channel_deployer),
        ("egypt_campaign", channel_deployer),
    ])
    .add_approval_gate("launch_approval", required_approvers={"manager"})
    .build()
)

result = await orchestrator.execute(workflow)
```

---

## Implementation Path (Phase 1 → Phase 3)

### **Phase 1: Core Architecture (NOW)**
✅ Define abstract interfaces (Agent, Tool, Message, State, Orchestrator)
✅ Simple reference implementations (EchoAgent, CalculatorAgent, SimpleOrchestrator)
✅ Unit tests validating the contracts
✅ Documentation

**Artifacts**:
- `src/core/abstractions/*.py` - Interface definitions
- `src/examples/agents.py` - Reference agent implementations
- `src/examples/workflows.py` - Example workflows
- `src/tests/test_core.py` - Unit tests

**Validation**: All tests pass, architecture is proven to work.

### **Phase 2: 6 Specialized Agents (NEXT)**
Implement the 6 Ramadan campaign agents:
1. **Campaign Commander** (Orchestrator) - Decomposes campaign tasks
2. **Content Architect** (Generator) - Creates bilingual content
3. **Channel Deployer** (API Agent) - Pushes to Meta/Google/Snapchat/TikTok/WhatsApp
4. **Analytics & Optimization** (Analyzer) - Computes ROAS, recommends budget shifts
5. **Customer Engagement** (Conversational) - Handles WhatsApp inquiries
6. **Compliance Guardian** (Validator) - Detects PII, validates consent, audit logging

**Artifacts**:
- `src/agents/` - Agent implementations
- `src/workflows/campaign_workflow.py` - Ramadan campaign orchestration

### **Phase 3: Framework Adapters (THEN)**
Implement orchestrators for each framework:
1. **CrewAI Adapter** - Crewtasks mapped to our Task abstraction
2. **LangGraph Adapter** - State graph nodes mapped to agents
3. **Agno Adapter** - Agent classes directly
4. Plus others (AutoGen, n8n, Dify, etc.)

**Artifacts**:
- `src/frameworks/crewai_adapter.py`
- `src/frameworks/langgraph_adapter.py`
- `src/frameworks/agno_adapter.py`

**Benchmark**: Same campaign logic, different frameworks, measure performance/cost/correctness.

---

## Key Design Decisions & Rationale

### Decision 1: Explicit Message Types (not generic JSON)
**Why**: Prevents misunderstandings. `MESSAGE_TYPE.APPROVAL_REQUEST` is unambiguous; `{"type": "approval"}` is not.

### Decision 2: SharedState is Thread-Safe but Not Distributed
**Why**: For multi-agent local coordination. If scaling to distributed agents, implement MCP or gRPC on top.

### Decision 3: Tool Execution is Logged & Observable
**Why**: Token costs are real (GPT-4 costs $15-60 per 1M tokens). Without visibility, costs explode during Ramadan campaign with 1000s of LLM calls.

### Decision 4: Approval Gates are First-Class, Not Ad-Hoc
**Why**: Compliance (Saudi PDPL, Egypt PDPL) require audit trails of every approval. Building this into the architecture from the start prevents security retrofits later.

### Decision 5: Agents are Purely Async
**Why**: Orchestration naturally involves waiting (for approvals, for API responses, for async tool results). Async/await models this directly vs callbacks/futures.

---

## Running the Examples

```bash
# Setup
cd d:\Mizan
python -m pytest src/tests/test_core.py -v

# Run simple echo workflow
python -c "
import asyncio
from src.examples.workflows import run_echo_workflow
result = asyncio.run(run_echo_workflow())
print(result)
"

# Run calculation workflow
python -c "
import asyncio
from src.examples.workflows import run_calculation_workflow
result = asyncio.run(run_calculation_workflow('10 + 5 * 2'))
print(result)
"

# Run sequential workflow (echo + calculation)
python -c "
import asyncio
from src.examples.workflows import run_sequential_workflow
result = asyncio.run(run_sequential_workflow())
print(result)
"
```

---

## Next Steps

1. **Validate Phase 1** → Run all tests, ensure architecture holds
2. **Begin Phase 2** → Implement Campaign Commander orchestrating Content Architect
3. **Add compliance** → Implement Compliance Guardian detecting PII
4. **Benchmark prep** → Set up metrics collection (tokens, costs, latencies)
5. **Framework adapters** → Start CrewAI adapter, then LangGraph, then Agno

---

## Clean Code Principles Applied

✅ **SOLID**:
- **S**: Each class has one responsibility (Agent ≠ Tool, Tool ≠ Message)
- **O**: Open for extension (new agent types inherit from Agent), closed for modification
- **L**: Substitutability (any Agent implementation works with SimpleOrchestrator)
- **I**: Interface segregation (ConversationalAgent only has methods it needs)
- **D**: Dependency injection (tools passed to Agent constructor, not hard-coded)

✅ **DRY**: Shared behavior in base classes, specific behavior in subclasses

✅ **Explicit > Implicit**: Message types, state operations, approval gates all explicit

✅ **Testable**: Pure functions, no global state (except singletons for DI), easy to mock

---

## References

- [Chain of Responsibility](https://refactoring.guru/design-patterns/chain-of-responsibility) - Approval gates
- [Strategy Pattern](https://refactoring.guru/design-patterns/strategy) - Framework swapping
- [Observer Pattern](https://refactoring.guru/design-patterns/observer) - Event handling
- [MVCC](https://en.wikipedia.org/wiki/Multiversion_concurrency_control) - State versioning
