# Agent Orchestration Architecture - Mizan

## 📋 نظرة عامة

هذا النظام يوفر **orchestrated multi-agent workflow** لتحسين وتحليل الـ campaigns بطريقة احترافية.

## 🏗️ المعمارية

```
┌─────────────────────────────────────────────────────────────┐
│                    Orchestrated Workflow                     │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│              SerialAgentOrchestrator                         │
│   (Controls agent execution flow & context sharing)          │
└─────────────────────────────────────────────────────────────┘
                              │
        ┌─────────────────────┼─────────────────────┐
        ▼                     ▼                     ▼
┌──────────────┐      ┌──────────────┐      ┌──────────────┐
│AnalysisAgent │──► │OptimizationA. │──► │ValidatorAgent │
│              │      │              │      │              │
│ • Analyzes   │      │ • Generates  │      │ • Validates  │
│   data       │      │   plan       │      │   rules      │
│ • Extracts   │      │ • Priority   │      │ • Checks     │
│   insights   │      │   actions    │      │   errors     │
└──────────────┘      └──────────────┘      └──────────────┘
                                                   │
                                                   ▼
                                            ┌──────────────┐
                                            │ExecutorAgent │
                                            │              │
                                            │ • Executes   │
                                            │   actions    │
                                            │ • Returns    │
                                            │   results    │
                                            └──────────────┘

┌─────────────────────────────────────────────────────────────┐
│                    AgentContext                              │
│   (Shared state, messages, communication between agents)     │
└─────────────────────────────────────────────────────────────┘
```

## 🔑 المكونات الرئيسية

### 1. **AgentResult** (`agent_result.py`)
نموذج موحد لـ response من كل agent:
```python
- agent_name: اسم الـ agent
- status: SUCCESS/FAILURE/PARTIAL
- data: النتائج الرئيسية
- metadata: بيانات إضافية
- execution_time_ms: وقت التنفيذ
- next_agent: الـ agent التالي في الـ pipeline
```

**Builder Pattern** للإنشاء السهل:
```python
result = AgentResultBuilder("MyAgent", "task_1") \
    .success(data) \
    .with_execution_time(100) \
    .next_step("NextAgent") \
    .build()
```

### 2. **AgentContext** (`agent_context.py`)
إدارة الـ state المشترك بين الـ agents:
```python
- shared_data: بيانات مشتركة
- messages: تاريخ التواصل
- campaign_id, market: سياق النطاق
- execution_stopped: التحكم بـ execution
- error_count: عد الأخطاء
```

**API Methods:**
```python
context.set_data("key", value)           # تخزين البيانات
context.get_data("key")                  # استرجاع البيانات
context.add_message(agent, type, data)   # إضافة رسالة
context.increment_errors()               # عد الأخطاء
context.should_stop()                    # هل نتوقف؟
```

### 3. **SerialAgentOrchestrator** (`orchestrator.py`)
المتحكم الرئيسي بـ execution:

**Features:**
- ✅ تنفيذ Sequential (agents تنفذ واحد تلو الآخر)
- ✅ تنفيذ Parallel (agents تنفذ في نفس الوقت)
- ✅ Retry logic مع exponential backoff
- ✅ State management بين agents
- ✅ Error handling متقدم
- ✅ Execution logging و debugging

**Usage:**
```python
orchestrator = SerialAgentOrchestrator(max_retries=2, debug=True)

# Serial execution
result = await orchestrator.orchestrate(
    agents=[agent1, agent2, agent3],
    task=task,
    context=context
)

# Parallel execution
results = await orchestrator.orchestrate_parallel(
    agents=[agent1, agent2, agent3],
    task=task,
    context=context
)
```

### 4. **Specialized Agents** (`specialized_agents.py`)

#### 🔍 **AnalysisAgent**
يحلل البيانات واستخراج insights:
```python
- يستقبل Task من orchestrator
- يبني prompt للـ LLM
- يحصل على تحليل من LLM
- يخزن النتائج في AgentContext
- يمرر النتائج للـ agent التالي
```

#### 🎯 **OptimizationAgent**
يولد خطة تحسين بناءً على التحليل:
```python
- يقرأ نتائج Analysis من Context
- يبني prompt بتوصيات التحسين
- يحصل على plan من LLM
- يخزن الـ plan في Context
```

#### ✅ **ValidatorAgent**
يتحقق من القواعد والـ constraints:
```python
- يقرأ optimization plan من Context
- يشغل validation rules
- يتحقق من القيود (budget, channels, etc.)
- يوقف execution إذا فشلت validation
```

#### ⚙️ **ExecutorAgent**
ينفذ الـ actions المعتمدة:
```python
- يقرأ validated plan من Context
- ينفذ الـ actions واحدة واحدة
- يتعامل مع الأخطاء
- يخزن النتائج في Context
```

### 5. **Use Case** (`optimize_campaign_with_agents.py`)

#### OptimizeCampaignWithAgentsUseCase
الـ use case الرئيسية:
```python
1. تجلب الـ campaign من database
2. تنشئ Task و AgentContext
3. تبني pipeline الـ agents
4. تشغل الـ orchestrator
5. تخزن النتائج
```

#### CampaignOptimizationPipeline
API عالي المستوى:
```python
# تحسين campaign واحد
await pipeline.optimize_single_campaign("campaign_123")

# تحليل عدة campaigns بـ parallel
await pipeline.optimize_campaigns_in_parallel(campaigns)

# تحسين batch من campaigns
await pipeline.optimize_batch(campaign_ids)
```

