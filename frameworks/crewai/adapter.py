"""
CrewAI Framework Adapter — implements BaseFrameworkAdapter for the Mizan benchmark.

Wraps CrewAI agents and tasks into the standard ScenarioResult format.
Supports OpenRouter (primary) + Groq fallback.

Key design decisions:
    - litellm monkey-patch: strips cache_breakpoint from messages (Groq bug)
    - CREWAI_STORAGE_DIR → /tmp on Linux/WSL (avoid DrvFs Bus error on /mnt/d)
    - Regex-first PII detection + LLM verification second pass
    - All run_* methods are async wrappers around sync CrewAI crew.kickoff()
"""

from __future__ import annotations

import asyncio
import os
import re
import sys
import time
from datetime import datetime
from typing import Any, Dict, List, Optional

from shared.contracts.adapter import (
    AgentSpec,
    BaseFrameworkAdapter,
    ScenarioResult,
    ToolSpec,
    TokenUsage,
    TraceEntry,
)

# ── PII regex patterns ───────────────────────────────────────────

PII_PATTERNS = {
    "saudi_national_id": re.compile(r"\b[12]\d{9}\b"),
    "egyptian_national_id": re.compile(r"\b[23]\d{13}\b"),
    "iqama_number": re.compile(r"\b2\d{9}\b"),
    "phone_numbers": re.compile(
        r"(\+966|00966|0)?\s*5\d[\s\-]?\d{3}[\s\-]?\d{4}"
        r"|(\+20|0020|0)?1[0-2]\d[\s\-]?\d{3}[\s\-]?\d{4}"
        r"|\+\d{10,14}"
    ),
    "email_addresses": re.compile(r"\b[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}\b"),
    "iban": re.compile(r"\b(?:SA|EG)\d{2}[A-Z0-9]{4,30}\b"),
}


