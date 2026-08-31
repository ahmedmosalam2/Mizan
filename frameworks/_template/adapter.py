"""
Template Adapter — Skeleton for a new framework adapter.

Replace every `raise NotImplementedError` with your framework's implementation.
The run_* methods map 1-to-1 to the 7 benchmark dimensions.
"""

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


class TemplateAdapter(BaseFrameworkAdapter):
    """
    Skeleton adapter — replace with your framework's implementation.
    """

    def __init__(self):
        super().__init__(framework_name="template")
        self._llm = None

    # ── Lifecycle ────────────────────────────────────────────────

    async def setup(self, llm_config: Dict[str, Any]) -> None:
        """Initialize your framework's LLM and any global setup."""
        # Example:
        # from your_framework import YourLLM
        # self._llm = YourLLM(model=llm_config["model"], api_key=llm_config["api_key"])
        raise NotImplementedError

    async def teardown(self) -> None:
        """Clean up resources."""
        self._llm = None

    # ── Scenario implementations ─────────────────────────────────

    async def run_orchestration(
        self,
        agent_specs: List[AgentSpec],
        task: Dict[str, Any],
        orchestration_mode: str = "sequential",
    ) -> ScenarioResult:
        """
        Dimension 1: Orchestration.
        Create agents, run campaign planning task, return structured result.
        """
        start = time.time()
        result = ScenarioResult(
            scenario_id="orchestration",
            framework_name=self.framework_name,
            started_at=datetime.now().isoformat(),
        )
        try:
            # TODO: implement with your framework
            raise NotImplementedError

        except Exception as e:
            result.status = "failed"
            result.error = str(e)
        finally:
            result.total_duration_ms = (time.time() - start) * 1000
            result.finished_at = datetime.now().isoformat()
        return result

    async def run_with_tools(
        self,
        agent_specs: List[AgentSpec],
        task: Dict[str, Any],
        tools: List[ToolSpec],
    ) -> ScenarioResult:
        """Dimension 2: Tool Use & Integrations."""
        raise NotImplementedError

    async def run_safety_check(
        self,
        text_with_pii: str,
        pii_types: List[str],
        jurisdiction: str,
    ) -> ScenarioResult:
        """Dimension 3: Safety & Privacy."""
        raise NotImplementedError

    async def run_hitl(
        self,
        agent_specs: List[AgentSpec],
        task: Dict[str, Any],
        approval_rules: Dict[str, Any],
        simulated_approvals: Dict[str, Any],
    ) -> ScenarioResult:
        """Dimension 4: Human-in-the-Loop."""
        raise NotImplementedError

    async def run_memory(
        self,
        agent_specs: List[AgentSpec],
        conversation_history: Dict[str, Any],
        follow_up: Dict[str, Any],
    ) -> ScenarioResult:
        """Dimension 5: Memory & State."""
        raise NotImplementedError

    async def run_observability(
        self,
        agent_specs: List[AgentSpec],
        task: Dict[str, Any],
    ) -> ScenarioResult:
        """Dimension 6: Observability."""
        raise NotImplementedError

    async def run_multimodal(
        self,
        agent_specs: List[AgentSpec],
        task: Dict[str, Any],
    ) -> ScenarioResult:
        """Dimension 7: Multimodal."""
        raise NotImplementedError

    # ── Helpers ──────────────────────────────────────────────────

    def _make_result(self, scenario_id: str) -> ScenarioResult:
        return ScenarioResult(
            scenario_id=scenario_id,
            framework_name=self.framework_name,
            started_at=datetime.now().isoformat(),
        )

    def _add_trace(
        self,
        result: ScenarioResult,
        agent_name: str,
        action: str,
        input_summary: str = "",
        output_summary: str = "",
        duration_ms: float = 0.0,
    ) -> None:
        result.trace.append(TraceEntry(
            timestamp=datetime.now().isoformat(),
            agent_name=agent_name,
            action=action,
            input_summary=input_summary,
            output_summary=output_summary,
            duration_ms=duration_ms,
        ))