## 🔄 Data Flow

```
Campaign Input
     │
     ▼
┌─────────────────────┐
│ AnalysisAgent       │  ┌─────────────────────────────┐
│ - Analyze data      │──▶ AgentContext updated with   │
│ - Extract insights  │  │ "analysis_results"         │
└─────────────────────┘  └─────────────────────────────┘
     │
     ▼
┌─────────────────────┐
│ OptimizationAgent   │  ┌─────────────────────────────┐
│ - Read analysis     │──▶ AgentContext updated with   │
│ - Generate plan     │  │ "optimization_plan"        │
└─────────────────────┘  └─────────────────────────────┘
     │
     ▼
┌─────────────────────┐
│ ValidatorAgent      │  ┌─────────────────────────────┐
│ - Validate plan     │──▶ AgentContext updated with   │
│ - Check rules       │  │ "validation_results"       │
└─────────────────────┘  └─────────────────────────────┘
     │
     ▼
┌─────────────────────┐
│ ExecutorAgent       │  ┌─────────────────────────────┐
│ - Execute actions   │──▶ AgentContext updated with   │
│ - Return results    │  │ "execution_results"        │
└─────────────────────┘  └─────────────────────────────┘
     │
     ▼
Final AgentResult + Updated Campaign
```

## 💡 مثال الاستخدام الكامل

```python
from core.use_cases.optimize_campaign_with_agents import (
    OptimizeCampaignWithAgentsUseCase,
    CampaignOptimizationPipeline
)

# تهيئة المكونات
campaign_repo = CampaignRepository()
llm_port = OpenAILLMAdapter()
executor_port = CampaignExecutor()

# إنشاء use case
use_case = OptimizeCampaignWithAgentsUseCase(
    campaign_repo=campaign_repo,
    llm_port=llm_port,
    executor_port=executor_port
)

# إنشاء pipeline
pipeline = CampaignOptimizationPipeline(use_case)

# تشغيل التحسين
result = await pipeline.optimize_single_campaign("campaign_123")

# قراءة النتائج
print(f"Status: {result.status}")
print(f\"Execution Time: {result.execution_time_ms}ms\")
print(f\"Data: {result.data}\")
print(f\"Next Agent: {result.next_agent}\")
```

## 🎯 Key Design Patterns

### 1. **Hexagonal Architecture**
- Agents هي domain logic
- Ports توصل مع external services (LLM, DB, etc.)
- Adapters implement الـ ports

### 2. **Builder Pattern**
```python
# AgentResult builder
AgentResultBuilder("Agent", "task_1")
    .success(data)
    .with_execution_time(100)
    .with_metadata("key", "value")
    .build()
```

### 3. **Context Pattern**
- AgentContext يمرر الـ state بين الـ agents
- كل agent يقرأ من context ويكتب فيه
- State بقى منظم وسهل المتابعة

### 4. **Chain of Responsibility**
- كل agent مسؤول عن جزء من الـ workflow
- agent يقرر إذا يمرر للـ agent التالي
- easy to add/remove agents من الـ pipeline

### 5. **Retry & Recovery**
- Exponential backoff للـ failures
- Graceful error handling
- State preservation للـ debugging

## 🧪 Testing Strategy

### Unit Tests
```python
# Test individual agents
test_analysis_agent()
test_optimization_agent()
test_validator_agent()
test_executor_agent()
```

### Integration Tests
```python
# Test orchestration with mock adapters
test_orchestrator_serial_execution()
test_orchestrator_parallel_execution()
test_context_sharing()
```

### E2E Tests
```python
# Test complete workflow
test_full_campaign_optimization()
test_error_handling_and_recovery()
```

## 📈 Performance Considerations

### Serial Execution
- ✅ **Pros:** State sharing سهل, deterministic
- ❌ **Cons:** بطء (agents تنفذ sequentially)

### Parallel Execution
- ✅ **Pros:** سريع، independent agents
- ❌ **Cons:** State sharing معقد، potential race conditions

### Optimization Tips
1. Use parallel execution للـ independent tasks
2. Cache LLM responses عشان ما تقدم requests متكررة
3. Batch operations عندما يكون ممكن
4. Monitor execution metrics للـ optimization

## 🔒 Validation & Safety

- ✅ ValidatorAgent checks business rules
- ✅ MaxErrors threshold for auto-stop
- ✅ Budget constraints enforcement
- ✅ PII/Compliance checks

## 📊 Monitoring & Logging

```python
# Get execution log
logs = orchestrator.get_execution_log()

# Monitor context state
messages = context.get_messages(agent_name="AnalysisAgent")

# Track performance
print(f"Total time: {final_result.execution_time_ms}ms")
print(f"Tokens used: {final_result.tokens_used}")
```

## 🚀 Next Steps

1. **Implement Adapters** للـ LLM providers (OpenAI, Claude, etc.)
2. **Add More Agents** متخصصة (ContentAgent, ComplianceAgent, etc.)
3. **Enhance Monitoring** (metrics, tracing, alerts)
4. **Add Caching** للـ LLM responses
5. **Implement Dashboard** لـ visualization الـ workflows
6. **Add Testing Suite** (unit, integration, e2e)

---

**Built with ❤️ using Hexagonal Architecture**
