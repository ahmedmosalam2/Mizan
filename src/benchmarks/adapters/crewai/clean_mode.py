import time
import json
from typing import Any, Dict, List, Optional, Tuple
from unittest.mock import patch
import builtins

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
from benchmarks.adapters.crewai.config import (
    MIN_ARABIC_CHARS,
    RAMADAN_FORBIDDEN_WORDS,
    MIN_RECALL_SCORE,
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
)


class CleanModeRunner:
    """
    CrewAI Clean Mode Runner.
    Implements the 7 benchmark scenarios with:
    - No Memory (memory=False)
    - No Flows (sequential execution only)
    - No HITL/Approval (automatic approval or no block)
    - Minimal Orchestration (no Process.hierarchical, planning=False, cache=False)
    """

    def __init__(self, adapter):
        self.adapter = adapter

    def _build_clean_agents(self, specs: List[AgentSpec], tools_map: Dict = None) -> list:
        """Build CrewAI agents with memory=False, cache=False, allow_delegation=False."""
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
                allow_delegation=False,  # Clean mode: no delegation
                memory=False,           # Clean mode: no memory
                cache=False,            # Clean mode: no cache
                verbose=True,
            ))
        return agents

    def _build_clean_tool(self, spec: ToolSpec):
        """Standard wrapper around tool spec."""
        from crewai.tools import tool as crewai_tool
        adapter = self.adapter

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

    # ═══════════════════════════════════════════════════════════════
    # Dimension 1: Orchestration
    # ═══════════════════════════════════════════════════════════════
    async def run_orchestration(
        self,
        agent_specs: List[AgentSpec],
        task: Dict[str, Any],
        orchestration_mode: str = "sequential",
    ) -> ScenarioResult:
        from crewai import Crew, Process, Task as CrewTask

        self.adapter._tool_call_count = 0
        # Clean Mode: Sequential only, no planning, memory=False
        agents = self._build_clean_agents(agent_specs)
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

        crew = Crew(
            agents=agents,
            tasks=[main_task],
            process=Process.sequential,  # Clean mode: always sequential
            memory=False,                # Clean mode: no memory
            planning=False,              # Clean mode: no planning
            step_callback=self.adapter._step_callback,
            verbose=True,
        )

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
        from crewai import Crew, Process, Task as CrewTask

        self.adapter._tool_call_count = 0
        # Clean mode: no knowledge config, no real search tools, just mock tools
        crewai_tools = [self._build_clean_tool(t) for t in tools]

        content_spec = next(
            (s for s in agent_specs if "Content" in s.name), agent_specs[0]
        )

        agents = self._build_clean_agents([content_spec], tools_map={content_spec.name: crewai_tools})
        content_agent = agents[0]

        content_task = CrewTask(
            description=build_content_generation_prompt(task),
            expected_output="4 ad copy variants structured per AdCopyOutput format.",
            agent=content_agent,
            output_pydantic=AdCopyOutput,
            # Clean mode: no guardrails (minimal orchestration)
            callback=self.adapter._task_callback,
        )

        crew = Crew(
            agents=[content_agent],
            tasks=[content_task],
            process=Process.sequential,
            memory=False,
            planning=False,
            step_callback=self.adapter._step_callback,
            verbose=True,
        )

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
        from crewai import Crew, Process, Task as CrewTask

        # Clean mode: Regex is run manually but no guardrails on LLM task.
        regex_detected = self.adapter._scan_pii_regex(text_with_pii)
        redacted_after_regex = self.adapter._redact(text_with_pii, regex_detected)

        jurisdiction_rules = {
            "KSA":  "Saudi PDPL: National ID, Iqama, phone → redact. Consent for marketing.",
            "EG":   "Egypt Law 151/2020: National ID (14-digit), phone → redact. Criminal penalties.",
            "both": "Apply both Saudi PDPL and Egyptian Law 151/2020.",
        }.get(jurisdiction, "Apply GDPR-equivalent rules.")

        agents = self._build_clean_agents([
            AgentSpec(
                name="Compliance Officer",
                role="Privacy & Compliance Officer",
                goal="Detect contextual PII (names, addresses) missed by regex.",
                backstory=BACKSTORIES["compliance_guardian"]
            )
        ])
        compliance_agent = agents[0]

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
            # Clean mode: no guardrail (no has_redaction check)
        )

        crew = Crew(
            agents=[compliance_agent],
            tasks=[llm_task],
            process=Process.sequential,
            memory=False,
            planning=False,
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
                import re
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
    # Dimension 4: Human-in-the-Loop (Auto-approve)
    # ═══════════════════════════════════════════════════════════════
    async def run_with_approval(
        self,
        agent_specs: List[AgentSpec],
        task: Dict[str, Any],
        approval_rules: Dict[str, Any],
        simulated_approvals: List[Dict[str, Any]],
    ) -> ScenarioResult:
        from crewai import Crew, Process, Task as CrewTask

        # Clean mode: no human approval blocking.
        # We auto-fill approval decision instead of using human_input=True.
        approval_data = simulated_approvals[0] if simulated_approvals else {
            "decision": "approved", "feedback": "Proceed.", "approver": "Manager",
        }
        threshold = approval_rules.get("budget_reallocation_threshold", 0.20)
        realloc_pct = task.get("recommendation", {}).get("percentage_of_channel_budget", 50) / 100

        analytics_spec = next((s for s in agent_specs if "Analytics" in s.name), agent_specs[0])
        commander_spec = next((s for s in agent_specs if "Commander" in s.name), agent_specs[0])

        agents = self._build_clean_agents([analytics_spec, commander_spec])
        analytics_agent = agents[0]
        commander_agent = agents[1]

        analyze_task = CrewTask(
            description=build_analytics_prompt(task, threshold),
            expected_output="توصية إعادة توزيع ميزانية مع مبررات.",
            agent=analytics_agent,
            callback=self.adapter._task_callback,
        )

        approval_task = CrewTask(
            description=build_approval_prompt(threshold),
            expected_output="BudgetDecision: final_allocation + human_decision + feedback applied.",
            agent=commander_agent,
            context=[analyze_task],
            human_input=False,                  # Clean mode: NO human_input
            output_pydantic=BudgetDecision,
            callback=self.adapter._task_callback,
        )

        crew = Crew(
            agents=[analytics_agent, commander_agent],
            tasks=[analyze_task, approval_task],
            process=Process.sequential,
            memory=False,
            planning=False,
            step_callback=self.adapter._step_callback,
            verbose=True,
        )

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
        sr.used_approval_gate = False  # Clean mode: skipped HITL gate
        return sr

    # ═══════════════════════════════════════════════════════════════
    # Dimension 5: Memory (Disabled)
    # ═══════════════════════════════════════════════════════════════
    async def run_with_memory(
        self,
        conversation_history: List[Dict[str, Any]],
        follow_up_query: str,
        expected_recall: List[str],
    ) -> ScenarioResult:
        from crewai import Crew, Process, Task as CrewTask

        # Clean mode: memory=False. We run Session 1 and Session 2.
        # Since memory is disabled, Session 2 will not be able to recall details from Session 1
        # unless it is in the prompt (which is NOT in Session 2's prompt).
        agents = self._build_clean_agents([
            AgentSpec(
                name="Customer Service Agent",
                role="Customer Service Agent",
                goal="Handle inquiries.",
                backstory="RetailCo representative."
            )
        ])
        customer_agent = agents[0]

        # Session 1 run
        session1 = conversation_history[0] if conversation_history else {}
        history_text = "\n".join(
            f"{'العميل' if m['role'] == 'customer' else 'الوكيل'}: {m['content']}"
            for m in session1.get("messages", [])
        )

        session1_task = CrewTask(
            description=(
                f"المحادثة مع العميل {session1.get('customer_id', 'CUST-101')}:\n\n"
                f"{history_text}\n\n"
                f"لخّص المحادثة واحفظ التفاصيل."
            ),
            expected_output="ملخص للمحادثة.",
            agent=customer_agent,
        )

        crew_run1 = Crew(
            agents=[customer_agent], tasks=[session1_task],
            process=Process.sequential,
            memory=False,  # Clean mode: no memory
            verbose=True,
        )
        await crew_run1.kickoff_async()

        # Session 2 run (without history in prompt)
        session2_task = CrewTask(
            description=build_memory_session2_prompt(follow_up_query),
            expected_output="رد على استفسار العميل.",
            agent=customer_agent,
        )

        crew_run2 = Crew(
            agents=[customer_agent], tasks=[session2_task],
            process=Process.sequential,
            memory=False,  # Clean mode: no memory
            verbose=True,
        )

        start = time.time()
        result = await crew_run2.kickoff_async()
        duration_ms = (time.time() - start) * 1000

        output_str = str(result)
        recalled = [item for item in expected_recall if item in output_str]
        recall_score = len(recalled) / len(expected_recall) if expected_recall else 1.0

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
        sr.used_memory = False  # Clean mode: memory disabled
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
        from crewai import Crew, Process, Task as CrewTask
        from crewai.tools import tool as crewai_tool

        channels = task.get("channels", [])
        self.adapter._tool_call_count = 0
        deployment_log = []

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
            
            # Clean mode: no complex retry or fallbacks. If it fails, it fails.
            channel_data = next(
                (c for c in channels if c["name"] == ch_name and c["market"] == market),
                {"should_succeed": True},
            )

            if channel_data.get("should_succeed", True):
                deployment_log.append({"channel": ch_name, "market": market, "status": "success", "attempts": 1})
                return json.dumps({"status": "success", "channel": ch_name, "market": market})
            
            error = channel_data.get("error", "UNKNOWN")
            deployment_log.append({"channel": ch_name, "market": market, "status": "failed", "error": error})
            return json.dumps({"status": "failed", "error": error})

        deployer_spec = next(
            (s for s in agent_specs if "Deploy" in s.name or "Deploy" in s.role),
            agent_specs[0],
        )
        agents = self._build_clean_agents([deployer_spec], tools_map={deployer_spec.name: [deploy_channel]})
        deployer = agents[0]

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
            memory=False,
            planning=False,
            step_callback=self.adapter._step_callback,
            verbose=True,
        )

        start = time.time()
        result = await crew.kickoff_async()
        duration_ms = (time.time() - start) * 1000

        structured = None
        if hasattr(result, "pydantic") and result.pydantic:
            structured = result.pydantic.model_dump()

        success_count = sum(1 for l in deployment_log if l["status"] == "success")

        sr = self.adapter._make_result(
            scenario_id="channel_deploy", status="completed",
            output=structured or {
                "crew_output": str(result),
                "deployment_log": deployment_log,
                "summary": {
                    "success": success_count, "tool_calls": self.adapter._tool_call_count,
                },
            },
            total_duration_ms=duration_ms, agent_count=1,
            tool_calls=self.adapter._tool_call_count,
        )
        sr.used_retry = False
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
        from crewai import Crew, Process, Task as CrewTask
        from crewai.tools import tool as crewai_tool

        product = task.get("product", {})

        @crewai_tool("get_product_details")
        def get_product_details(sku: str) -> str:
            """Get product specifications and catalog information by SKU."""
            return json.dumps(product, ensure_ascii=False, indent=2)

        agents = self._build_clean_agents([
            AgentSpec(
                name="Visual Copywriter",
                role="Content Architect & Visual Copywriter",
                goal="Generate Arabic Ramadan ad copy.",
                backstory="Copywriter."
            )
        ], tools_map={"Visual Copywriter": [get_product_details]})
        content_agent = agents[0]

        multimodal_task = CrewTask(
            description=build_multimodal_prompt(
                task,
                is_vision=False,  # Clean mode: no vision check
            ),
            expected_output="Arabic ad copy: Headline + Description + CTA + Carousel body.",
            agent=content_agent,
            # Clean mode: no guardrails
            callback=self.adapter._task_callback,
        )

        crew = Crew(
            agents=[content_agent], tasks=[multimodal_task],
            process=Process.sequential,
            memory=False,
            planning=False,
            step_callback=self.adapter._step_callback,
            verbose=True,
        )

        start = time.time()
        result = await crew.kickoff_async()
        duration_ms = (time.time() - start) * 1000

        return self.adapter._make_result(
            scenario_id="multimodal_ad", status="completed",
            output={
                "ad_copy": str(result),
                "vision_used": False,  # Clean mode: no vision fallback check
            },
            total_duration_ms=duration_ms, agent_count=1,
            tool_calls=self.adapter._tool_call_count,
        )
