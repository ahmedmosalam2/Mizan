# 🤖 Agent Orchestration System - Mizan

**Enterprise-grade AI Agent orchestration system for campaign optimization**

---

## 📚 الفهرس السريع

- [🎯 نظرة عامة](#-نظرة-عامة)
- [🏗️ المعمارية](#️-المعمارية)
- [📦 المكونات](#-المكونات)
- [🚀 البدء السريع](#-البدء-السريع)
- [💡 أمثلة عملية](#-أمثلة-عملية)
- [🔧 التكوين المتقدم](#-التكوين-المتقدم)
- [📊 المراقبة والتتبع](#-المراقبة-والتتبع)
- [🧪 الاختبار](#-الاختبار)
- [📝 الأفضليات](#-الأفضليات)

---

## 🎯 نظرة عامة

**Mizan Agent Orchestration** نظام متقدم يوازن ويدير عدة وكلاء AI (Agents) بطريقة منظمة:

✅ **Multi-Agent Workflow** - تشغيل عدة agents بتسلسل أو بالتوازي  
✅ **Intelligent Orchestration** - توجيه data بين الـ agents بذكاء  
✅ **State Management** - حفظ الـ context المشترك بين الـ agents  
✅ **Error Handling** - معالجة الأخطاء مع إعادة المحاولة  
✅ **Performance Monitoring** - تتبع الـ metrics والأداء  
✅ **Business Logic** - تحقق من القواعد والـ constraints  

---

## 🏗️ المعمارية

```
┌─────────────────────────────────────────────────────────────┐
│           Campaign Optimization Pipeline                    │
│  (OptimizeCampaignWithAgentsUseCase)                        │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│              SerialAgentOrchestrator                         │
│   (Controls execution flow, context sharing, monitoring)     │
└─────────────────────────────────────────────────────────────┘
                              │
        ┌─────────────────────┼─────────────────────┐
        │                     │                     │
        ▼                     ▼                     ▼
    ┌────────────┐      ┌────────────┐      ┌────────────┐
    │ Analysis   │      │Optimization│      │ Validator  │
    │   Agent    │ ──►  │   Agent    │ ──►  │   Agent    │
    └────────────┘      └────────────┘      └────────────┘
                                                   │
                                                   ▼
                                            ┌────────────┐
                                            │  Executor  │
                                            │   Agent    │
                                            └────────────┘

┌─────────────────────────────────────────────────────────────┐
│              AgentContext (Shared State)                    │
│   - Campaign data, analysis results, optimization plan      │
│   - Message history, error logs, execution metrics          │
└─────────────────────────────────────────────────────────────┘
```

### Data Flow

```
Campaign Input
     │
     ▼ (Task + Context)
[AnalysisAgent]
     │ (analysis_results → context)
     ▼ (Task + Context + Analysis)
[OptimizationAgent]
     │ (optimization_plan → context)
     ▼ (Task + Context + Plan)
[ValidatorAgent]
     │ (validation_results → context)
     ▼ (Task + Context + Validated Plan)
[ExecutorAgent]
     │
     ▼ (execution_results)
Final AgentResult + Updated Context
```

---

## 📦 المكونات

### 1️⃣ **AgentResult** - نموذج الـ Response الموحد

```python
from core.domain.agents import AgentResult, AgentResultBuilder

# باستخدام Builder Pattern
result = AgentResultBuilder("MyAgent", "task_1") \
    .success({"data": "result"}) \
    .with_execution_time(100.5) \
    .with_metadata("key", "value") \
    .with_tokens(250) \
    .next_step("NextAgent") \
    .build()

# الخصائص الرئيسية
result.agent_name          # اسم الـ agent
result.status              # SUCCESS, FAILURE, PARTIAL, PENDING
result.data                # البيانات الأساسية
result.execution_time_ms   # وقت التنفيذ بـ milliseconds
result.error               # رسالة الخطأ (إن وجدت)
result.next_agent          # الـ agent التالي
result.tokens_used         # الـ LLM tokens المستخدمة
```

### 2️⃣ **AgentContext** - إدارة الـ State المشترك

```python
from core.domain.agents import AgentContext

# الإنشاء
context = AgentContext(
    workflow_id="wf_123",
    task_id="task_1",
    campaign_id="campaign_123",
    market="KSA"
)

# تخزين البيانات المشتركة
context.set_data("analysis_results", {"insights": [...]})
context.set_data("optimization_plan", {"actions": [...]})

# استرجاع البيانات
analysis = context.get_data("analysis_results")
all_data = context.get_all_data()

# إدارة الرسائل
context.add_message("AnalysisAgent", "analysis", {"status": "done"})
messages = context.get_messages()
agent_messages = context.get_messages("AnalysisAgent")

# التحكم بـ Execution
context.increment_step()
context.increment_errors()
context.should_stop()
context.stop_execution("Reason")

# الحالة
print(context.step_count)       # عدد الخطوات المنفذة
print(context.error_count)      # عدد الأخطاء
print(context.execution_stopped) # هل توقف التنفيذ؟
```

### 3️⃣ **SerialAgentOrchestrator** - المتحكم الرئيسي

```python
from core.domain.agents import SerialAgentOrchestrator

# الإنشاء
orchestrator = SerialAgentOrchestrator(
    max_retries=2,           # عدد محاولات إعادة المحاولة
    timeout_per_agent=60,    # timeout بالثواني
    debug=True               # تفعيل debug logging
)

# التنفيذ Sequential (الواحدة تلو الأخرى)
result = await orchestrator.orchestrate(
    agents=[agent1, agent2, agent3],
    task=task,
    context=context
)

# التنفيذ Parallel (في نفس الوقت)
results = await orchestrator.orchestrate_parallel(
    agents=[agent1, agent2, agent3],
    task=task,
    context=context
)

# الحصول على سجل التنفيذ
logs = orchestrator.get_execution_log()
for log in logs:
    print(f"{log['agent']}: {log['status']} ({log['time_ms']}ms)")
```

### 4️⃣ **Specialized Agents** - الـ Agents المتخصصة

#### **AnalysisAgent** - التحليل
```python
from core.domain.agents import AnalysisAgent

agent = AnalysisAgent(llm_port)

result = await agent.execute(
    task=task,
    context=context
)
# Returns: {
#   "type": "analysis",
#   "insights": [...],
#   "data_quality_score": 85,
#   "recommendations": [...]
# }
```

#### **OptimizationAgent** - التحسين
```python
from core.domain.agents import OptimizationAgent

agent = OptimizationAgent(llm_port)

result = await agent.execute(
    task=task,
    context=context
)
# Returns: {
#   "type": "optimization",
#   "actions": [...],
#   "estimated_improvement": 35,
#   "priority": "high",
#   "implementation_steps": [...]
# }
```

#### **ValidatorAgent** - التحقق
```python
from core.domain.agents import ValidatorAgent

validation_rules = {
    "budget_constraint": lambda t, p: p.get("estimated_improvement", 0) >= 0,
    "channel_coverage": lambda t, p: len(p.get("actions", [])) > 0
}

agent = ValidatorAgent(validation_rules)

result = await agent.execute(
    task=task,
    context=context
)
# Returns: {
#   "type": "validation",
#   "is_valid": True,
#   "errors": [],
#   "warnings": [],
#   "passed_checks": [...]
# }
```

#### **ExecutorAgent** - التنفيذ
```python
from core.domain.agents import ExecutorAgent

agent = ExecutorAgent(executor_port)

result = await agent.execute(
    task=task,
    context=context
)
# Returns: {
#   "type": "execution",
#   "status": "success",
#   "executed_actions": [...],
#   "errors": []
# }
```

### 5️⃣ **Use Cases** - حالات الاستخدام

#### **OptimizeCampaignWithAgentsUseCase**
```python
from core.use_cases import OptimizeCampaignWithAgentsUseCase

use_case = OptimizeCampaignWithAgentsUseCase(
    campaign_repo=campaign_repo,
    llm_port=llm_port,
    executor_port=executor_port
)

# تحسين campaign واحد
result = await use_case.execute("campaign_123")

# تحليل عدة campaigns بالتوازي
results = await use_case.execute_parallel_analysis(campaigns)
```

#### **CampaignOptimizationPipeline**
```python
from core.use_cases import CampaignOptimizationPipeline

pipeline = CampaignOptimizationPipeline(use_case)

# تحسين واحد
result = await pipeline.optimize_single_campaign("campaign_123")

# تحليل متوازي
results = await pipeline.optimize_campaigns_in_parallel(campaigns)

# batch متسلسل
results = await pipeline.optimize_batch(campaign_ids)
```

---

## 🚀 البدء السريع

### 1️⃣ التثبيت

```bash
# استنساخ المستودع
git clone <repo>
cd Mizan

# تثبيت المتطلبات
pip install -r requirements.txt

# التثبيت في وضع Development
pip install -e .
```

### 2️⃣ إعداد البيئة

```bash
# نسخ ملف الإعدادات
cp .env.example .env

# تعديل البيانات
# - أضف API keys للـ LLM services
# - أضف database connection strings
# - أضف configuration أخرى
```

### 3️⃣ مثال بسيط

```python
import asyncio
from core.domain.agents import (
    SerialAgentOrchestrator,
    AnalysisAgent,
    OptimizationAgent,
    ValidatorAgent,
    ExecutorAgent
)
from core.domain.agents import AgentContext
from core.domain.entities.agent_helper import Task

async def main():
    # 1. إنشاء الـ agents
    llm = MyLLMAdapter()
    executor = MyExecutor()
    
    agents = [
        AnalysisAgent(llm),
        OptimizationAgent(llm),
        ValidatorAgent(),
        ExecutorAgent(executor)
    ]
    
    # 2. إنشاء Task
    task = Task(
        goal="Optimize campaign",
        context={"campaign_id": "123"},
        constraints=["budget: 100000"],
        expected_output="Optimization plan"
    )
    
    # 3. إنشاء Orchestrator
    orchestrator = SerialAgentOrchestrator(debug=True)
    
    # 4. تشغيل
    result = await orchestrator.orchestrate(
        agents=agents,
        task=task
    )
    
    print(f"Status: {result.status}")
    print(f"Data: {result.data}")
    print(f"Time: {result.execution_time_ms}ms")

if __name__ == "__main__":
    asyncio.run(main())
```

---

## 💡 أمثلة عملية

### مثال 1: تحليل وتحسين Campaign

```python
# في examples/agent_orchestration_examples.py
await example_1_basic_orchestration()
```

### مثال 2: تحليل متوازي لعدة Campaigns

```python
await example_2_parallel_analysis()
```

### مثال 3: استخدام Use Case كاملة

```python
await example_3_complete_use_case()
```

### مثال 4: معالجة الأخطاء

```python
await example_4_error_handling()
```

### مثال 5: Validation مخصصة

```python
await example_5_custom_validation()
```

---

## 🔧 التكوين المتقدم

### Custom Validation Rules

```python
def budget_rule(task, plan):
    """Validate budget."""
    return plan.get("estimated_improvement", 0) >= 20

def performance_rule(task, plan):
    """Validate performance."""
    return len(plan.get("actions", [])) > 0

rules = {
    "budget": budget_rule,
    "performance": performance_rule
}

validator = ValidatorAgent(rules)
```

### Custom Orchestrator

```python
class MyCustomOrchestrator(AgentOrchestratorPort):
    async def orchestrate(self, agents, task, context=None):
        # Implementation مخصصة
        pass

orchestrator = MyCustomOrchestrator()
```

### Error Recovery

```python
orchestrator = SerialAgentOrchestrator(
    max_retries=3,
    timeout_per_agent=30  # 30 seconds
)

# Exponential backoff يتم تطبيقه تلقائياً
```

---

## 📊 المراقبة والتتبع

### عرض السجلات

```python
# سجل التنفيذ
logs = orchestrator.get_execution_log()
for log in logs:
    print(f"Agent: {log['agent']}")
    print(f"Status: {log['status']}")
    print(f"Time: {log['time_ms']}ms")

# رسائل السياق
messages = context.get_messages()
for msg in messages:
    print(f"[{msg['agent']}] {msg['type']}: {msg['content']}")

# البيانات المشتركة
data = context.get_all_data()
```

### Metrics

```python
# وقت التنفيذ
execution_time = result.execution_time_ms

# الـ tokens المستخدمة
tokens = result.tokens_used

# عدد الخطوات
steps = context.step_count

# عدد الأخطاء
errors = context.error_count
```

---

## 🧪 الاختبار

### Unit Tests

```bash
pytest tests/unit/core/domain/agents/ -v
```

### Integration Tests

```bash
pytest tests/integration/ -v
```

### E2E Tests

```bash
pytest tests/e2e/ -v
```

### تشغيل الأمثلة

```bash
python examples/agent_orchestration_examples.py
```

---

## 📝 الأفضليات

### Best Practices

✅ **استخدم AgentContext** لمشاركة البيانات  
✅ **استخدم Builder Pattern** لإنشاء النتائج  
✅ **ضع Validation Rules واضحة** قبل Execution  
✅ **راقب الأخطاء** وأعد المحاولة بحذر  
✅ **وثق Custom Agents** بوضوح  

### Performance Tips

⚡ استخدم Parallel execution للـ independent agents  
⚡ Cache LLM responses عند الإمكان  
⚡ استخدم Timeouts للـ long-running operations  
⚡ راقب Memory usage للـ large contexts  

### Security

🔒 تحقق من الـ inputs قبل التمرير  
🔒 لا تخزن sensitive data في Context  
🔒 استخدم Rate limiting للـ LLM calls  
🔒 فعّل Authentication للـ executor operations  

---

## 📚 مراجع إضافية

- [ARCHITECTURE_DETAILS.md](./AGENT_ORCHESTRATION_ARCHITECTURE.md) - تفاصيل المعمارية
- [examples/](../examples/) - أمثلة عملية
- [tests/](../tests/) - اختبارات
- [API Reference](#) - مرجع API كامل

---

## 🤝 المساهمة

نرحب بـ contributions! يرجى:

1. Fork المستودع
2. أنشئ branch للـ feature
3. اكتب الاختبارات
4. submit Pull Request

---

## 📄 الترخيص

MIT License - انظر [LICENSE](../LICENSE)

---

## 📞 الدعم

- 📧 البريد الإلكتروني: support@mizan.ai
- 💬 Discord: [Join our community](https://discord.gg/mizan)
- 📖 الوثائق: [docs.mizan.ai](https://docs.mizan.ai)

---

**بُني بـ ❤️ باستخدام Hexagonal Architecture وأفضليات الـ Enterprise Software**
