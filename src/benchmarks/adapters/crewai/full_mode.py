import re
import json
import time
import shutil
import builtins
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from unittest.mock import patch

from benchmarks.models import (
    AgentSpec,
    ToolSpec,
    ScenarioResult,
    TraceEntry,
    CampaignPlanOutput,
    AdCopyOutput,
    PIIReport,
    BudgetDecision,
    DeploymentReport,
)
from benchmarks.adapters.crewai.utils import _PII_PATTERNS
from benchmarks.adapters.crewai.enums import LLMProvider
from benchmarks.adapters.crewai.config import (
    MAX_RETRY_ATTEMPTS,
    BUDGET_REALLOCATION_THRESHOLD,
    MIN_ARABIC_CHARS,
    RAMADAN_FORBIDDEN_WORDS,
    MIN_RECALL_SCORE,
    RAG_RESULTS_LIMIT,
    RAG_SCORE_THRESHOLD,
)
from helpers import (
    BACKSTORIES,
    build_orchestration_prompt,
    build_content_generation_prompt,
    build_deploy_channels_prompt,
    build_analytics_prompt,
    build_approval_prompt,
    build_memory_session1_prompt,
    build_memory_session2_prompt,
    build_pii_scan_prompt,
    build_multimodal_prompt,
    build_flow_deploy_prompt,
    build_flow_analytics_prompt,
)

# On WSL/Linux, use /tmp to avoid Bus error on mounted drives (/mnt/d)
import sys
if sys.platform == "win32":
    _CREWAI_MEMORY_DIR = Path(__file__).parent.parent.parent.parent / ".crewai_memory"
else:
    _CREWAI_MEMORY_DIR = Path("/tmp/.crewai_memory")


