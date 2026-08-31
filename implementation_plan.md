# Mizan — Rebuild Plan

## الهدف

بناء **benchmark يشغّل نفس الـ Ramadan campaign scenario على 20 framework** ويقارن النتائج.

المخرج النهائي:
1. **Leaderboard** — جدول 20 framework × 7 dimensions مع scores
2. **تقرير تفصيلي** — analysis مكتوب بـ evidence من التشغيل الفعلي
3. **كود قابل للتشغيل** — أي حد يقدر يشغّل `python runner/run.py --framework crewai`

---

## ليه الـ rebuild؟

الكود القديم بنى framework جوا framework:
- `shared/contracts/Agent`, `Tool`, `Orchestrator`, `Message`, `State` — abstractions ضخمة ما بيستخدمهاش حد
- `ScenarioResult` فيه boolean flags (`used_parallel: bool`) بس الـ rubrics بتتوقع أرقام
- نظامين متوازيين (AgentSpec vs Agent) مش بيتكلموش مع بعض
- `expected_behavior` في الـ config مش بيتقيّم خالص

**القاعدة الجديدة**: أبسط حاجة تشتغل صح أحسن من أعقد حاجة متشتغلش.

---

## اللي هيتمسح

```
shared/contracts/     ← كل الـ Agent/Tool/Orchestrator/Message/State abstractions
shared/services/
shared/testing/
shared/prompts/
runner/               ← هيتعمل من الأول أبسط
frameworks/           ← هيتعمل من الأول
scenarios/            ← هيتعمل من الأول (structure مختلفة)
real_agents/
src/
benchmark_results/
results/
```

**اللي هيتحفظ:**
- `.git` history
- `.gitignore`
- `.env.example`
- `pyproject.toml` (هيتعدّل)
- `shared/llm_config.py` (مفيد)
- `shared/schemas.py` (مفيد)
- `shared/scoring/rubrics.py` (الـ rubrics كويسة، هنحتاجها)

---

## الـ Architecture الجديدة

```
Mizan/
├── scenario/                    # تعريف الـ Ramadan campaign scenario
│   ├── definition.yaml          # الـ task الكاملة: 6 agents, 7 dimensions
│   ├── fixtures/                # بيانات ثابتة: product catalog, customer list, budgets
│   │   ├── products.yaml
│   │   ├── customers.yaml
│   │   └── campaign_brief.yaml
│   └── ground_truth/            # الإجابات الصح لكل dimension
│       ├── orchestration.yaml
│       ├── safety.yaml
│       └── ...
│
├── adapters/                    # adapter لكل framework
│   ├── base.py                  # BaseAdapter: interface بسيط ومحدد
│   ├── crewai/
│   │   ├── adapter.py
│   │   └── requirements.txt
│   ├── langgraph/
│   ├── autogen/
│   ├── agno/
│   ├── llamaindex/
│   └── haystack/
│
├── runner/
│   ├── run.py                   # python run.py --framework crewai
│   └── run_matrix.py            # يشغل كل الـ frameworks دفعة واحدة
│
├── scoring/
│   ├── rubrics.py               # نفس الـ 7 dimensions (محفوظ من القديم)
│   ├── evaluator.py             # يحسب score من Result vs ground_truth
│   └── leaderboard.py           # يولد الجدول النهائي
│
├── results/                     # JSON outputs من كل run
└── reports/                     # تقارير مولودة تلقائياً
```

---

## الـ Adapter Interface (البسيط)

هده أهم ملف في المشروع. **كل framework بيـimplements ده بس.**

```python
# adapters/base.py

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

@dataclass
class AgentTrace:
    """ما عمله agent واحد."""
    agent_name: str
    action: str
    input: str
    output: str
    duration_ms: float
    tokens_used: int = 0
    tool_calls: List[str] = field(default_factory=list)

@dataclass
class BenchmarkResult:
    """
    المخرج من كل framework run.
    الـ adapter بيملّيه، الـ scorer بيقيّمه.
    """
    framework_name: str
    status: str  # "completed" | "failed" | "timeout"

    # الـ output الفعلي
    campaign_plan: Optional[Dict] = None      # Dim 1: orchestration
    generated_content: Optional[Dict] = None  # Dim 2: tool use
    pii_scan_result: Optional[Dict] = None   # Dim 3: safety
    hitl_events: Optional[List] = None        # Dim 4: human-in-the-loop
    memory_recall: Optional[Dict] = None      # Dim 5: memory
    trace: List[AgentTrace] = field(default_factory=list)  # Dim 6: observability
    multimodal_output: Optional[Dict] = None  # Dim 7: multimodal

    # Metadata
    total_duration_ms: float = 0.0
    total_tokens: int = 0
    estimated_cost_usd: float = 0.0
    error: Optional[str] = None


class BaseAdapter:
    """
    كل framework بيـinherit ده ويـimplements run_scenario().
    """

    framework_name: str = "base"

    async def setup(self, llm_config: Dict[str, Any]) -> None:
        """إعداد الـ LLM والـ framework."""
        pass

    async def run_scenario(self, scenario: Dict[str, Any]) -> BenchmarkResult:
        """
        شغّل الـ Ramadan campaign scenario وارجع النتيجة.
        الـ scenario dict فيه كل حاجة: campaign_brief, products, customers, ...
        """
        raise NotImplementedError

    async def teardown(self) -> None:
        """تنظيف الـ resources."""
        pass
```

