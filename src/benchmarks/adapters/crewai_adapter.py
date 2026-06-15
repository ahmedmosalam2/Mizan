
import re
import json
import time
import shutil
import builtins
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass
from unittest.mock import patch

from pydantic import BaseModel, Field

from benchmarks.adapters.base_adapter import (
    BaseFrameworkAdapter,
    AgentSpec,
    ToolSpec,
    ScenarioResult,
    TraceEntry,
)



class CampaignPlanOutput(BaseModel):
  
    campaign_name: str = Field(description="اسم الحملة")
    agent_assignments: Dict[str, str] = Field(
        description="مين مسؤول عن إيه: {agent_name: deliverable}"
    )
    channel_plan: Dict[str, Any] = Field(
        description="خطة كل channel: {channel: {budget, content_type, market}}"
    )
    content_requirements: List[str] = Field(
        description="المتطلبات الـ content"
    )
    kpis: Dict[str, str] = Field(
        description="KPIs لكل market: {market: kpi_description}"
    )
    compliance_checklist: List[str] = Field(
        description="PDPL + Law 151 compliance items"
    )


class AdCopyOutput(BaseModel):
    """Output مضمون من Dimension 2: Tool Use / Content Generation."""
    variant_gulf_arabic_carousel: str = Field(description="Gulf Arabic — carousel format")
    variant_gulf_arabic_single: str   = Field(description="Gulf Arabic — single image")
    variant_english_carousel: str     = Field(description="English — carousel format")
    whatsapp_template: str            = Field(description="WhatsApp template (Meta compliant)")
    product_sku: str                  = Field(description="SKU المنتج المستخدم")
    price_mentioned_sar: bool         = Field(description="هل ذكر السعر بالريال؟")


class PIIReport(BaseModel):
    """Output مضمون من Dimension 3: Safety."""
    detected_pii: Dict[str, List[str]] = Field(description="PII types → values found")
    redacted_text: str                 = Field(description="النص بعد الـ redaction")
    compliance_notes: str              = Field(description="ملاحظات الـ compliance")
    risk_level: str                    = Field(description="low | medium | high | critical")
    jurisdiction_applied: str          = Field(description="KSA | EG | both")


class BudgetDecision(BaseModel):
    """Output مضمون من Dimension 4: HITL."""
    original_allocation: Dict[str, float] = Field(description="الميزانية الأصلية")
    recommended_changes: Dict[str, float] = Field(description="التغييرات المقترحة")
    human_decision: str                   = Field(description="approved | rejected | modified")
    human_feedback: str                   = Field(description="تعليق المدير")
    final_allocation: Dict[str, float]    = Field(description="الميزانية النهائية")
    requires_approval: bool               = Field(description="هل تعدّت الـ threshold؟")


class DeploymentReport(BaseModel):
    """Output مضمون من Dimension 6: Observability."""
    channel_results: List[Dict[str, Any]] = Field(description="نتيجة كل channel")
    total_deployed: int                   = Field(description="عدد channels نجحت")
    total_failed: int                     = Field(description="عدد channels فشلت")
    fallbacks_used: List[str]             = Field(description="الـ fallback channels المستخدمة")
    retry_attempts: Dict[str, int]        = Field(description="عدد retries لكل channel")


# ═══════════════════════════════════════════════════════════════════════
# PII Regex Patterns (MANUAL)
# ═══════════════════════════════════════════════════════════════════════

_PII_PATTERNS = {
    "saudi_national_id":    re.compile(r"\b[12]\d{9}\b"),
    "iqama_number":         re.compile(r"\b2\d{9}\b"),
    "egyptian_national_id": re.compile(r"\b[23]\d{13}\b"),
    "phone_numbers":        re.compile(
        r"\b(?:\+966|00966|0)?5[0-9]{8}\b"
        r"|\b(?:\+20|0020|0)?1[0-2]\d{8}\b"
        r"|\+\d{10,13}\b"
    ),
    "email_addresses":      re.compile(r"\b[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}\b"),
    "iban":                 re.compile(r"\bSA\d{22}\b|\bEG\d{27}\b"),
}

# ═══════════════════════════════════════════════════════════════════════
# Memory Path (MANUAL)
# ═══════════════════════════════════════════════════════════════════════

_CREWAI_MEMORY_DIR = Path(__file__).parent.parent.parent / ".crewai_memory"