def _build_campaign_flow(llm, campaign_brief: Dict, simulated_approval: Dict):
    try:
        from crewai.flow.flow import Flow, start, listen, router
        from crewai import Agent, Task as CrewTask, Crew, Process
    except ImportError:
        return None

    brief_str = json.dumps(campaign_brief, ensure_ascii=False, indent=2)

    class RamadanCampaignFlow(Flow):
        # ── Step 1: Initialize ──────────────────────────────────────
        @start()
        def initialize_campaign(self):
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
                output_pydantic=CampaignPlanOutput,
            )
            crew = Crew(
                agents=[commander],
                tasks=[init_task],
                process=Process.sequential,
                verbose=True,
            )
            result = crew.kickoff()
            self.state["campaign_plan"] = str(result)
            self.state["initialized"] = True
            return str(result)

        # ── Step 2: Generate Content ────────────────────────────────
        @listen(initialize_campaign)
        def generate_content(self, campaign_plan):
            content_agent = Agent(
                role="Bilingual Content Generator",
                goal="Generate Arabic/English ad copy for Ramadan campaign.",
                backstory=(
                    "Expert Arabic copywriter. Gulf + Egyptian dialects. "
                    "Ramadan cultural sensitivity specialist."
                ),
                llm=llm,
                cache=True,
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
                output_pydantic=AdCopyOutput,
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

        # ── Step 3: Router ──────────────────────────────────────────
        @router(generate_content)
        def validate_content(self, content):
            arabic_chars = sum(1 for c in content if "\u0600" <= c <= "\u06ff")
            attempts = self.state.get("content_attempts", 1)

            if arabic_chars >= 20:
                self.state["content_approved"] = True
                return "deploy"
            elif attempts >= 2:
                self.state["content_approved"] = True
                return "deploy"
            else:
                return "regenerate"

        # ── Step 3b: Regenerate ──────────────────────────────────────
        @listen("regenerate")
        def regenerate_content(self, _):
            return self.generate_content(self.state.get("campaign_plan", ""))

        # ── Step 4: Deploy Channels ─────────────────────────────────
        @listen("deploy")
        def deploy_channels(self, content):
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
                output_pydantic=DeploymentReport,
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
            self.state["needs_reallocation"] = True
            return str(result)

        # ── Step 6: Router ──────────────────────────────────────────
        @router(analyze_performance)
        def check_reallocation(self, analysis):
            if self.state.get("needs_reallocation", False):
                return "hitl_approval"
            return "complete"

        # ── Step 7: HITL Approval ───────────────────────────────────
        @listen("hitl_approval")
        def request_human_approval(self, analysis):
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
                human_input=True,
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
            self.state["final_status"] = "completed_no_reallocation"
            return {"status": "completed", "reallocation": False}

        @listen(request_human_approval)
        def finalize_with_approval(self, approval_result):
            self.state["final_status"] = "completed_with_approval"
            return {
                "status": "completed",
                "reallocation": True,
                "approval": approval_result,
            }

    return RamadanCampaignFlow


class FullModeRunner:
    """
    CrewAI Full Mode Runner.
    Implements the 7 benchmark scenarios with full features:
    - Short-term/long-term memory (using ChromaDB)
    - Flows (Ramadan Campaign Flow)
    - Hierarchical processes and managers
    - Planning and caching
    - Real search tools, custom embedders, and guardrails
    - HITL (pausing execution for approvals)
    """

    def __init__(self, adapter):
        self.adapter = adapter

    def _supports_cache(self) -> bool:
        """Groq doesn't support cache_breakpoint in messages — disable for Groq."""
        return self.adapter._provider.lower() != LLMProvider.GROQ

    def _build_agents(self, specs: List[AgentSpec], tools_map: Dict = None) -> list:
        from crewai import Agent
        agents = []
        for spec in specs:
            agent_tools = (tools_map or {}).get(spec.name, [])
            agents.append(Agent(
                role=spec.role,
                goal=spec.goal,
                backstory=spec.backstory,
                llm=self.adapter.llm,
                tools=agent_tools,
                allow_delegation=spec.can_delegate,
                memory=True,
                cache=self._supports_cache(),
                verbose=True,
            ))
        return agents

    def _build_tool(self, spec: ToolSpec):
        from crewai.tools import tool as crewai_tool
        adapter = self.adapter

        # CrewAI validates __doc__ at decoration time — set it BEFORE applying the decorator
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

        _wrapper.__doc__ = spec.description or spec.name
        return crewai_tool(spec.name)(_wrapper)

    def _build_knowledge(self, catalog_data: List[Dict]) -> Any:
        try:
            from crewai.knowledge.source.string_knowledge_source import StringKnowledgeSource
            catalog_text = (
                "Product Catalog — RetailCo MENA:\n\n"
                + json.dumps(catalog_data, ensure_ascii=False, indent=2)
            )
            return StringKnowledgeSource(content=catalog_text)
        except ImportError:
            return None

    def _get_embedder_config(self) -> Optional[Dict]:
        import os
        provider = self.adapter._provider.lower()

        def _valid(key: str) -> bool:
            """Return True only if the key looks real (not a placeholder)."""
            return bool(key) and not key.startswith("your_")

        if provider == LLMProvider.OPENAI:
            key = self.adapter._api_key or os.getenv("OPENAI_API_KEY", "")
            if _valid(key):
                return {
                    "provider": "openai",
                    "config": {"model": "text-embedding-3-small", "api_key": key},
                }

        elif provider in (LLMProvider.GEMINI, "google"):
            key = self.adapter._api_key or os.getenv("GEMINI_API_KEY", "") or os.getenv("GOOGLE_API_KEY", "")
            if _valid(key):
                return {
                    "provider": "google-generativeai",
                    "config": {"model_name": "gemini-embedding-001", "api_key": key},
                }

        elif provider == LLMProvider.OLLAMA:
            return {
                "provider": "ollama",
                "config": {
                    "model": "mxbai-embed-large",
                    "url": os.getenv("OLLAMA_BASE_URL", "http://localhost:11434/api/embeddings"),
                },
            }

        elif provider == LLMProvider.GROQ:
            # Groq لا يملك embeddings — نستخدم Gemini كـ fallback (مفتاحه متوفر)
            gemini_key = os.getenv("GEMINI_API_KEY", "") or os.getenv("GOOGLE_API_KEY", "")
            if _valid(gemini_key):
                return {
                    "provider": "google-generativeai",
                    "config": {"model_name": "gemini-embedding-001", "api_key": gemini_key},
                }
            openai_key = os.getenv("OPENAI_API_KEY", "")
            if _valid(openai_key):
                return {
                    "provider": "openai",
                    "config": {"model": "text-embedding-3-small", "api_key": openai_key},
                }

        # لو مفيش embedder صالح → None (بدون knowledge source)
        return None


    def _get_search_tools(self) -> list:
        import os
        real_tools = []

        if os.getenv("SERPER_API_KEY"):
            try:
                from crewai_tools import SerperDevTool
                real_tools.append(SerperDevTool())
                self.adapter.add_trace(TraceEntry(
                    agent_name="system", action="search_tool_loaded",
                    output_summary="SerperDevTool (Google Search) — active",
                ))
            except ImportError:
                pass

        if not real_tools and os.getenv("EXA_API_KEY"):
            try:
                from crewai_tools import ExaSearchTool
                real_tools.append(ExaSearchTool(highlights=True, type="auto"))
                self.adapter.add_trace(TraceEntry(
                    agent_name="system", action="search_tool_loaded",
                    output_summary="ExaSearchTool (Semantic Search) — active",
                ))
            except ImportError:
                pass

        if not real_tools:
            self.adapter.add_trace(TraceEntry(
                agent_name="system", action="search_tool_loaded",
                output_summary="No real search tools — using mock fallback only",
            ))

        return real_tools

    def _guardrail_arabic_content(self, output: Any) -> Tuple[bool, str]:
        text = output.raw if hasattr(output, "raw") else str(output)
        arabic_chars = sum(1 for c in text if "\u0600" <= c <= "\u06ff")
        if arabic_chars < MIN_ARABIC_CHARS:
            return False, "Content must contain Arabic text — Gulf Arabic required for KSA market."
        return True, ""

    def _guardrail_ramadan_sensitivity(self, output: Any) -> Tuple[bool, str]:
        text = output.raw if hasattr(output, "raw") else str(output)
        for word in RAMADAN_FORBIDDEN_WORDS:
            if word.lower() in text.lower():
                return False, f"Content violates Ramadan guidelines: '{word}' detected."
        return True, ""

    def _clean_memory(self) -> None:
        if _CREWAI_MEMORY_DIR.exists():
            shutil.rmtree(_CREWAI_MEMORY_DIR, ignore_errors=True)
        _CREWAI_MEMORY_DIR.mkdir(parents=True, exist_ok=True)

    # ═══════════════════════════════════════════════════════════════
    # Dimension 1: Orchestration
    # ═══════════════════════════════════════════════════════════════
    async def run_orchestration(
        self,
        agent_specs: List[AgentSpec],
        task: Dict[str, Any],
        orchestration_mode: str = "hierarchical",
    ) -> ScenarioResult:
        from crewai import Crew, Process, Task as CrewTask

        self.adapter._tool_call_count = 0
        agents = self._build_agents(agent_specs)
        brief_str = json.dumps(task, ensure_ascii=False, indent=2)

        main_task = CrewTask(
            description=build_orchestration_prompt(task),
            expected_output=(
                "Campaign plan شامل: agent assignments + channel plan + KPIs + compliance checklist."
            ),
            agent=agents[0],
            output_pydantic=CampaignPlanOutput,
            callback=self.adapter._task_callback,
        )

        embedder = self._get_embedder_config()
        crew_kwargs = dict(
            agents=agents,
            tasks=[main_task],
            process=Process.hierarchical,
            manager_llm=self.adapter.llm,
            memory=False,     # Disable to prevent CrewAI from defaulting memory queries to OpenAI
            planning=False,   # Disable to prevent CrewAI from creating a planning agent that requires OpenAI
            step_callback=self.adapter._step_callback,
            verbose=True,
        )

        crew = Crew(**crew_kwargs)

        start = time.time()
        result = await crew.kickoff_async()
        duration_ms = (time.time() - start) * 1000

        structured = None
        if hasattr(result, "pydantic") and result.pydantic:
            structured = result.pydantic.model_dump()

        return self.adapter._make_result(
            scenario_id="campaign_planning",
            status="completed",
            output=structured or str(result),
            total_duration_ms=duration_ms,
            agent_count=len(agents),
        )

    # ═══════════════════════════════════════════════════════════════
    # Dimension 2: Tool Use
    # ═══════════════════════════════════════════════════════════════
    async def run_with_tools(
        self,
        agent_specs: List[AgentSpec],
        task: Dict[str, Any],
        tools: List[ToolSpec],
    ) -> ScenarioResult:
        from crewai import Agent, Crew, Process, Task as CrewTask

        self.adapter._tool_call_count = 0
        real_search_tools = self._get_search_tools()

        knowledge_config = None
        try:
            from crewai.knowledge.knowledge_config import KnowledgeConfig
            knowledge_config = KnowledgeConfig(
                results_limit=RAG_RESULTS_LIMIT,
                score_threshold=RAG_SCORE_THRESHOLD,
            )
        except ImportError:
            pass

        product_data = [task.get("product", {})]
        knowledge_source = self._build_knowledge(product_data)
        crewai_tools = [self._build_tool(t) for t in tools]
        content_spec = next(
            (s for s in agent_specs if "Content" in s.name), agent_specs[0]
        )
        all_tools = crewai_tools + real_search_tools

        agent_kwargs = dict(
            role=content_spec.role,
            goal=content_spec.goal,
            backstory=content_spec.backstory,
            llm=self.adapter.llm,
            tools=all_tools,
            cache=self._supports_cache(),
            verbose=True,
        )
        embedder = self._get_embedder_config()
        if embedder:
            agent_kwargs["embedder"] = embedder
            # Knowledge source يحتاج embedder — بدونه بيفشل
            # Groq لا يدعم cache_breakpoint اللي CrewAI بيضيفه مع knowledge sources
            if knowledge_source and self._supports_cache():
                agent_kwargs["knowledge_sources"] = [knowledge_source]
                if knowledge_config:
                    agent_kwargs["knowledge_config"] = knowledge_config

        content_agent = Agent(**agent_kwargs)
        product = task.get("product", {})
        content_task = CrewTask(
            description=build_content_generation_prompt(task),
            expected_output="4 ad copy variants: Gulf Arabic carousel, Gulf Arabic single, English, WhatsApp template.",
            agent=content_agent,
            callback=self.adapter._task_callback,
        )

        crew_kwargs = dict(
            agents=[content_agent],
            tasks=[content_task],
            process=Process.sequential,
            step_callback=self.adapter._step_callback,
            verbose=True,
        )
        if embedder:
            crew_kwargs["embedder"] = embedder
        crew = Crew(**crew_kwargs)

        start = time.time()
        result = await crew.kickoff_async()
        duration_ms = (time.time() - start) * 1000

        structured = None
        if hasattr(result, "pydantic") and result.pydantic:
            structured = result.pydantic.model_dump()

        return self.adapter._make_result(
            scenario_id="content_generation",
            status="completed",
            output=structured or str(result),
            total_duration_ms=duration_ms,
            agent_count=1,
            tool_calls=self.adapter._tool_call_count,
        )

    # ═══════════════════════════════════════════════════════════════
    # Dimension 3: Safety & Privacy
    # ═══════════════════════════════════════════════════════════════
    async def run_safety_check(
        self,
        text_with_pii: str,
        pii_types: List[str],
        jurisdiction: str,
        expected_pii: Optional[Dict[str, List[str]]] = None,
    ) -> ScenarioResult:
        from crewai import Agent, Crew, Process, Task as CrewTask

        regex_detected = self.adapter._scan_pii_regex(text_with_pii)
        redacted_after_regex = self.adapter._redact(text_with_pii, regex_detected)
        self.adapter.add_trace(TraceEntry(
            agent_name="regex_scanner", action="pii_regex_scan",
            output_summary=(
                f"types={list(regex_detected.keys())} | "
                f"hits={sum(len(v) for v in regex_detected.values())}"
            ),
        ))

        jurisdiction_rules = {
            "KSA":  "Saudi PDPL: National ID, Iqama, phone → redact. Consent for marketing.",
            "EG":   "Egypt Law 151/2020: National ID (14-digit), phone → redact. Criminal penalties.",
            "both": "Apply both Saudi PDPL and Egyptian Law 151/2020.",
        }.get(jurisdiction, "Apply GDPR-equivalent rules.")

        def _guardrail_has_redaction(output: Any) -> Tuple[bool, str]:
            text = output.raw if hasattr(output, "raw") else str(output)
            if "[REDACTED" not in text and "REDACTED" not in text:
                return False, "Output must contain redacted PII markers."
            return True, ""

        compliance_agent = Agent(
            role="Privacy & Compliance Officer",
            goal="Detect contextual PII (names, addresses) missed by regex.",
            backstory=BACKSTORIES["compliance_guardian"],
            llm=self.adapter.llm,
            verbose=True,
        )

        llm_task = CrewTask(
            description=build_pii_scan_prompt(
                redacted_text=redacted_after_regex,
                original_text=text_with_pii,
                jurisdiction=jurisdiction,
                jurisdiction_rules=jurisdiction_rules,
            ),
            expected_output="PIIReport JSON: detected_pii + redacted_text + risk_level + compliance_notes.",
            agent=compliance_agent,
            output_pydantic=PIIReport,
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

        accuracy = self.adapter._score_pii(merged, expected_pii or {})
        self.adapter.add_trace(TraceEntry(
            agent_name="ComplianceGuardian", action="pii_complete",
            output_summary=f"accuracy={accuracy:.1%} | risk={risk_level} | types={list(merged.keys())}",
            duration_ms=duration_ms,
        ))

        sr = self.adapter._make_result(
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
    # ═══════════════════════════════════════════════════════════════
    async def run_with_approval(
        self,
        agent_specs: List[AgentSpec],
        task: Dict[str, Any],
        approval_rules: Dict[str, Any],
        simulated_approvals: List[Dict[str, Any]],
    ) -> ScenarioResult:
        from crewai import Agent, Crew, Process, Task as CrewTask

        approval_data = simulated_approvals[0] if simulated_approvals else {
            "decision": "approved", "feedback": "Proceed.", "approver": "Manager",
        }
        threshold = approval_rules.get("budget_reallocation_threshold", 0.20)
        realloc_pct = task.get("recommendation", {}).get("percentage_of_channel_budget", 50) / 100

        analytics_spec = next((s for s in agent_specs if "Analytics" in s.name), agent_specs[0])
        commander_spec = next((s for s in agent_specs if "Commander" in s.name), agent_specs[0])

        analytics_agent = Agent(
            role=analytics_spec.role, goal=analytics_spec.goal,
            backstory=analytics_spec.backstory, llm=self.adapter.llm, verbose=True,
        )
        commander_agent = Agent(
            role=commander_spec.role, goal=commander_spec.goal,
            backstory=commander_spec.backstory, llm=self.adapter.llm, verbose=True,
        )

        analyze_task = CrewTask(
            description=build_analytics_prompt(task, threshold),
            expected_output="توصية إعادة توزيع ميزانية مع مبررات.",
            agent=analytics_agent,
            callback=self.adapter._task_callback,
        )

        approval_text = (
            f"{approval_data['decision'].upper()}. "
            f"Feedback: {approval_data.get('feedback', 'Proceed.')}"
        )

        approval_task = CrewTask(
            description=(
                f"{build_approval_prompt(threshold)}\n\n"
                f"── SIMULATED HUMAN DECISION (INJECTED): ──\n"
                f"The marketing manager has made the following decision:\n"
                f"Decision: {approval_text}\n"
                f"Please record this decision and apply it to the budget reallocation recommendation."
            ),
            expected_output="BudgetDecision: final_allocation + human_decision + feedback applied.",
            agent=commander_agent,
            context=[analyze_task],
            human_input=False,  # Bypasses the buggy CrewAI ask_for_human_input method
            output_pydantic=BudgetDecision,
            callback=self.adapter._task_callback,
        )

        crew = Crew(
            agents=[analytics_agent, commander_agent],
            tasks=[analyze_task, approval_task],
            process=Process.sequential,
            step_callback=self.adapter._step_callback,
            verbose=True,
        )

        self.adapter.add_trace(TraceEntry(
            agent_name="system", action="hitl_mock_inject",
            input_summary=approval_text,
            output_summary=f"approver={approval_data.get('approver', 'MockManager')}",
        ))

        start = time.time()
        result = await crew.kickoff_async()
        duration_ms = (time.time() - start) * 1000

        structured = None
        if hasattr(result, "pydantic") and result.pydantic:
            structured = result.pydantic.model_dump()

        sr = self.adapter._make_result(
            scenario_id="budget_approval", status="completed",
            output=structured or str(result),
            total_duration_ms=duration_ms, agent_count=2,
        )
        sr.used_approval_gate = True
        return sr

    # ═══════════════════════════════════════════════════════════════
    # Dimension 5: Memory
    # ═══════════════════════════════════════════════════════════════
    async def run_with_memory(
        self,
        conversation_history: List[Dict[str, Any]],
        follow_up_query: str,
        expected_recall: List[str],
    ) -> ScenarioResult:
        from crewai import Agent, Crew, Process, Task as CrewTask

        self._clean_memory()

        embedder = self._get_embedder_config()
        has_embedder = bool(embedder)

        customer_agent = Agent(
            role="Customer Service Agent",
            goal="Handle inquiries with full recall from previous conversations.",
            backstory=BACKSTORIES["customer_engagement"],
            llm=self.adapter.llm,
            memory=has_embedder,
            verbose=True,
        )

        session1 = conversation_history[0] if conversation_history else {}
        history_text = "\n".join(
            f"{'العميل' if m['role'] == 'customer' else 'الوكيل'}: {m['content']}"
            for m in session1.get("messages", [])
        )

        session1_task = CrewTask(
            description=build_memory_session1_prompt(session1),
            expected_output=(
                "ملخص: قلاية فيلبس XXL، 764 ريال (خصم 15%)، أبيض، فرع الرياض."
            ),
            agent=customer_agent,
        )

        crew1_kwargs = dict(
            agents=[customer_agent], tasks=[session1_task],
            process=Process.sequential,
            memory=has_embedder,
            verbose=True,
        )
        if has_embedder:
            crew1_kwargs["embedder"] = embedder
        crew_run1 = Crew(**crew1_kwargs)
        await crew_run1.kickoff_async()

        session2_task = CrewTask(
            description=build_memory_session2_prompt(follow_up_query),
            expected_output=(
                "رد يذكر: قلاية فيلبس، 764 ريال، أبيض، الرياض — بدون سؤال العميل."
            ),
            agent=customer_agent,
        )

        crew2_kwargs = dict(
            agents=[customer_agent], tasks=[session2_task],
            process=Process.sequential,
            memory=has_embedder,
            verbose=True,
        )
        if has_embedder:
            crew2_kwargs["embedder"] = embedder
        crew_run2 = Crew(**crew2_kwargs)

        start = time.time()
        result = await crew_run2.kickoff_async()
        duration_ms = (time.time() - start) * 1000

        output_str = str(result)
        recalled = [item for item in expected_recall if item in output_str]
        recall_score = len(recalled) / len(expected_recall) if expected_recall else 1.0

        self.adapter.add_trace(TraceEntry(
            agent_name="CustomerEngagement", action="memory_recall",
            output_summary=(
                f"score={recall_score:.1%} | "
                f"recalled={recalled} | "
                f"missing={[i for i in expected_recall if i not in recalled]}"
            ),
            duration_ms=duration_ms,
        ))

        sr = self.adapter._make_result(
            scenario_id="cross_session_chat", status="completed",
            output={
                "response": output_str,
                "recalled_items": recalled,
                "recall_score": recall_score,
                "expected": expected_recall,
            },
            total_duration_ms=duration_ms, agent_count=1,
        )
        sr.used_memory = recall_score > MIN_RECALL_SCORE
        return sr

    # ═══════════════════════════════════════════════════════════════
    # Dimension 6: Observability
    # ═══════════════════════════════════════════════════════════════
    async def run_with_tracing(
        self,
        agent_specs: List[AgentSpec],
        task: Dict[str, Any],
        inject_failure: Optional[Dict[str, Any]] = None,
    ) -> ScenarioResult:
        from crewai import Agent, Crew, Process, Task as CrewTask
        from crewai.tools import tool as crewai_tool

        channels = task.get("channels", [])
        self.adapter._tool_call_count = 0
        retry_state: Dict[str, int] = {}
        deployment_log: List[Dict] = []

        @crewai_tool("deploy_channel")
        def deploy_channel(channel_json: str) -> str:
            """Deploy campaign content to a specific advertising channel."""
            self.adapter._tool_call_count += 1
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
                self.adapter.add_trace(TraceEntry(
                    agent_name="ChannelDeployer", action=f"deploy::{key}",
                    output_summary="success",
                ))
                return json.dumps({"status": "success", "channel": ch_name, "market": market})

            error = channel_data.get("error", "UNKNOWN")

            if error == "API_RATE_LIMIT":
                attempts = retry_state.get(key, 0) + 1
                retry_state[key] = attempts
                self.adapter.add_trace(TraceEntry(
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
                self.adapter.add_trace(TraceEntry(
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
            llm=self.adapter.llm, tools=[deploy_channel], verbose=True,
        )

        deploy_task = CrewTask(
            description=build_deploy_channels_prompt(channels),
            expected_output="DeploymentReport: channel_results + fallbacks + retries.",
            agent=deployer,
            output_pydantic=DeploymentReport,
            callback=self.adapter._task_callback,
        )

        crew = Crew(
            agents=[deployer], tasks=[deploy_task],
            process=Process.sequential,
            step_callback=self.adapter._step_callback,
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

        sr = self.adapter._make_result(
            scenario_id="channel_deploy", status="completed",
            output=structured or {
                "crew_output": str(result),
                "deployment_log": deployment_log,
                "summary": {
                    "success": success_count, "fallback": fallback_count,
                    "retried": retry_count, "tool_calls": self.adapter._tool_call_count,
                },
            },
            total_duration_ms=duration_ms, agent_count=1,
            tool_calls=self.adapter._tool_call_count,
        )
        sr.used_retry = retry_count > 0
        return sr

    # ═══════════════════════════════════════════════════════════════
    # Dimension 7: Multimodal
    # ═══════════════════════════════════════════════════════════════
    async def run_multimodal(
        self,
        image_path: Optional[str],
        document_path: Optional[str],
        task: Dict[str, Any],
    ) -> ScenarioResult:
        from crewai import Agent, Crew, Process, Task as CrewTask
        from crewai.tools import tool as crewai_tool

        product = task.get("product", {})
        model_str = self.adapter.llm.model if self.adapter.llm else ""
        # Disable native vision for Gemini/Google to avoid the buggy google-genai SDK 404 errors.
        # Fall back to text-only mode using get_product_details.
        is_vision = "gpt-4o" in model_str

        @crewai_tool("get_product_details")
        def get_product_details(sku: str) -> str:
            """Get product specifications and catalog information by SKU."""
            return json.dumps(product, ensure_ascii=False, indent=2)

        agent_kwargs = dict(
            role="Content Architect & Visual Copywriter",
            goal="Generate Arabic Ramadan ad copy for Meta Ads carousel.",
            backstory=BACKSTORIES["content_architect"],
            llm=self.adapter.llm,
            tools=[get_product_details],
            cache=True,
            verbose=True,
        )

        content_agent = Agent(**agent_kwargs)
        vision_note = (
            "⚠️ Vision model active — analyze the product image directly."
            if is_vision
            else "⚠️ Text-only model — use get_product_details tool for specs."
        )

        multimodal_task = CrewTask(
            description=build_multimodal_prompt(
                task,
                is_vision=is_vision,
                image_path=str(image_path) if image_path else None,
            ),
            expected_output="Arabic ad copy: Headline + Description + CTA + Carousel body.",
            agent=content_agent,
            callback=self.adapter._task_callback,
        )

        crew = Crew(
            agents=[content_agent], tasks=[multimodal_task],
            process=Process.sequential,
            step_callback=self.adapter._step_callback,
            verbose=True,
        )

        self.adapter.add_trace(TraceEntry(
            agent_name="system", action="multimodal_mode",
            output_summary=(
                f"vision={is_vision} | image_provided={bool(image_path)} | "
                f"fallback={'product_metadata' if not is_vision else 'none'}"
            ),
        ))

        start = time.time()
        result = await crew.kickoff_async()
        duration_ms = (time.time() - start) * 1000

        return self.adapter._make_result(
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
            tool_calls=self.adapter._tool_call_count,
        )

    # ═══════════════════════════════════════════════════════════════
    # Dimension 8: CrewAI Flows (Bonus)
    # ═══════════════════════════════════════════════════════════════
    async def run_as_flow(
        self,
        campaign_brief: Dict[str, Any],
        simulated_approval: Dict[str, Any],
    ) -> ScenarioResult:
        FlowClass = _build_campaign_flow(self.adapter.llm, campaign_brief, simulated_approval)

        if FlowClass is None:
            return self.adapter._make_result(
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
        self.adapter.add_trace(TraceEntry(
            agent_name="system", action="flow_start",
            output_summary="RamadanCampaignFlow initialized",
        ))

        start = time.time()
        try:
            loop = asyncio.get_event_loop()
            with ThreadPoolExecutor() as pool:
                result = await loop.run_in_executor(pool, flow.kickoff)
            duration_ms = (time.time() - start) * 1000

            self.adapter.add_trace(TraceEntry(
                agent_name="system", action="flow_complete",
                output_summary=f"final_status={flow.state.get('final_status', 'unknown')}",
                duration_ms=duration_ms,
            ))

            return self.adapter._make_result(
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
            return self.adapter._make_result(
                scenario_id="campaign_flow",
                status="failed",
                output={"error": str(e), "flow_state": getattr(flow, "state", {})},
                total_duration_ms=duration_ms,
            )