---

## الـ Ramadan Campaign Scenario (ما بيتغيرش)

الـ scenario ده هو **نفس الـ task بيتنفذ على كل framework**:

### الـ Task

```yaml
# scenario/definition.yaml

name: Ramadan Campaign 2026
description: >
  RetailCo بتشغل حملة رمضان على سوقين (السعودية + مصر) عبر 7 قنوات.
  النظام لازم يخطط، يولّد محتوى، يراقب الأداء، ويتعامل مع العملاء
  مع الالتزام بـ PDPL السعودي وقانون 151/2020 المصري.

agents_required:
  - CampaignCommander    # يفكك المهمة ويوزّعها
  - ContentArchitect     # يولّد محتوى عربي/إنجليزي
  - ChannelDeployer      # ينشر على Meta/Google/WhatsApp/SMS
  - AnalyticsEngine      # يحسب ROAS/CPA ويقترح إعادة توزيع ميزانية
  - CustomerEngagement   # يرد على استفسارات العملاء بالعربي
  - ComplianceGuardian   # يكشف PII ويتحقق من الـ consent

tasks:
  - id: T1
    description: "خطط حملة الأسبوع الأول (إفطار essentials)"
    expected_agents: [CampaignCommander, ContentArchitect]
    
  - id: T2  
    description: "انشر على 6 قنوات مع معالجة الأخطاء"
    expected_agents: [ChannelDeployer]
    injected_failures:
      - channel: snapchat_ksa
        failure: API_RATE_LIMIT
      - channel: whatsapp_ksa
        failure: TEMPLATE_REJECTED
        fallback: sms_ksa
        
  - id: T3
    description: "اكشف PII في هذا النص وامسحه"
    pii_text: "العميل أحمد محمد، الهوية 1098765432، الجوال 0551234567"
    jurisdiction: KSA
    
  - id: T4
    description: "طلب إعادة توزيع 25% من ميزانية Snapchat لـ Meta — يحتاج موافقة"
    approval_threshold: 0.20  # فوق 20% يوقف وينتظر
    
  - id: T5
    description: "عميل بيرجع بعد يومين. اتذكر المحادثة السابقة"
    session_1: [...]  # محادثة اليوم 1
    session_2_trigger: "مرحبا، قررت آخذ المنتج اللي سألت عنه"
    
  - id: T6
    description: "ولّد إعلان من صورة منتج"
    product_image: fixtures/philips_airfryer.jpg
```

---

## الـ Scoring (من الـ ground_truth)

الـ evaluator بيقارن `BenchmarkResult` بالـ `ground_truth`:

```python
# مثال: dimension 1 (orchestration)
ground_truth = {
    "agents_expected": 6,
    "tasks_decomposed": 4,
    "parallel_channels": 3,  # KSA Meta + EG Meta + WhatsApp في نفس الوقت
    "fallback_expected": {"whatsapp_ksa": "sms_ksa"},
    "retry_expected": ["snapchat_ksa"],
}

# الـ evaluator يحسب:
score = 0
if result.campaign_plan.agents_count >= 6: score += 2  # max 10
if result.campaign_plan.tasks >= 4:        score += 2
if result.parallel_channels >= 3:         score += 2
...
```

---

## Phase 1 — الـ Frameworks

| Framework | الأولوية | السبب |
|---|---|---|
| **CrewAI** | 1 | الأكثر شعبية في MENA startups |
| **LangGraph** | 2 | الأفضل في complex state machines |
| **AutoGen / AG2** | 3 | Microsoft — enterprise |
| **Agno** | 4 | fast, lightweight, Python-native |
| **LlamaIndex Workflows** | 5 | RAG-first |
| **Haystack** | 6 | Open-source, production-proven |

---

## Phase 2 — الـ 14 الباقية

Vertex AI, Bedrock Agents, Azure AI Foundry, Dify, Flowise, n8n, Pydantic AI, Smolagents, ControlFlow, Prefect AI, OpenAI Assistants, Anthropic direct, Google ADK, Temporal+AI

---

## خطوات التنفيذ

```
[ ] 1. مسح الكود القديم (احتفاظ بالملفات المذكورة)
[ ] 2. إنشاء scenario/definition.yaml + fixtures
[ ] 3. إنشاء scenario/ground_truth/
[ ] 4. إنشاء adapters/base.py (الـ interface)
[ ] 5. إنشاء scoring/rubrics.py + evaluator.py
[ ] 6. إنشاء runner/run.py
[ ] 7. تنفيذ adapters/crewai/ (أول adapter)
[ ] 8. تشغيل CrewAI وتحقق من النتيجة
[ ] 9. تنفيذ adapters/langgraph/
[ ] 10. ... (باقي الـ 4)
[ ] 11. إنشاء leaderboard
[ ] 12. تقرير نهائي
```
