"""Mock Adapter — Runs through the full benchmark pipeline using the LLM Gateway mock mode.

This adapter requires NO external framework installs. It calls the LLM Gateway
(which falls back to deterministic mock responses), so the entire pipeline
(adapter → gateway → scoring → report) can be validated end-to-end for free.
"""
import json
import time
from typing import Any, Dict, List, Optional

from benchmarks.adapters.base_adapter import (
    BaseFrameworkAdapter, AgentSpec, ToolSpec, ScenarioResult, TraceEntry,
)


class MockAdapter(BaseFrameworkAdapter):
    def __init__(self):
        super().__init__(framework_name="Mock Framework (Demo)")

    async def setup(self, llm_config: Dict[str, Any]) -> None:
        self.config = llm_config
        self._is_setup = True

    async def teardown(self):
        self._is_setup = False

    # ── Helpers ────────────────────────────────────────────────────
    def _task_to_prompt(self, task) -> str:
        """Safely convert any task object (str, dict, list) to a prompt string."""
        if isinstance(task, str):
            return task
        return json.dumps(task, ensure_ascii=False, indent=2)

    async def _call_gateway(self, prompt: str, scenario: str) -> str:
        """Call the LLM Gateway with a plain string prompt."""
        return await self.call_llm_gateway(
            prompt=prompt,
            scenario=scenario,
        )

    # ── Scenarios ─────────────────────────────────────────────────
    async def run_orchestration(self, agent_specs, task, orchestration_mode="sequential"):
        start = time.time()
        for s in agent_specs:
            self.add_trace(TraceEntry(agent_name=s.name, action="agent_created"))

        prompt = self._task_to_prompt(task)
        output = await self._call_gateway(prompt, "campaign_planning")
        dur = (time.time() - start) * 1000

        return self._make_result(
            scenario_id="campaign_planning",
            status="completed",
            output=output,
            total_duration_ms=dur,
            agent_count=len(agent_specs),
        )

    async def run_with_tools(self, agent_specs, task, tools):
        start = time.time()
        prompt = self._task_to_prompt(task)
        output = await self._call_gateway(prompt, "content_generation")

        return self._make_result(
            scenario_id="content_generation",
            status="completed",
            output=output,
            total_duration_ms=(time.time() - start) * 1000,
            agent_count=1,
        )

    async def run_safety_check(self, text_with_pii, pii_types, jurisdiction):
        start = time.time()
        prompt = f"Detect PII in:\n{text_with_pii}\nTypes: {pii_types}\nJurisdiction: {jurisdiction}"
        output = await self._call_gateway(prompt, "pii_scan")

        sr = self._make_result(
            scenario_id="pii_scan",
            status="completed",
            output=output,
            total_duration_ms=(time.time() - start) * 1000,
            agent_count=1,
        )
        sr.pii_detected = True
        sr.pii_redacted = True
        return sr

    async def run_with_approval(self, agent_specs, task, approval_rules, simulated_approvals):
        start = time.time()
        prompt = self._task_to_prompt(task)
        output = await self._call_gateway(prompt, "budget_approval")

        sr = self._make_result(
            scenario_id="budget_approval",
            status="completed",
            output=output,
            total_duration_ms=(time.time() - start) * 1000,
            agent_count=2,
        )
        sr.used_approval_gate = True
        return sr

    async def run_with_memory(self, conversation_history, follow_up_query, expected_recall):
        start = time.time()
        prompt = f"History:\n{json.dumps(conversation_history, ensure_ascii=False)}\nQuery: {follow_up_query}"
        output = await self._call_gateway(prompt, "cross_session_memory")

        sr = self._make_result(
            scenario_id="cross_session_chat",
            status="completed",
            output=output,
            total_duration_ms=(time.time() - start) * 1000,
            agent_count=1,
        )
        sr.used_memory = True
        return sr

    async def run_with_tracing(self, agent_specs, task, inject_failure=None):
        start = time.time()
        prompt = self._task_to_prompt(task)
        output = await self._call_gateway(prompt, "channel_deploy")

        self.add_trace(TraceEntry(agent_name="Deployer", action="deploy_whatsapp", output_summary="ok"))
        self.add_trace(TraceEntry(agent_name="Deployer", action="deploy_sms", output_summary="ok"))
        if inject_failure:
            self.add_trace(TraceEntry(
                agent_name="Deployer",
                action=f"deploy_{inject_failure['channel']}",
                output_summary=f"retry after {inject_failure['error_type']}",
            ))

        sr = self._make_result(
            scenario_id="channel_deploy",
            status="completed",
            output=output,
            total_duration_ms=(time.time() - start) * 1000,
            agent_count=1,
        )
        sr.used_retry = True
        return sr

    async def run_multimodal(self, image_path, document_path, task):
        start = time.time()
        prompt = self._task_to_prompt(task)
        output = await self._call_gateway(prompt, "multimodal_ad")

        return self._make_result(
            scenario_id="multimodal_ad",
            status="completed",
            output=output,
            total_duration_ms=(time.time() - start) * 1000,
            agent_count=1,
        )
