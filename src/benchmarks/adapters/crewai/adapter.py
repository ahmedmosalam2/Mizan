import os
import sys
from typing import Any, Dict, List, Optional, Tuple

from benchmarks.models import (
    BaseFrameworkAdapter,
    AgentSpec,
    ToolSpec,
    ScenarioResult,
    TraceEntry,
)
from benchmarks.adapters.crewai.utils import _PII_PATTERNS


class CrewaiAdapter(BaseFrameworkAdapter):
    """
    CrewAI Framework Adapter — Supports Clean Mode and Full Mode.
    Defines the adapter structure and routes requests to the appropriate runner mode.
    """

    def __init__(self):
        super().__init__(framework_name="CrewAI")
        self.llm = None
        self._tool_call_count = 0
        self._provider = "groq"
        self._api_key = ""
        self.mode = "full"
        self.runner = None

    # ── Lifecycle ──────────────────────────────────────────────────

    async def setup(self, llm_config: Dict[str, Any]) -> None:
        try:
            import litellm
            from crewai import LLM

            # ── Groq cache_breakpoint fix ────────────────────────────────────
            # CrewAI's experimental executor injects cache_breakpoint INSIDE
            # message dicts (not as a top-level param), so drop_params won't help.
            # We monkey-patch litellm.completion to strip it before it hits Groq.
            _orig_completion = litellm.completion

            def _safe_completion(*args, **kwargs):
                if "messages" in kwargs:
                    for msg in kwargs["messages"]:
                        if isinstance(msg, dict):
                            msg.pop("cache_breakpoint", None)
                            msg.pop("cache_control", None)
                
                # Auto-retry on Rate Limit errors (useful for Groq Free Tier TPM limits)
                import time
                import random
                retries = 5
                backoff = 2.0
                for attempt in range(retries):
                    try:
                        return _orig_completion(*args, **kwargs)
                    except (litellm.exceptions.RateLimitError, Exception) as e:
                        # Only retry if it is explicitly a rate limit or temp overload error
                        err_str = str(e).lower()
                        is_rate_limit = "rate limit" in err_str or "429" in err_str or "tpm" in err_str
                        if is_rate_limit and attempt < retries - 1:
                            sleep_time = backoff * (2 ** attempt) + random.uniform(0.1, 1.0)
                            print(f"\n[Rate Limit] Groq TPM limit hit. Retrying in {sleep_time:.2f}s... (Attempt {attempt+1}/{retries})")
                            time.sleep(sleep_time)
                            continue
                        raise e

            litellm.completion = _safe_completion
            # ─────────────────────────────────────────────────────────────────

            # Force CrewAI storage to /tmp on Linux/WSL to avoid Bus error on /mnt/d (DrvFs)
            if sys.platform != "win32":
                os.environ["CREWAI_STORAGE_DIR"] = "/tmp/.crewai_storage"

            self.mode = llm_config.get("mode", "full")
            provider = llm_config.get("provider", "openrouter")
            model    = llm_config.get("model", "meta-llama/llama-3.3-70b-instruct:free")
            api_key  = llm_config.get("api_key", "")

            # ── Automatically resolve API key from Env if not provided ──────
            if not api_key:
                prov_lower = provider.lower()
                if prov_lower == "openrouter":
                    api_key = os.getenv("OPENROUTER_API_KEY", "")
                elif prov_lower == "groq":
                    api_key = os.getenv("GROQ_API_KEY", "")
                elif prov_lower in ("google", "gemini"):
                    api_key = os.getenv("GEMINI_API_KEY", "") or os.getenv("GOOGLE_API_KEY", "")
                elif prov_lower == "openai":
                    api_key = os.getenv("OPENAI_API_KEY", "")
                elif prov_lower == "anthropic":
                    api_key = os.getenv("ANTHROPIC_API_KEY", "")
            
            # Print debug for loaded API key
            print(f"[Debug] Loaded API key for {provider}: {api_key[:10]}...{api_key[-5:] if len(api_key) > 5 else ''}")
            
            api_key = api_key or "mock_key"

            self._provider = provider
            self._api_key = api_key

            gateway  = os.getenv("LLM_GATEWAY_URL")
            
            # Strip duplicate prefixes from model string
            clean_model = model
            if clean_model.startswith("openrouter/"):
                clean_model = clean_model.replace("openrouter/", "", 1)
            if clean_model.startswith("openai/"):
                clean_model = clean_model.replace("openai/", "", 1)

            # Standard native OpenRouter configuration
            if provider.lower() == "openrouter":
                os.environ["OPENROUTER_API_KEY"] = api_key
                self.llm = LLM(model=f"openrouter/{clean_model}", api_key=api_key, max_tokens=1000)
            elif gateway:
                self.llm = LLM(model=f"openai/{clean_model}", api_key=api_key, base_url=gateway, max_tokens=1000)
            else:
                # LiteLLM natively handles openrouter/ prefix if the key is provided
                self.llm = LLM(model=f"{provider}/{clean_model}", api_key=api_key, max_tokens=1000)



            # Lazy load runner based on mode
            if self.mode == "clean":
                from benchmarks.adapters.crewai.clean_mode import CleanModeRunner
                self.runner = CleanModeRunner(self)
            else:
                from benchmarks.adapters.crewai.full_mode import FullModeRunner
                self.runner = FullModeRunner(self)

            self._is_setup = True
            self.add_trace(TraceEntry(
                agent_name="system", action="setup",
                output_summary=f"model={model} | mode={self.mode} | gateway={'yes' if gateway else 'no'}",
            ))
        except ImportError as e:
            raise RuntimeError(f"CrewAI missing: {e}. Run: pip install 'crewai[tools]'")

    async def teardown(self) -> None:
        self.llm = None
        self.runner = None
        self._is_setup = False

    # ── Internal Helpers ───────────────────────────────────────────

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

    # ── Dimension Routing ──────────────────────────────────────────

    async def run_orchestration(
        self,
        agent_specs: List[AgentSpec],
        task: Dict[str, Any],
        orchestration_mode: str = "hierarchical",
    ) -> ScenarioResult:
        if not self._is_setup or not self.runner:
            raise RuntimeError("Adapter is not setup.")
        return await self.runner.run_orchestration(agent_specs, task, orchestration_mode)

    async def run_with_tools(
        self,
        agent_specs: List[AgentSpec],
        task: Dict[str, Any],
        tools: List[ToolSpec],
    ) -> ScenarioResult:
        if not self._is_setup or not self.runner:
            raise RuntimeError("Adapter is not setup.")
        return await self.runner.run_with_tools(agent_specs, task, tools)

    async def run_safety_check(
        self,
        text_with_pii: str,
        pii_types: List[str],
        jurisdiction: str,
        expected_pii: Optional[Dict[str, List[str]]] = None,
    ) -> ScenarioResult:
        if not self._is_setup or not self.runner:
            raise RuntimeError("Adapter is not setup.")
        return await self.runner.run_safety_check(text_with_pii, pii_types, jurisdiction, expected_pii)

    async def run_with_approval(
        self,
        agent_specs: List[AgentSpec],
        task: Dict[str, Any],
        approval_rules: Dict[str, Any],
        simulated_approvals: List[Dict[str, Any]],
    ) -> ScenarioResult:
        if not self._is_setup or not self.runner:
            raise RuntimeError("Adapter is not setup.")
        return await self.runner.run_with_approval(
            agent_specs, task, approval_rules, simulated_approvals
        )

    async def run_with_memory(
        self,
        conversation_history: List[Dict[str, Any]],
        follow_up_query: str,
        expected_recall: List[str],
    ) -> ScenarioResult:
        if not self._is_setup or not self.runner:
            raise RuntimeError("Adapter is not setup.")
        return await self.runner.run_with_memory(conversation_history, follow_up_query, expected_recall)

    async def run_with_tracing(
        self,
        agent_specs: List[AgentSpec],
        task: Dict[str, Any],
        inject_failure: Optional[Dict[str, Any]] = None,
    ) -> ScenarioResult:
        if not self._is_setup or not self.runner:
            raise RuntimeError("Adapter is not setup.")
        return await self.runner.run_with_tracing(agent_specs, task, inject_failure)

    async def run_multimodal(
        self,
        image_path: Optional[str],
        document_path: Optional[str],
        task: Dict[str, Any],
    ) -> ScenarioResult:
        if not self._is_setup or not self.runner:
            raise RuntimeError("Adapter is not setup.")
        return await self.runner.run_multimodal(image_path, document_path, task)

    # CrewAI Flow Bonus scenario
    async def run_as_flow(
        self,
        campaign_brief: Dict[str, Any],
        simulated_approval: Dict[str, Any],
    ) -> ScenarioResult:
        if not self._is_setup or not self.runner:
            raise RuntimeError("Adapter is not setup.")
        # Only FullModeRunner has run_as_flow. If in CleanMode, return non-supported result.
        if hasattr(self.runner, "run_as_flow"):
            return await self.runner.run_as_flow(campaign_brief, simulated_approval)
        
        return self._make_result(
            scenario_id="campaign_flow",
            status="failed",
            error="CrewAI Flows scenario is not supported in Clean Mode.",
            total_duration_ms=0,
        )