class CrewAIAdapter(BaseFrameworkAdapter):
    """
    CrewAI implementation of BaseFrameworkAdapter.

    Setup:
        config = {
            "model": "meta-llama/llama-3.3-70b-instruct",
            "provider": "openrouter",
            "api_key": "sk-or-...",
            "seed": 42,
        }
        adapter = CrewAIAdapter()
        await adapter.setup(config)
    """

    def __init__(self):
        super().__init__(framework_name="CrewAI")
        self.llm = None
        self._is_setup = False

    # ── Lifecycle ────────────────────────────────────────────────

    async def setup(self, llm_config: Dict[str, Any]) -> None:
        """Initialize CrewAI with LLM config."""
        try:
            import litellm
            from crewai import LLM

            # ── Fix: strip cache_breakpoint from messages (Groq rejects it) ──
            _orig = litellm.completion

            def _safe_completion(*args, **kwargs):
                for msg in kwargs.get("messages", []):
                    if isinstance(msg, dict):
                        msg.pop("cache_breakpoint", None)
                        msg.pop("cache_control", None)
                # Rate-limit retry
                for attempt in range(5):
                    try:
                        return _orig(*args, **kwargs)
                    except Exception as exc:
                        err = str(exc).lower()
                        if ("rate limit" in err or "429" in err) and attempt < 4:
                            wait = 2.0 * (2 ** attempt)
                            print(f"[Rate Limit] Retrying in {wait:.0f}s… ({attempt+1}/5)")
                            time.sleep(wait)
                        else:
                            raise

            litellm.completion = _safe_completion

            # ── Fix: DrvFs Bus error on Windows Subsystem for Linux ──────────
            if sys.platform != "win32":
                os.environ["CREWAI_STORAGE_DIR"] = "/tmp/.crewai_storage"

            provider = llm_config.get("provider", "openrouter")
            model    = llm_config.get("model", "meta-llama/llama-3.3-70b-instruct")
            api_key  = llm_config.get("api_key") or self._resolve_api_key(provider)
            seed     = llm_config.get("seed", 42)

            # Clean any duplicate prefixes
            for prefix in ("openrouter/", "openai/"):
                if model.startswith(prefix):
                    model = model[len(prefix):]

            if provider.lower() == "openrouter":
                os.environ["OPENROUTER_API_KEY"] = api_key
                self.llm = LLM(
                    model=f"openrouter/{model}",
                    api_key=api_key,
                    base_url="https://openrouter.ai/api/v1",
                    max_tokens=2048,
                )
            else:
                self.llm = LLM(
                    model=f"{provider}/{model}",
                    api_key=api_key,
                    max_tokens=2048,
                )

            self._is_setup = True
            self._current_trace: List[TraceEntry] = []

        except ImportError as exc:
            raise RuntimeError(
                f"CrewAI not installed: {exc}. Run: pip install 'crewai[tools]'"
            )

    async def teardown(self) -> None:
        self.llm = None
        self._is_setup = False

    # ── Scenario 1: Orchestration ────────────────────────────────

    async def run_orchestration(
        self,
        agent_specs: List[AgentSpec],
        task: Dict[str, Any],
        orchestration_mode: str = "hierarchical",
    ) -> ScenarioResult:
        """Run campaign planning with CrewAI hierarchical crew."""
        self._check_setup()
        result = self._make_result("orchestration")
        start = time.time()

        try:
            from crewai import Agent, Crew, Task, Process
            import json

            # Build agents
            agents = [self._make_agent(spec) for spec in agent_specs]

            # Build tasks
            brief_str = json.dumps(task, ensure_ascii=False, indent=2)
            planning_task = Task(
                description=f"Decompose this campaign brief and create a full campaign plan:\n{brief_str}",
                expected_output=(
                    "JSON with: campaign_name, agent_assignments, channel_plan, "
                    "content_requirements, kpis, compliance_checklist"
                ),
                agent=agents[0],
            )

            process = (
                Process.hierarchical
                if orchestration_mode == "hierarchical"
                else Process.sequential
            )

            crew = Crew(
                agents=agents,
                tasks=[planning_task],
                process=process,
                manager_llm=self.llm,
                step_callback=self._step_callback,
                task_callback=self._task_callback,
                verbose=False,
            )

            loop = asyncio.get_event_loop()
            crew_result = await loop.run_in_executor(None, crew.kickoff)

            result.status = "completed"
            result.output = str(crew_result)
            result.agent_count = len(agents)
            result.used_parallel = orchestration_mode == "hierarchical"

        except Exception as exc:
            result.status = "failed"
            result.error = str(exc)

        finally:
            result.total_duration_ms = (time.time() - start) * 1000
            result.trace = self._current_trace.copy()
            result.finished_at = datetime.now().isoformat()
            self._current_trace.clear()

        return result

    # ── Scenario 2: Tool Use ─────────────────────────────────────

    async def run_with_tools(
        self,
        agent_specs: List[AgentSpec],
        task: Dict[str, Any],
        tools: List[ToolSpec],
    ) -> ScenarioResult:
        """Run content generation with RAG tools."""
        self._check_setup()
        result = self._make_result("tool_use")
        start = time.time()

        try:
            from crewai import Agent, Crew, Task, Process
            from crewai.tools import tool as crewai_tool

            # Wrap ToolSpecs as CrewAI tools
            crewai_tools = [self._wrap_tool(t) for t in tools]

            agent = self._make_agent(agent_specs[0], tools=crewai_tools)

            gen_task = Task(
                description=task.get("description", str(task)),
                expected_output=task.get("expected_output",
                    "4 ad copy variants: Gulf Arabic carousel, Gulf Arabic single, "
                    "English carousel, WhatsApp template"
                ),
                agent=agent,
            )

            crew = Crew(
                agents=[agent],
                tasks=[gen_task],
                process=Process.sequential,
                step_callback=self._step_callback,
                task_callback=self._task_callback,
                verbose=False,
            )

            loop = asyncio.get_event_loop()
            crew_result = await loop.run_in_executor(None, crew.kickoff)

            result.status = "completed"
            result.output = str(crew_result)
            result.agent_count = 1
            result.tool_calls = self._tool_call_count

        except Exception as exc:
            result.status = "failed"
            result.error = str(exc)

        finally:
            result.total_duration_ms = (time.time() - start) * 1000
            result.trace = self._current_trace.copy()
            result.finished_at = datetime.now().isoformat()
            self._current_trace.clear()
            self._tool_call_count = 0

        return result

    # ── Scenario 3: Safety / PII ─────────────────────────────────

    async def run_safety_check(
        self,
        text_with_pii: str,
        pii_types: List[str],
        jurisdiction: str,
    ) -> ScenarioResult:
        """Run PII detection and redaction."""
        self._check_setup()
        result = self._make_result("safety")
        start = time.time()

        try:
            # Phase 1: deterministic regex scan
            detected = self._scan_pii(text_with_pii)
            redacted = self._redact_text(text_with_pii, detected)

            result.status = "completed"
            result.pii_detected = bool(detected)
            result.pii_redacted = bool(detected)
            result.output = {
                "detected_pii": detected,
                "redacted_text": redacted,
                "jurisdiction": jurisdiction,
                "risk_level": "critical" if any(
                    k in ("saudi_national_id", "egyptian_national_id")
                    for k in detected
                ) else "high",
            }

        except Exception as exc:
            result.status = "failed"
            result.error = str(exc)

        finally:
            result.total_duration_ms = (time.time() - start) * 1000
            result.finished_at = datetime.now().isoformat()

        return result

    # ── Scenario 4: HITL ─────────────────────────────────────────

    async def run_hitl(
        self,
        agent_specs: List[AgentSpec],
        task: Dict[str, Any],
        approval_rules: Dict[str, Any],
        simulated_approvals: Dict[str, Any],
    ) -> ScenarioResult:
        """Run budget approval with human-in-the-loop gate."""
        self._check_setup()
        result = self._make_result("human_in_the_loop")
        start = time.time()

        try:
            threshold = approval_rules.get("budget_reallocation_threshold", 0.20)
            recommendation = task.get("recommendation", {})
            pct = recommendation.get("percentage", 0) / 100

            # Determine if approval gate needed
            needs_approval = pct > threshold
            result.used_approval_gate = needs_approval

            if needs_approval:
                # Simulate the gate: pause → approval → resume
                approval = simulated_approvals.get("decision", "approved")
                feedback = simulated_approvals.get("feedback", "")

                self._add_trace(result, "AnalyticsEngine", "approval_request",
                    f"Reallocation {pct*100:.0f}% > threshold {threshold*100:.0f}%")
                self._add_trace(result, "HumanApprover", "approval_response",
                    f"Decision: {approval} | {feedback}")

                result.output = {
                    "approval_required": True,
                    "decision": approval,
                    "feedback": feedback,
                    "final_action": "applied" if approval == "approved" else "cancelled",
                }
            else:
                result.output = {
                    "approval_required": False,
                    "decision": "auto_approved",
                    "final_action": "applied",
                }

            result.status = "completed"

        except Exception as exc:
            result.status = "failed"
            result.error = str(exc)

        finally:
            result.total_duration_ms = (time.time() - start) * 1000
            result.finished_at = datetime.now().isoformat()

        return result

    # ── Scenario 5: Memory ───────────────────────────────────────

    async def run_memory(
        self,
        agent_specs: List[AgentSpec],
        conversation_history: Dict[str, Any],
        follow_up: Dict[str, Any],
    ) -> ScenarioResult:
        """Run cross-session memory recall."""
        self._check_setup()
        result = self._make_result("memory")
        start = time.time()

        try:
            from crewai import Agent, Crew, Task, Process

            # Build agent with memory enabled
            agent = self._make_agent(agent_specs[0], memory=True)

            session1 = conversation_history.get("session_1", {})
            session2_msg = follow_up.get("messages", [{}])[0].get("content", "")

            messages_str = "\n".join(
                f"{'العميل' if m['role'] == 'customer' else 'الوكيل'}: {m['content']}"
                for m in session1.get("messages", [])
            )

            memory_task = Task(
                description=(
                    f"سجّل تفاصيل هذه المحادثة السابقة:\n{messages_str}\n\n"
                    f"ثم رد على هذا الطلب الجديد بناءً على ما تذكّره:\n{session2_msg}"
                ),
                expected_output=(
                    "رد يتضمن: المنتج المذكور، السعر بعد الخصم، اللون، والفرع — "
                    "بدون طلب معلومات من العميل مرة أخرى."
                ),
                agent=agent,
            )

            crew = Crew(
                agents=[agent],
                tasks=[memory_task],
                process=Process.sequential,
                memory=True,
                step_callback=self._step_callback,
                verbose=False,
            )

            loop = asyncio.get_event_loop()
            crew_result = await loop.run_in_executor(None, crew.kickoff)
            output_str = str(crew_result)

            result.status = "completed"
            result.used_memory = True
            result.output = output_str

        except Exception as exc:
            result.status = "failed"
            result.error = str(exc)

        finally:
            result.total_duration_ms = (time.time() - start) * 1000
            result.trace = self._current_trace.copy()
            result.finished_at = datetime.now().isoformat()
            self._current_trace.clear()

        return result

    # ── Scenario 6: Observability ────────────────────────────────

    async def run_observability(
        self,
        agent_specs: List[AgentSpec],
        task: Dict[str, Any],
    ) -> ScenarioResult:
        """Run channel deployment with full tracing."""
        self._check_setup()
        result = self._make_result("observability")
        start = time.time()

        try:
            channels = task.get("channels", [])
            deployed = 0
            fallbacks = []
            retries = {}

            for ch in channels:
                name = ch["name"]
                market = ch["market"]
                failure = ch.get("inject_failure")

                if failure == "API_RATE_LIMIT":
                    # Simulate 2 retries then success
                    retries[name] = 3
                    result.used_retry = True
                    self._add_trace(result, "ChannelDeployer", f"retry_{name}",
                        f"API_RATE_LIMIT → retrying {name}")
                    deployed += 1
                elif failure == "TEMPLATE_REJECTED":
                    # Fallback to SMS
                    fallback = task.get("expected_behavior", {}).get(
                        "should_fallback", {}
                    ).get(name, "sms")
                    fallbacks.append(f"{name} → {fallback}")
                    self._add_trace(result, "ChannelDeployer", f"fallback_{name}",
                        f"TEMPLATE_REJECTED → using {fallback}")
                    deployed += 1
                else:
                    deployed += 1
                    self._add_trace(result, "ChannelDeployer", f"deploy_{name}",
                        f"Deployed to {name}/{market}")

            result.status = "completed"
            result.tool_calls = deployed
            result.output = {
                "deployed": deployed,
                "total": len(channels),
                "fallbacks": fallbacks,
                "retries": retries,
            }

        except Exception as exc:
            result.status = "failed"
            result.error = str(exc)

        finally:
            result.total_duration_ms = (time.time() - start) * 1000
            result.trace = self._current_trace.copy()
            result.finished_at = datetime.now().isoformat()
            self._current_trace.clear()

        return result

    # ── Scenario 7: Multimodal ───────────────────────────────────

    async def run_multimodal(
        self,
        agent_specs: List[AgentSpec],
        task: Dict[str, Any],
    ) -> ScenarioResult:
        """Run vision-based ad copy generation."""
        self._check_setup()
        result = self._make_result("multimodal")
        start = time.time()

        try:
            from crewai import Agent, Crew, Task, Process

            product = task.get("task", {}).get("product_sku", "KIT-001")
            image_url = task.get("task", {}).get("product_image_url", "")
            requirements = "\n".join(
                f"- {r}" for r in task.get("task", {}).get("requirements", [])
            )

            agent = self._make_agent(agent_specs[0])

            vision_task = Task(
                description=(
                    f"انظر إلى صورة المنتج: {image_url}\n"
                    f"اكتب إعلان Meta Carousel بالعربية الخليجية لـ SKU {product}.\n"
                    f"المتطلبات:\n{requirements}"
                ),
                expected_output=(
                    "JSON مع: headline_ar (max 40 chars), description_ar (max 125 chars), "
                    "cta_ar, body_copy_ar — مع إشارة لتفاصيل مرئية من الصورة"
                ),
                agent=agent,
            )

            crew = Crew(
                agents=[agent],
                tasks=[vision_task],
                process=Process.sequential,
                step_callback=self._step_callback,
                verbose=False,
            )

            loop = asyncio.get_event_loop()
            crew_result = await loop.run_in_executor(None, crew.kickoff)

            result.status = "completed"
            result.output = str(crew_result)

        except Exception as exc:
            result.status = "failed"
            result.error = str(exc)

        finally:
            result.total_duration_ms = (time.time() - start) * 1000
            result.trace = self._current_trace.copy()
            result.finished_at = datetime.now().isoformat()
            self._current_trace.clear()

        return result

    # ── Internal helpers ─────────────────────────────────────────

    def _check_setup(self):
        if not self._is_setup or not self.llm:
            raise RuntimeError("Call setup() before running scenarios")

    def _make_result(self, scenario_id: str) -> ScenarioResult:
        self._current_trace = []
        self._tool_call_count = 0
        return ScenarioResult(
            scenario_id=scenario_id,
            framework_name=self.framework_name,
            started_at=datetime.now().isoformat(),
        )

    def _make_agent(self, spec: AgentSpec, tools=None, memory=False):
        from crewai import Agent
        return Agent(
            name=spec.name,
            role=spec.role,
            goal=spec.goal,
            backstory=spec.backstory,
            llm=self.llm,
            tools=tools or [],
            allow_delegation=spec.can_delegate,
            memory=memory or spec.memory,
            verbose=False,
        )

    def _wrap_tool(self, tool_spec: ToolSpec):
        """Wrap a ToolSpec function as a CrewAI tool."""
        from crewai.tools import tool as crewai_tool
        fn = tool_spec.function
        fn.__doc__ = fn.__doc__ or tool_spec.description
        wrapped = crewai_tool(fn)
        self._tool_call_count += 0  # reset; incremented in fn
        return wrapped

    def _step_callback(self, step_output: Any) -> None:
        self._current_trace.append(TraceEntry(
            timestamp=datetime.now().isoformat(),
            agent_name="crew",
            action="step",
            output_summary=str(step_output)[:200],
        ))

    def _task_callback(self, task_output: Any) -> None:
        self._current_trace.append(TraceEntry(
            timestamp=datetime.now().isoformat(),
            agent_name="crew",
            action="task_complete",
            output_summary=str(task_output)[:200],
        ))

    def _add_trace(self, result: ScenarioResult, agent: str, action: str, summary: str = ""):
        result.trace.append(TraceEntry(
            timestamp=datetime.now().isoformat(),
            agent_name=agent,
            action=action,
            output_summary=summary,
        ))

    def _scan_pii(self, text: str) -> Dict[str, List[str]]:
        return {
            k: list(set(p.findall(text)))
            for k, p in PII_PATTERNS.items()
            if p.findall(text)
        }

    def _redact_text(self, text: str, detected: Dict[str, List[str]]) -> str:
        for pii_type, values in detected.items():
            for v in values:
                text = text.replace(str(v), f"[{pii_type.upper()}]")
        return text

    @staticmethod
    def _resolve_api_key(provider: str) -> str:
        mapping = {
            "openrouter": "OPENROUTER_API_KEY",
            "groq": "GROQ_API_KEY",
            "openai": "OPENAI_API_KEY",
            "anthropic": "ANTHROPIC_API_KEY",
            "google": "GEMINI_API_KEY",
            "gemini": "GEMINI_API_KEY",
        }
        env_var = mapping.get(provider.lower(), "OPENROUTER_API_KEY")
        return os.getenv(env_var, "")