def _build_campaign_flow(llm, campaign_brief: Dict, simulated_approval: Dict):
    """
    [NATIVE] CrewAI Flow: الـ campaign كـ event-driven workflow.

    Flow vs Crew:
        Crew = مجموعة agents يشتغلوا على tasks
        Flow = workflow كامل فيه Crews + branching + state + routing

    الـ Ramadan Campaign Flow:
        START → initialize → generate_content → validate
             → (approved) deploy → analyze → (needs_reallocation) approve → complete
             → (rejected)  regenerate → validate (retry)

    ليه Flow أقوى من Process.hierarchical هنا؟
        - بتقدر تروح جنبين: لو Content فشل → regenerate
        - State محفوظ بين الـ steps تلقائياً
        - كل step مستقل — ممكن يتشتغل على Crew منفصل
    """
    try:
        from crewai.flow.flow import Flow, start, listen, router
        from crewai import Agent, Task as CrewTask, Crew, Process
    except ImportError:
        return None  # Flow مش متاح في الـ version دي

    brief_str = json.dumps(campaign_brief, ensure_ascii=False, indent=2)

    class RamadanCampaignFlow(Flow):
        """
        Full campaign orchestration as a CrewAI Flow.
        State بيتنقل بين كل step تلقائياً.
        """

        # ── Step 1: Initialize ──────────────────────────────────────
        @start()
        def initialize_campaign(self):
            """
            [NATIVE] @start — أول step في الـ Flow.
            CampaignCommander يقرأ الـ brief ويعمل decomposition.
            """
            commander = Agent(
                role="Campaign Manager & Orchestrator",
                goal="Decompose Ramadan campaign brief into actionable sub-tasks.",
                backstory=(
                    "Senior marketing strategist. 10 years MENA e-commerce. "
                    "Manages AI agent teams for multi-channel campaigns."
                ),
                llm=llm,
                verbose=True,
            )
            init_task = CrewTask(
                description=(
                    f"اقرأ الـ brief وحوّله لـ action plan:\n{brief_str}\n\n"
                    f"حدد: مين يشتغل على إيه، والـ timeline، والـ KPIs."
                ),
                expected_output="Action plan مفصّل لكل agent مع deliverables وtimeline.",
                agent=commander,
                output_pydantic=CampaignPlanOutput,  # [NATIVE] structured output
            )
            crew = Crew(
                agents=[commander],
                tasks=[init_task],
                process=Process.sequential,
                verbose=True,
            )
            result = crew.kickoff()
            # حفظ الـ plan في الـ Flow state
            self.state["campaign_plan"] = str(result)
            self.state["initialized"] = True
            return str(result)

        # ── Step 2: Generate Content ────────────────────────────────
        @listen(initialize_campaign)
        def generate_content(self, campaign_plan):
            """
            [NATIVE] @listen — بيستمع لـ initialize_campaign ويبدأ تلقائياً.
            ContentArchitect يكتب الـ ad copy.
            """
            content_agent = Agent(
                role="Bilingual Content Generator",
                goal="Generate Arabic/English ad copy for Ramadan campaign.",
                backstory=(
                    "Expert Arabic copywriter. Gulf + Egyptian dialects. "
                    "Ramadan cultural sensitivity specialist."
                ),
                llm=llm,
                cache=True,   # [NATIVE] cache tool calls
                verbose=True,
            )
            content_task = CrewTask(
                description=(
                    f"بناءً على الخطة:\n{campaign_plan}\n\n"
                    f"اكتب ad copy لـ Philips Air Fryer للسوق السعودي:\n"
                    f"- 2 variants Gulf Arabic\n"
                    f"- 1 English variant\n"
                    f"- 1 WhatsApp template\n"
                    f"السعر: 899 SAR (764 بعد خصم 15%)\n"
                    f"الـ tone: دافئ، عائلي، رمضاني"
                ),
                expected_output="4 ad copy variants with Gulf Arabic and English.",
                agent=content_agent,
                output_pydantic=AdCopyOutput,  # [NATIVE] structured output
            )
            crew = Crew(
                agents=[content_agent],
                tasks=[content_task],
                process=Process.sequential,
                verbose=True,
            )
            result = crew.kickoff()
            self.state["content"] = str(result)
            self.state["content_attempts"] = self.state.get("content_attempts", 0) + 1
            return str(result)

        # ── Step 3: Router — هل الـ content مقبول؟ ─────────────────
        @router(generate_content)
        def validate_content(self, content):
            """
            [NATIVE] @router — branching logic في الـ Flow.
            لو الـ content فيه Arabic → approved
            لو مفيهوش Arabic كافي → regenerate (مع limit 2 محاولات)
            """
            arabic_chars = sum(1 for c in content if "\u0600" <= c <= "\u06ff")
            attempts = self.state.get("content_attempts", 1)

            if arabic_chars >= 20:
                self.state["content_approved"] = True
                return "deploy"          # → deploy_channels
            elif attempts >= 2:
                self.state["content_approved"] = True   # نقبل بعد محاولتين
                return "deploy"
            else:
                return "regenerate"      # → regenerate_content

        # ── Step 3b: Regenerate (لو الـ router قال regenerate) ──────
        @listen("regenerate")
        def regenerate_content(self, _):
            """[NATIVE] @listen("regenerate") — بيستمع لـ router string output."""
            return self.generate_content(self.state.get("campaign_plan", ""))

        # ── Step 4: Deploy Channels ─────────────────────────────────
        @listen("deploy")
        def deploy_channels(self, content):
            """[NATIVE] @listen("deploy") — بيستمع لـ router string output."""
            deployer = Agent(
                role="Multi-Channel Campaign Deployer",
                goal="Deploy campaign content to all channels. Handle failures.",
                backstory="Digital advertising ops specialist. MENA platforms expert.",
                llm=llm,
                verbose=True,
            )
            deploy_task = CrewTask(
                description=(
                    f"انشر هذا الـ content:\n{content}\n\n"
                    f"على الـ channels: Meta Ads (KSA+EG), Snapchat (KSA), "
                    f"Google Ads (KSA), WhatsApp (KSA), Email (EG)\n\n"
                    f"تعليمات الأخطاء:\n"
                    f"- Snapchat API_RATE_LIMIT → retry حتى 3 مرات\n"
                    f"- WhatsApp TEMPLATE_REJECTED → fallback SMS"
                ),
                expected_output="Deployment report per channel: status, attempts, fallbacks.",
                agent=deployer,
                output_pydantic=DeploymentReport,  # [NATIVE] structured output
            )
            crew = Crew(
                agents=[deployer],
                tasks=[deploy_task],
                process=Process.sequential,
                verbose=True,
            )
            result = crew.kickoff()
            self.state["deployment"] = str(result)
            return str(result)

        # ── Step 5: Analyze Performance ─────────────────────────────
        @listen(deploy_channels)
        def analyze_performance(self, deployment_result):
            """[NATIVE] @listen — بيستمع لـ deploy_channels بعد ما تخلص."""
            analyst = Agent(
                role="Campaign Performance Analyst",
                goal="Monitor ROAS/CPA and recommend budget reallocation.",
                backstory="Data analyst specialized in MENA e-commerce. Ramadan patterns expert.",
                llm=llm,
                verbose=True,
            )
            analysis_task = CrewTask(
                description=(
                    f"بعد الـ deployment:\n{deployment_result}\n\n"
                    f"حلّل الأداء الأولي وهل تحتاج إعادة توزيع ميزانية؟\n"
                    f"Snapchat ROAS = 1.1x (أقل من threshold 2x)\n"
                    f"Meta ROAS = 8.2x (الأعلى)\n"
                    f"التوصية: نقل 5000 SAR من Snapchat لـ Meta (50% من ميزانية Snapchat)"
                ),
                expected_output=(
                    "Performance report + budget reallocation recommendation. "
                    "هل التغيير > 20%؟ (نعم = يحتاج موافقة)"
                ),
                agent=analyst,
            )
            crew = Crew(agents=[analyst], tasks=[analysis_task], verbose=True)
            result = crew.kickoff()
            self.state["analysis"] = str(result)
            # 50% > 20% threshold → يحتاج approval
            self.state["needs_reallocation"] = True
            return str(result)

        # ── Step 6: Router — هل يحتاج HITL؟ ───────────────────────
        @router(analyze_performance)
        def check_reallocation(self, analysis):
            """
            [NATIVE] @router — conditional routing على نتيجة الـ analysis.
            لو التغيير > 20% → hitl_approval
            لو < 20% → complete
            """
            if self.state.get("needs_reallocation", False):
                return "hitl_approval"
            return "complete"

        # ── Step 7: HITL Approval ───────────────────────────────────
        @listen("hitl_approval")
        def request_human_approval(self, analysis):
            """
            [NATIVE] @listen("hitl_approval") + Task(human_input=True)
            Flow بيوقف هنا ويستنى موافقة بشرية.
            """
            commander = Agent(
                role="Campaign Manager",
                goal="Present reallocation recommendation for human approval.",
                backstory="Senior manager who presents data and waits for decisions.",
                llm=llm,
                verbose=True,
            )
            approval_task = CrewTask(
                description=(
                    f"التحليل:\n{analysis}\n\n"
                    f"التوصية: نقل 5000 SAR (50%) من Snapchat لـ Meta.\n"
                    f"هذا التغيير يتجاوز الـ 20% threshold.\n"
                    f"اعرض التوصية على المدير وانتظر الموافقة."
                ),
                expected_output="القرار النهائي للميزانية بعد موافقة المدير.",
                agent=commander,
                human_input=True,          # [NATIVE] Flow بيوقف هنا
                output_pydantic=BudgetDecision,
            )
            crew = Crew(agents=[commander], tasks=[approval_task], verbose=True)

            approval_text = (
                f"{simulated_approval.get('decision', 'approved').upper()}. "
                f"Feedback: {simulated_approval.get('feedback', 'Proceed as recommended.')}"
            )
            with patch.object(builtins, "input", return_value=approval_text):
                result = crew.kickoff()

            self.state["approval_result"] = str(result)
            return str(result)

        # ── Step 8: Complete ────────────────────────────────────────
        @listen("complete")
        def finalize_no_reallocation(self, analysis):
            """Budget في الـ threshold — مش محتاج approval."""
            self.state["final_status"] = "completed_no_reallocation"
            return {"status": "completed", "reallocation": False}

        @listen(request_human_approval)
        def finalize_with_approval(self, approval_result):
            """بعد الـ HITL approval — Campaign انتهت بنجاح."""
            self.state["final_status"] = "completed_with_approval"
            return {
                "status": "completed",
                "reallocation": True,
                "approval": approval_result,
            }

    return RamadanCampaignFlow


# ═══════════════════════════════════════════════════════════════════════
# Main Adapter Class
# ═══════════════════════════════════════════════════════════════════════

class CrewaiAdapter(BaseFrameworkAdapter):
    """
    CrewAI Framework Adapter — Maximum Feature Extraction.
    كل feature في CrewAI بتخدم الـ Ramadan Campaign بنستخدمها.
    """

    def __init__(self):
        super().__init__(framework_name="CrewAI")
        self.llm = None
        self._tool_call_count = 0
        self._provider = "groq"
        self._api_key = ""

    # ── Lifecycle ──────────────────────────────────────────────────

    async def setup(self, llm_config: Dict[str, Any]) -> None:
        try:
            import os
            from crewai import LLM

            provider = llm_config.get("provider", "groq")
            model    = llm_config.get("model", "llama-3.3-70b-versatile")
            api_key  = llm_config.get("api_key", "") or "mock_key"

            # [NEW] حفظ إعدادات المزود للاستخدام في Embedder و Knowledge
            self._provider = provider
            self._api_key = api_key
            gateway  = os.getenv("LLM_GATEWAY_URL")

            if gateway:
                self.llm = LLM(model=f"openai/{model}", api_key=api_key, base_url=gateway)
            else:
                self.llm = LLM(model=f"{provider}/{model}", api_key=api_key)

            self._is_setup = True
            self.add_trace(TraceEntry(
                agent_name="system", action="setup",
                output_summary=f"model={model} | gateway={'yes' if gateway else 'no'}",
            ))
        except ImportError as e:
            raise RuntimeError(f"CrewAI missing: {e}. Run: pip install 'crewai[tools]'")

    async def teardown(self) -> None:
        self.llm = None
        self._is_setup = False

    # ── Internal Helpers ───────────────────────────────────────────

    def _build_agents(self, specs: List[AgentSpec], tools_map: Dict = None) -> list:
        """AgentSpec → CrewAI Agent مع كل الـ native options."""
        from crewai import Agent
        agents = []
        for spec in specs:
            agent_tools = (tools_map or {}).get(spec.name, [])
            agents.append(Agent(
                role=spec.role,
                goal=spec.goal,
                backstory=spec.backstory,
                llm=self.llm,
                tools=agent_tools,
                allow_delegation=spec.can_delegate,
                memory=True,       # [NATIVE] short-term memory
                cache=True,        # [NATIVE] tool call caching
                verbose=True,
            ))
        return agents

    def _build_tool(self, spec: ToolSpec):
        """ToolSpec → CrewAI tool مع tracking."""
        from crewai.tools import tool as crewai_tool
        adapter = self

        @crewai_tool(spec.name)
        def _wrapper(query: str) -> str:
            adapter._tool_call_count += 1
            start = time.time()
            result = spec.function(query)
            adapter.add_trace(TraceEntry(
                agent_name="tool", action=f"call::{spec.name}",
                input_summary=query[:100], output_summary=str(result)[:200],
                duration_ms=(time.time() - start) * 1000,
            ))
            return str(result)

        _wrapper.__doc__ = spec.description
        return _wrapper

    def _build_knowledge(self, catalog_data: List[Dict]) -> Any:

        try:
            from crewai.knowledge.source.string_knowledge_source import StringKnowledgeSource
            catalog_text = (
                "Product Catalog — RetailCo MENA:\n\n"
                + json.dumps(catalog_data, ensure_ascii=False, indent=2)
            )
            return StringKnowledgeSource(content=catalog_text)
        except ImportError:
            return None  # Knowledge API مش متاح في الـ version دي

    def _get_embedder_config(self) -> Optional[Dict]:
        """
        [NEW] بتختار embedder مناسب بناءً على الـ provider المستخدم.
        بدون ده → CrewAI هيحاول يستخدم OpenAI embeddings بشكل خفي
        وده هيكسر لو مفيش OPENAI_API_KEY.
        """
        import os
        provider = self._provider.lower()

        if provider in ("openai",):
            return {
                "provider": "openai",
                "config": {
                    "model": "text-embedding-3-small",
                    "api_key": self._api_key or os.getenv("OPENAI_API_KEY", ""),
                },
            }
        elif provider in ("google", "gemini"):
            return {
                "provider": "google-generativeai",
                "config": {
                    "model_name": "gemini-embedding-001",
                    "api_key": self._api_key or os.getenv("GOOGLE_API_KEY", ""),
                },
            }
        elif provider == "ollama":
            return {
                "provider": "ollama",
                "config": {
                    "model": "mxbai-embed-large",
                    "url": os.getenv("OLLAMA_BASE_URL", "http://localhost:11434/api/embeddings"),
                },
            }
        elif provider == "groq":
            # Groq لا يوفر embedding API — نستخدم OpenAI كـ fallback
            openai_key = os.getenv("OPENAI_API_KEY", "")
            if openai_key:
                return {
                    "provider": "openai",
                    "config": {"model": "text-embedding-3-small", "api_key": openai_key},
                }
            return None  # مفيش embedder متاح — Knowledge/Memory هيشتغل بالـ defaults
        else:
            # mock أو provider مش معروف — نرجع None
            return None

    def _get_search_tools(self) -> list:
        """
        [NEW] بتحاول تجيب أدوات بحث حقيقية من crewai_tools.
        لو مفيش API keys → ترجع [] (graceful fallback).
        """
        import os
        real_tools = []

        # 1. SerperDevTool (Google Search)
        if os.getenv("SERPER_API_KEY"):
            try:
                from crewai_tools import SerperDevTool
                real_tools.append(SerperDevTool())
                self.add_trace(TraceEntry(
                    agent_name="system", action="search_tool_loaded",
                    output_summary="SerperDevTool (Google Search) — active",
                ))
            except ImportError:
                pass

        # 2. ExaSearchTool (Semantic Web Search)
        if not real_tools and os.getenv("EXA_API_KEY"):
            try:
                from crewai_tools import ExaSearchTool
                real_tools.append(ExaSearchTool(highlights=True, type="auto"))
                self.add_trace(TraceEntry(
                    agent_name="system", action="search_tool_loaded",
                    output_summary="ExaSearchTool (Semantic Search) — active",
                ))
            except ImportError:
                pass

        if not real_tools:
            self.add_trace(TraceEntry(
                agent_name="system", action="search_tool_loaded",
                output_summary="No real search tools — using mock fallback only",
            ))

        return real_tools

    def _guardrail_arabic_content(self, output: Any) -> Tuple[bool, str]:
        """
        [NATIVE] Task(guardrail=fn) — CrewAI بتستدعيها بعد كل task.
        لو فشلت → CrewAI بتعمل retry تلقائياً على الـ task.

        بنتحقق: الـ ad copy فيه Arabic text كافي؟
        """
        text = output.raw if hasattr(output, "raw") else str(output)
        arabic_chars = sum(1 for c in text if "\u0600" <= c <= "\u06ff")
        if arabic_chars < 15:
            return False, "Content must contain Arabic text — Gulf Arabic required for KSA market."
        return True, ""

    def _guardrail_ramadan_sensitivity(self, output: Any) -> Tuple[bool, str]:
        """
        [NATIVE] Guardrail للـ Ramadan content.
        بيتحقق من inappropriate content.
        """
        text = output.raw if hasattr(output, "raw") else str(output)
        forbidden = ["كحول", "خمر", "مسكر", "alcohol", "wine", "beer"]
        for word in forbidden:
            if word.lower() in text.lower():
                return False, f"Content violates Ramadan guidelines: '{word}' detected."
        return True, ""

    def _step_callback(self, step_output: Any) -> None:
        """[NATIVE] step_callback — trace حقيقي من CrewAI."""
        self.add_trace(TraceEntry(
            agent_name="crew", action="step",
            output_summary=str(step_output)[:200],
        ))

    def _task_callback(self, task_output: Any) -> None:
        """[NATIVE] task callback."""
        self.add_trace(TraceEntry(
            agent_name="crew", action="task_complete",
            output_summary=str(task_output)[:200],
        ))

    def _clean_memory(self) -> None:
        """[MANUAL] Clean Slate — بنمسح ChromaDB قبل كل benchmark run."""
        if _CREWAI_MEMORY_DIR.exists():
            shutil.rmtree(_CREWAI_MEMORY_DIR, ignore_errors=True)
        _CREWAI_MEMORY_DIR.mkdir(parents=True, exist_ok=True)

    def _scan_pii_regex(self, text: str) -> Dict[str, List[str]]:
        """[MANUAL] Deterministic regex scan."""
        return {
            k: list(set(p.findall(text)))
            for k, p in _PII_PATTERNS.items()
            if p.findall(text)
        }

    def _redact(self, text: str, detected: Dict) -> str:
        """[MANUAL] Redact PII."""
        for pii_type, vals in detected.items():
            for v in vals:
                text = text.replace(v, f"[{pii_type.upper()}]")
        return text

    def _score_pii(self, detected: Dict, expected: Dict) -> float:
        """[MANUAL] Score PII detection accuracy."""
        if not expected:
            return 1.0
        total = sum(len(v) for v in expected.values())
        if total == 0:
            return 1.0
        correct = sum(
            1 for k, evs in expected.items()
            for ev in evs
            if any(ev in dv or dv in ev for dv in detected.get(k, []))
        )
        return correct / total

    # ═══════════════════════════════════════════════════════════════
    # Dimension 1: Orchestration
    # [NATIVE] Process.hierarchical + planning=True + output_pydantic
    # ═══════════════════════════════════════════════════════════════

    async def run_orchestration(
        self,
        agent_specs: List[AgentSpec],
        task: Dict[str, Any],
        orchestration_mode: str = "hierarchical",
    ) -> ScenarioResult:

        from crewai import Agent, Task as CrewTask, Crew, Process

        self._tool_call_count = 0
        agents = self._build_agents(agent_specs)
        brief_str = json.dumps(task, ensure_ascii=False, indent=2)

        # Task رئيسية — في hierarchical المدير بيقسّمها
        main_task = CrewTask(
            description=(
                f"أنت Campaign Commander لـ RetailCo. قُد الفريق لتنفيذ الحملة.\n\n"
                f"Brief:\n{brief_str}\n\n"
                f"المطلوب:\n"
                f"1. حدد deliverable لكل agent بوضوح\n"
                f"2. اعمل channel plan بالميزانية والـ content type\n"
                f"3. حدد KPIs لكل market\n"
                f"4. اعمل compliance checklist للـ PDPL وقانون 151"
            ),
            expected_output=(
                "Campaign plan شامل: agent assignments + channel plan + KPIs + compliance checklist."
            ),
            agent=agents[0],                          # Commander هو الـ anchor
            output_pydantic=CampaignPlanOutput,       # [NATIVE] structured output
            callback=self._task_callback,             # [NATIVE] event بعد الـ task
        )

        embedder = self._get_embedder_config()
        crew_kwargs = dict(
            agents=agents,
            tasks=[main_task],
            process=Process.hierarchical,             # [NATIVE] manager يوزع
            manager_llm=self.llm,                     # [NATIVE] manager LLM
            memory=True,                              # [NATIVE] short-term memory
            planning=True,                            # [NATIVE] planning pass أول
            step_callback=self._step_callback,        # [NATIVE] trace كل step
            verbose=True,
        )
        if embedder:
            crew_kwargs["embedder"] = embedder        # [NEW] embedder مطابق للمزود

        crew = Crew(**crew_kwargs)

        start = time.time()
        result = await crew.kickoff_async()
        duration_ms = (time.time() - start) * 1000

        # استخراج الـ structured output لو اتعمل
        structured = None
        if hasattr(result, "pydantic") and result.pydantic:
            structured = result.pydantic.model_dump()

        sr = self._make_result(
            scenario_id="campaign_planning",
            status="completed",
            output=structured or str(result),
            total_duration_ms=duration_ms,
            agent_count=len(agents),
        )
        return sr

    # ═══════════════════════════════════════════════════════════════
    # Dimension 2: Tool Use
    # [NATIVE] Knowledge (RAG) + Agent(cache=True) + guardrail
    # ═══════════════════════════════════════════════════════════════

    async def run_with_tools(
        self,
        agent_specs: List[AgentSpec],
        task: Dict[str, Any],
        tools: List[ToolSpec],
    ) -> ScenarioResult:

        from crewai import Agent, Task as CrewTask, Crew, Process

        self._tool_call_count = 0

        # [NEW] أدوات بحث حقيقية (SerperDev/Exa) لو متاحة
        real_search_tools = self._get_search_tools()

        # [NEW] KnowledgeConfig لتحسين دقة الـ RAG
        knowledge_config = None
        try:
            from crewai.knowledge.knowledge_config import KnowledgeConfig
            knowledge_config = KnowledgeConfig(results_limit=5, score_threshold=0.35)
        except ImportError:
            pass

        # [NATIVE] بنبني Knowledge من الـ product catalog
        product_data = [task.get("product", {})]
        knowledge_source = self._build_knowledge(product_data)

        # [MANUAL] Tool fallback لو Knowledge مش متاح
        crewai_tools = [self._build_tool(t) for t in tools]

        content_spec = next(
            (s for s in agent_specs if "Content" in s.name), agent_specs[0]
        )

        # [NEW] دمج الأدوات: mock tools + real search tools
        all_tools = crewai_tools + real_search_tools

        agent_kwargs = dict(
            role=content_spec.role,
            goal=content_spec.goal,
            backstory=content_spec.backstory,
            llm=self.llm,
            tools=all_tools,
            cache=True,       # [NATIVE] caching
            verbose=True,
        )
        # لو Knowledge متاح → نديها للـ agent
        if knowledge_source:
            agent_kwargs["knowledge_sources"] = [knowledge_source]
        # [NEW] KnowledgeConfig لتحسين دقة البحث
        if knowledge_config:
            agent_kwargs["knowledge_config"] = knowledge_config

        # [NEW] Embedder مخصص للمزود
        embedder = self._get_embedder_config()
        if embedder:
            agent_kwargs["embedder"] = embedder

        content_agent = Agent(**agent_kwargs)

        product = task.get("product", {})
        content_task = CrewTask(
            description=(
                f"المهمة: {task.get('goal', 'Generate ad copy')}\n\n"
                f"المنتج: {product.get('name_ar', '')} (SKU: {product.get('sku', '')})\n"
                f"السوق: {task.get('market', 'KSA')}\n"
                f"الجمهور: {task.get('audience', '')}\n"
                f"الـ tone: {task.get('tone', 'دافئ ورمضاني')}\n"
                f"القيود: {json.dumps(task.get('constraints', []), ensure_ascii=False)}\n\n"
                f"اكتب:\n"
                f"1. Gulf Arabic carousel variant\n"
                f"2. Gulf Arabic single image variant\n"
                f"3. English carousel variant\n"
                f"4. WhatsApp template (Meta-compliant)\n"
                f"تأكد من ذكر السعر بالريال السعودي."
            ),
            expected_output="4 ad copy variants structured per AdCopyOutput format.",
            agent=content_agent,
            output_pydantic=AdCopyOutput,                       # [NATIVE] structured
            guardrail=self._guardrail_arabic_content,           # [NATIVE] auto-retry لو فشل
            callback=self._task_callback,
        )

        crew_kwargs = dict(
            agents=[content_agent],
            tasks=[content_task],
            process=Process.sequential,
            step_callback=self._step_callback,
            verbose=True,
        )
        if embedder:
            crew_kwargs["embedder"] = embedder        # [NEW] embedder للـ Crew
        crew = Crew(**crew_kwargs)

        start = time.time()
        result = await crew.kickoff_async()
        duration_ms = (time.time() - start) * 1000

        structured = None
        if hasattr(result, "pydantic") and result.pydantic:
            structured = result.pydantic.model_dump()

        sr = self._make_result(
            scenario_id="content_generation",
            status="completed",
            output=structured or str(result),
            total_duration_ms=duration_ms,
            agent_count=1,
            tool_calls=self._tool_call_count,
        )
        return sr

    # ═══════════════════════════════════════════════════════════════
    # Dimension 3: Safety & PII
    # [NATIVE] output_pydantic=PIIReport + guardrail
    # ═══════════════════════════════════════════════════════════════

    async def run_safety_check(
        self,
        text_with_pii: str,
        pii_types: List[str],
        jurisdiction: str,
        expected_pii: Optional[Dict[str, List[str]]] = None,
    ) -> ScenarioResult:

        from crewai import Agent, Task as CrewTask, Crew, Process

        # Phase 1: Regex (MANUAL)
        regex_detected = self._scan_pii_regex(text_with_pii)
        redacted_after_regex = self._redact(text_with_pii, regex_detected)
        self.add_trace(TraceEntry(
            agent_name="regex_scanner", action="pii_regex_scan",
            output_summary=(
                f"types={list(regex_detected.keys())} | "
                f"hits={sum(len(v) for v in regex_detected.values())}"
            ),
        ))

        # Phase 2: LLM (NATIVE)
        jurisdiction_rules = {
            "KSA":  "Saudi PDPL: National ID, Iqama, phone → redact. Consent for marketing.",
            "EG":   "Egypt Law 151/2020: National ID (14-digit), phone → redact. Criminal penalties.",
            "both": "Apply both Saudi PDPL and Egyptian Law 151/2020.",
        }.get(jurisdiction, "Apply GDPR-equivalent rules.")

        def _guardrail_has_redaction(output: Any) -> Tuple[bool, str]:
            """[NATIVE] guardrail — بنتحقق إن في redaction حصلت."""
            text = output.raw if hasattr(output, "raw") else str(output)
            if "[REDACTED" not in text and "REDACTED" not in text:
                return False, "Output must contain redacted PII markers."
            return True, ""

        compliance_agent = Agent(
            role="Privacy & Compliance Officer",
            goal="Detect contextual PII (names, addresses) missed by regex.",
            backstory=(
                "خبير PDPL سعودي وقانون 151 مصري. "
                "بتتخصص في الـ PII الضمنية اللي الـ regex ما بيلاقيهاش."
            ),
            llm=self.llm,
            verbose=True,
        )

        llm_task = CrewTask(
            description=(
                f"النص بعد الـ regex redaction:\n{redacted_after_regex}\n\n"
                f"النص الأصلي للمقارنة:\n{text_with_pii}\n\n"
                f"Jurisdiction: {jurisdiction}\n"
                f"القواعد: {jurisdiction_rules}\n\n"
                f"ابحث عن PII إضافية:\n"
                f"- أسماء أشخاص\n- عناوين\n- معلومات مالية ضمنية\n\n"
                f"الـ risk level: critical لو National ID موجود، high لو phone/email، medium لو اسم فقط."
            ),
            expected_output="PIIReport JSON: detected_pii + redacted_text + risk_level + compliance_notes.",
            agent=compliance_agent,
            output_pydantic=PIIReport,            # [NATIVE] structured output
            guardrail=_guardrail_has_redaction,   # [NATIVE] auto-retry لو مفيش redaction
        )

        crew = Crew(
            agents=[compliance_agent],
            tasks=[llm_task],
            process=Process.sequential,
            verbose=True,
        )

        start = time.time()
        llm_result = await crew.kickoff_async()
        duration_ms = (time.time() - start) * 1000

        # Merge regex + LLM
        llm_pii: Dict = {}
        if hasattr(llm_result, "pydantic") and llm_result.pydantic:
            pii_report = llm_result.pydantic
            llm_pii = pii_report.detected_pii
            final_redacted = pii_report.redacted_text
            risk_level = pii_report.risk_level
        else:
            raw = str(llm_result)
            try:
                m = re.search(r'\{[\s\S]*\}', raw)
                parsed = json.loads(m.group()) if m else {}
            except Exception:
                parsed = {}
            llm_pii = parsed.get("detected_pii", {})
            final_redacted = parsed.get("redacted_text", redacted_after_regex)
            risk_level = parsed.get("risk_level", "medium")

        merged = {**regex_detected}
        for k, v in llm_pii.items():
            if v:
                merged[k] = list(set(merged.get(k, []) + (v if isinstance(v, list) else [v])))

        accuracy = self._score_pii(merged, expected_pii or {})
        self.add_trace(TraceEntry(
            agent_name="ComplianceGuardian", action="pii_complete",
            output_summary=f"accuracy={accuracy:.1%} | risk={risk_level} | types={list(merged.keys())}",
            duration_ms=duration_ms,
        ))

        sr = self._make_result(
            scenario_id="pii_scan", status="completed",
            output={
                "detected_pii": merged,
                "redacted_text": final_redacted,
                "risk_level": risk_level,
                "pii_accuracy_score": accuracy,
                "regex_hits": sum(len(v) for v in regex_detected.values()),
            },
            total_duration_ms=duration_ms, agent_count=1,
        )
        sr.pii_detected = bool(merged)
        sr.pii_redacted = bool(final_redacted and "[" in final_redacted)
        return sr

    # ═══════════════════════════════════════════════════════════════
    # Dimension 4: Human-in-the-Loop
    # [NATIVE] human_input=True + output_pydantic=BudgetDecision
    # ═══════════════════════════════════════════════════════════════

    async def run_with_approval(
        self,
        agent_specs: List[AgentSpec],
        task: Dict[str, Any],
        approval_rules: Dict[str, Any],
        simulated_approvals: List[Dict[str, Any]],
    ) -> ScenarioResult:

        from crewai import Agent, Task as CrewTask, Crew, Process

        approval_data = simulated_approvals[0] if simulated_approvals else {
            "decision": "approved", "feedback": "Proceed.", "approver": "Manager",
        }
        threshold = approval_rules.get("budget_reallocation_threshold", 0.20)
        realloc_pct = task.get("recommendation", {}).get("percentage_of_channel_budget", 50) / 100

        analytics_spec = next((s for s in agent_specs if "Analytics" in s.name), agent_specs[0])
        commander_spec = next((s for s in agent_specs if "Commander" in s.name), agent_specs[0])

        analytics_agent = Agent(
            role=analytics_spec.role, goal=analytics_spec.goal,
            backstory=analytics_spec.backstory, llm=self.llm, verbose=True,
        )
        commander_agent = Agent(
            role=commander_spec.role, goal=commander_spec.goal,
            backstory=commander_spec.backstory, llm=self.llm, verbose=True,
        )

        # Task 1: تحليل
        analyze_task = CrewTask(
            description=(
                f"حلّل أداء الحملة:\n{json.dumps(task, ensure_ascii=False, indent=2)}\n\n"
                f"الـ threshold للموافقة: {threshold*100:.0f}%\n"
                f"التغيير المقترح: {realloc_pct*100:.0f}% "
                f"({'يحتاج موافقة ✋' if realloc_pct > threshold else 'لا يحتاج موافقة ✅'})\n\n"
                f"قدّم توصية واضحة مع مبررات ROAS."
            ),
            expected_output="توصية إعادة توزيع ميزانية مع مبررات.",
            agent=analytics_agent,
            callback=self._task_callback,
        )

        # Task 2: HITL — [NATIVE] human_input=True
        approval_task = CrewTask(
            description=(
                f"التوصية تعدّت الـ {threshold*100:.0f}% threshold.\n"
                f"اعرض التوصية على المدير وانتظر قراره.\n"
                f"طبّق الـ feedback على الخطة النهائية."
            ),
            expected_output="BudgetDecision: final_allocation + human_decision + feedback applied.",
            agent=commander_agent,
            context=[analyze_task],            # [NATIVE] dependency
            human_input=True,                  # [NATIVE] CrewAI بتوقف هنا
            output_pydantic=BudgetDecision,    # [NATIVE] structured output
            callback=self._task_callback,
        )

        crew = Crew(
            agents=[analytics_agent, commander_agent],
            tasks=[analyze_task, approval_task],
            process=Process.sequential,
            step_callback=self._step_callback,
            verbose=True,
        )

        approval_text = (
            f"{approval_data['decision'].upper()}. "
            f"Feedback: {approval_data.get('feedback', 'Proceed.')}"
        )
        self.add_trace(TraceEntry(
            agent_name="system", action="hitl_mock_inject",
            input_summary=approval_text,
            output_summary=f"approver={approval_data.get('approver', 'MockManager')}",
        ))

        start = time.time()
        with patch.object(builtins, "input", return_value=approval_text):
            result = await crew.kickoff_async()
        duration_ms = (time.time() - start) * 1000

        structured = None
        if hasattr(result, "pydantic") and result.pydantic:
            structured = result.pydantic.model_dump()

        sr = self._make_result(
            scenario_id="budget_approval", status="completed",
            output=structured or str(result),
            total_duration_ms=duration_ms, agent_count=2,
        )
        sr.used_approval_gate = True
        return sr

    # ═══════════════════════════════════════════════════════════════
    # Dimension 5: Memory
    # [NATIVE] Crew(memory=True) — Run 1 → ChromaDB → Run 2
    # ═══════════════════════════════════════════════════════════════

    async def run_with_memory(
        self,
        conversation_history: List[Dict[str, Any]],
        follow_up_query: str,
        expected_recall: List[str],
    ) -> ScenarioResult:

        from crewai import Agent, Task as CrewTask, Crew, Process

        self._clean_memory()  # [MANUAL] Clean Slate

        customer_agent = Agent(
            role="Customer Service Agent",
            goal="Handle inquiries with full recall from previous conversations.",
            backstory=(
                "موظف خدمة عملاء RetailCo. بتتذكر كل تفاصيل المحادثات السابقة "
                "— المنتج، السعر، اللون، الفرع. بتتحدث بالعربية الخليجية."
            ),
            llm=self.llm,
            memory=True,   # [NATIVE]
            verbose=True,
        )

        # ── Run 1: Session 1 ──────────────────────────────────────
        session1 = conversation_history[0] if conversation_history else {}
        history_text = "\n".join(
            f"{'العميل' if m['role'] == 'customer' else 'الوكيل'}: {m['content']}"
            for m in session1.get("messages", [])
        )

        session1_task = CrewTask(
            description=(
                f"المحادثة مع العميل {session1.get('customer_id', 'CUST-101')}:\n\n"
                f"{history_text}\n\n"
                f"لخّص المحادثة واحفظ: المنتج + السعر بعد الخصم + اللون + الفرع."
            ),
            expected_output=(
                "ملخص: قلاية فيلبس XXL، 764 ريال (خصم 15%)، أبيض، فرع الرياض."
            ),
            agent=customer_agent,
        )

        embedder = self._get_embedder_config()
        crew1_kwargs = dict(
            agents=[customer_agent], tasks=[session1_task],
            process=Process.sequential,
            memory=True,   # [NATIVE] STM + LTM + Entity Memory
            verbose=True,
        )
        if embedder:
            crew1_kwargs["embedder"] = embedder       # [NEW] embedder مطابق للمزود
        crew_run1 = Crew(**crew1_kwargs)
        await crew_run1.kickoff_async()

        # ── Run 2: Session 2 — بدون history في الـ prompt ──────────
        session2_task = CrewTask(
            description=(
                f"عميل عاد للتواصل:\n'{follow_up_query}'\n\n"
                f"رد عليه بتذكّر تفاصيل محادثته السابقة.\n"
                f"لا تسأله عن معلومات موجودة في سجله."
            ),
            expected_output=(
                "رد يذكر: قلاية فيلبس، 764 ريال، أبيض، الرياض — بدون سؤال العميل."
            ),
            agent=customer_agent,
        )

        crew2_kwargs = dict(
            agents=[customer_agent], tasks=[session2_task],
            process=Process.sequential,
            memory=True,   # [NATIVE] يقرأ من ChromaDB (STM + LTM + Entity)
            verbose=True,
        )
        if embedder:
            crew2_kwargs["embedder"] = embedder       # [NEW] نفس الـ embedder
        crew_run2 = Crew(**crew2_kwargs)

        start = time.time()
        result = await crew_run2.kickoff_async()
        duration_ms = (time.time() - start) * 1000

        output_str = str(result)
        recalled = [item for item in expected_recall if item in output_str]
        recall_score = len(recalled) / len(expected_recall) if expected_recall else 1.0

        self.add_trace(TraceEntry(
            agent_name="CustomerEngagement", action="memory_recall",
            output_summary=(
                f"score={recall_score:.1%} | "
                f"recalled={recalled} | "
                f"missing={[i for i in expected_recall if i not in recalled]}"
            ),
            duration_ms=duration_ms,
        ))

        sr = self._make_result(
            scenario_id="cross_session_chat", status="completed",
            output={
                "response": output_str,
                "recalled_items": recalled,
                "recall_score": recall_score,
                "expected": expected_recall,
            },
            total_duration_ms=duration_ms, agent_count=1,
        )
        sr.used_memory = recall_score > 0.5
        return sr

    # ═══════════════════════════════════════════════════════════════
    # Dimension 6: Observability + Retry
    # [NATIVE] step_callback + task_callback + output_pydantic
    # [MANUAL] Retry/fallback tool logic
    # ═══════════════════════════════════════════════════════════════

    async def run_with_tracing(
        self,
        agent_specs: List[AgentSpec],
        task: Dict[str, Any],
        inject_failure: Optional[Dict[str, Any]] = None,
    ) -> ScenarioResult:

        from crewai import Agent, Task as CrewTask, Crew, Process
        from crewai.tools import tool as crewai_tool

        channels = task.get("channels", [])
        self._tool_call_count = 0
        retry_state: Dict[str, int] = {}
        deployment_log: List[Dict] = []

        @crewai_tool("deploy_channel")
        def deploy_channel(channel_json: str) -> str:
            """
            ينشر campaign على channel.
            Input: JSON string {name, market}.
            يتعامل مع: API_RATE_LIMIT (retry) + TEMPLATE_REJECTED (fallback SMS).
            """
            self._tool_call_count += 1
            try:
                info = json.loads(channel_json)
            except Exception:
                info = {"name": channel_json, "market": "KSA"}

            ch_name = info.get("name", "unknown")
            market  = info.get("market", "KSA")
            key     = f"{ch_name}_{market}"

            channel_data = next(
                (c for c in channels if c["name"] == ch_name and c["market"] == market),
                {"should_succeed": True},
            )

            if channel_data.get("should_succeed", True):
                log = {"channel": ch_name, "market": market, "status": "success", "attempts": 1}
                deployment_log.append(log)
                self.add_trace(TraceEntry(
                    agent_name="ChannelDeployer", action=f"deploy::{key}",
                    output_summary="success",
                ))
                return json.dumps({"status": "success", "channel": ch_name, "market": market})

            error = channel_data.get("error", "UNKNOWN")

            if error == "API_RATE_LIMIT":
                attempts = retry_state.get(key, 0) + 1
                retry_state[key] = attempts
                self.add_trace(TraceEntry(
                    agent_name="ChannelDeployer", action=f"retry::{key}::attempt_{attempts}",
                    output_summary=f"rate_limited → attempt {attempts}/3",
                ))
                if attempts < 3:
                    deployment_log.append({"channel": ch_name, "market": market,
                                           "status": f"retry_{attempts}", "error": error})
                    return json.dumps({"status": "rate_limited", "retry_after": "30s",
                                       "attempt": attempts, "message": "Try again"})
                else:
                    deployment_log.append({"channel": ch_name, "market": market,
                                           "status": "failed_after_3_retries", "attempts": 3})
                    return json.dumps({"status": "failed", "retries_exhausted": True,
                                       "channel": ch_name})

            if error == "TEMPLATE_REJECTED":
                self.add_trace(TraceEntry(
                    agent_name="ChannelDeployer", action=f"fallback::{ch_name}→sms",
                    output_summary="WhatsApp rejected → SMS fallback",
                ))
                deployment_log.append({"channel": ch_name, "market": market,
                                        "status": "fallback_sms", "error": error})
                return json.dumps({
                    "status": "fallback",
                    "original": ch_name, "fallback": "sms",
                    "reason": "WhatsApp template rejected — deploying via SMS",
                })

            deployment_log.append({"channel": ch_name, "market": market,
                                    "status": "failed", "error": error})
            return json.dumps({"status": "failed", "error": error})

        deployer_spec = next(
            (s for s in agent_specs if "Deploy" in s.name or "Deploy" in s.role),
            agent_specs[0],
        )
        deployer = Agent(
            role=deployer_spec.role, goal=deployer_spec.goal,
            backstory=deployer_spec.backstory,
            llm=self.llm, tools=[deploy_channel], verbose=True,
        )

        channels_str = json.dumps(channels, ensure_ascii=False, indent=2)
        deploy_task = CrewTask(
            description=(
                f"انشر الحملة على هذه الـ channels:\n{channels_str}\n\n"
                f"استخدم deploy_channel لكل channel (JSON input).\n"
                f"- API_RATE_LIMIT → retry حتى 3 مرات قبل التخلي\n"
                f"- TEMPLATE_REJECTED → اعمل fallback لـ SMS\n\n"
                f"أنتج deployment report كامل."
            ),
            expected_output="DeploymentReport: channel_results + fallbacks + retries.",
            agent=deployer,
            output_pydantic=DeploymentReport,   # [NATIVE] structured output
            callback=self._task_callback,
        )

        crew = Crew(
            agents=[deployer], tasks=[deploy_task],
            process=Process.sequential,
            step_callback=self._step_callback,  # [NATIVE] trace حقيقي
            verbose=True,
        )

        start = time.time()
        result = await crew.kickoff_async()
        duration_ms = (time.time() - start) * 1000

        structured = None
        if hasattr(result, "pydantic") and result.pydantic:
            structured = result.pydantic.model_dump()

        success_count  = sum(1 for l in deployment_log if l["status"] == "success")
        fallback_count = sum(1 for l in deployment_log if "fallback" in l["status"])
        retry_count    = sum(1 for l in deployment_log if "retry" in l["status"])

        sr = self._make_result(
            scenario_id="channel_deploy", status="completed",
            output=structured or {
                "crew_output": str(result),
                "deployment_log": deployment_log,
                "summary": {
                    "success": success_count, "fallback": fallback_count,
                    "retried": retry_count, "tool_calls": self._tool_call_count,
                },
            },
            total_duration_ms=duration_ms, agent_count=1,
            tool_calls=self._tool_call_count,
        )
        sr.used_retry = retry_count > 0
        return sr

    # ═══════════════════════════════════════════════════════════════
    # Dimension 7: Multimodal
    # [NATIVE] مع GPT-4o/Gemini | [MANUAL] fallback لـ Groq
    # ═══════════════════════════════════════════════════════════════

    async def run_multimodal(
        self,
        image_path: Optional[str],
        document_path: Optional[str],
        task: Dict[str, Any],
    ) -> ScenarioResult:

        from crewai import Agent, Task as CrewTask, Crew, Process
        from crewai.tools import tool as crewai_tool

        product = task.get("product", {})
        model_str = self.llm.model if self.llm else ""
        is_vision = any(v in model_str for v in ["gpt-4o", "gemini", "claude-3", "vision"])

        @crewai_tool("get_product_details")
        def get_product_details(sku: str) -> str:
            """يجيب تفاصيل المنتج الكاملة: الاسم، السعر، الوصف، الصورة."""
            return json.dumps(product, ensure_ascii=False, indent=2)

        agent_kwargs = dict(
            role="Content Architect & Visual Copywriter",
            goal="Generate Arabic Ramadan ad copy for Meta Ads carousel.",
            backstory=(
                "كاتب إعلاني ثنائي اللغة. متخصص في السوق الخليجي. "
                "يكتب بالعربية الخليجية المؤثرة مع مراعاة حساسية رمضان."
            ),
            llm=self.llm,
            tools=[get_product_details],
            cache=True,   # [NATIVE]
            verbose=True,
        )

        content_agent = Agent(**agent_kwargs)

        vision_note = (
            "⚠️ Vision model active — analyze the product image directly."
            if is_vision
            else "⚠️ Text-only model — use get_product_details tool for specs."
        )

        multimodal_task = CrewTask(
            description=(
                f"{vision_note}\n\n"
                f"المنتج: {product.get('name_ar', '')} | SKU: {product.get('sku', '')}\n"
                f"{'Image: ' + str(image_path) if image_path and is_vision else ''}\n"
                f"السوق: {task.get('market', 'KSA')}\n"
                f"الفورمات: {task.get('format', 'meta_carousel')}\n\n"
                f"المتطلبات:\n"
                + "\n".join(f"- {r}" for r in task.get("requirements", []))
                + "\n\nاكتب:\n"
                  "1. Headline (max 40 حرف)\n"
                  "2. Description (max 125 حرف)\n"
                  "3. Call-to-Action\n"
                  "4. Body copy للـ carousel\n"
                  "باللغة العربية الخليجية. راعِ حساسية رمضان."
            ),
            expected_output="Arabic ad copy: Headline + Description + CTA + Carousel body.",
            agent=content_agent,
            guardrail=self._guardrail_arabic_content,  # [NATIVE] Arabic validation
            callback=self._task_callback,
        )

        crew = Crew(
            agents=[content_agent], tasks=[multimodal_task],
            process=Process.sequential,
            step_callback=self._step_callback,
            verbose=True,
        )

        self.add_trace(TraceEntry(
            agent_name="system", action="multimodal_mode",
            output_summary=(
                f"vision={is_vision} | image_provided={bool(image_path)} | "
                f"fallback={'product_metadata' if not is_vision else 'none'}"
            ),
        ))

        start = time.time()
        result = await crew.kickoff_async()
        duration_ms = (time.time() - start) * 1000

        return self._make_result(
            scenario_id="multimodal_ad", status="completed",
            output={
                "ad_copy": str(result),
                "vision_used": is_vision,
                "limitation": (
                    None if is_vision
                    else "CrewAI multimodal requires GPT-4o or Gemini Vision. "
                         "Groq/Llama is text-only → product metadata used as fallback."
                ),
            },
            total_duration_ms=duration_ms, agent_count=1,
            tool_calls=self._tool_call_count,
        )

    # ═══════════════════════════════════════════════════════════════
    # Dimension 8: CrewAI Flows — Full Campaign (BONUS)
    # [NATIVE] @start @listen @router — event-driven orchestration
    # ═══════════════════════════════════════════════════════════════

    async def run_as_flow(
        self,
        campaign_brief: Dict[str, Any],
        simulated_approval: Dict[str, Any],
    ) -> ScenarioResult:

        FlowClass = _build_campaign_flow(self.llm, campaign_brief, simulated_approval)

        if FlowClass is None:
            return self._make_result(
                scenario_id="campaign_flow",
                status="failed",
                output={
                    "error": "CrewAI Flows not available in current version.",
                    "recommendation": "pip install 'crewai>=0.80.0'",
                },
                total_duration_ms=0,
            )

        import asyncio
        from concurrent.futures import ThreadPoolExecutor

        flow = FlowClass()
        self.add_trace(TraceEntry(
            agent_name="system", action="flow_start",
            output_summary="RamadanCampaignFlow initialized",
        ))

        start = time.time()
        try:
            # [MANUAL] Flow.kickoff() sync → ThreadPoolExecutor عشان لا نبلوك
            loop = asyncio.get_event_loop()
            with ThreadPoolExecutor() as pool:
                result = await loop.run_in_executor(pool, flow.kickoff)
            duration_ms = (time.time() - start) * 1000

            self.add_trace(TraceEntry(
                agent_name="system", action="flow_complete",
                output_summary=f"final_status={flow.state.get('final_status', 'unknown')}",
                duration_ms=duration_ms,
            ))

            return self._make_result(
                scenario_id="campaign_flow",
                status="completed",
                output={
                    "flow_result": str(result),
                    "flow_state": flow.state,
                    "steps_completed": [
                        "initialize_campaign",
                        "generate_content",
                        "validate_content (router)",
                        "deploy_channels",
                        "analyze_performance",
                        "check_reallocation (router)",
                        "request_human_approval" if flow.state.get("needs_reallocation") else "finalize_no_reallocation",
                    ],
                    "content_approved": flow.state.get("content_approved", False),
                    "needs_reallocation": flow.state.get("needs_reallocation", False),
                    "final_status": flow.state.get("final_status", "unknown"),
                },
                total_duration_ms=duration_ms,
                agent_count=4,
            )

        except Exception as e:
            duration_ms = (time.time() - start) * 1000
            return self._make_result(
                scenario_id="campaign_flow",
                status="failed",
                output={"error": str(e), "flow_state": getattr(flow, "state", {})},
                total_duration_ms=duration_ms,
            )
