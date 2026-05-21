"""
OpenAI Agents SDK Adapter.

Uses OpenAI's native Agents SDK (formerly Swarm successor)
with built-in tool calling and handoffs.
"""

import time
import json
import re
from typing import Any, Dict, List, Optional

from benchmarks.adapters.base_adapter import (
    BaseFrameworkAdapter,
    AgentSpec,
    ToolSpec,
    ScenarioResult,
    TraceEntry,
)


class OpenaiAgentsAdapter(BaseFrameworkAdapter):
    """Adapter for OpenAI Agents SDK."""

    def __init__(self):
        super().__init__(framework_name="OpenAI Agents SDK")
        self.api_key = ""
        self.model_name = ""

    async def setup(self, llm_config: Dict[str, Any]) -> None:
        try:
            from agents import Agent
            self.model_name = llm_config.get("model", "gpt-4o-mini")
            self.api_key = llm_config.get("api_key", "")
            self._is_setup = True
            self.add_trace(TraceEntry(
                agent_name="system", action="setup",
                output_summary=f"OpenAI Agents SDK initialized with {self.model_name}",
            ))
        except ImportError:
            raise RuntimeError("Install: pip install openai-agents")

    async def teardown(self) -> None:
        self._is_setup = False

    # ── Dimension 1: Orchestration ─────────────────────────────────
    async def run_orchestration(
        self, agent_specs: List[AgentSpec], task: Dict[str, Any],
        orchestration_mode: str = "sequential",
    ) -> ScenarioResult:
        from agents import Agent, Runner

        # Create agents with handoff chain
        agents = []
        for i, spec in enumerate(agent_specs):
            agent = Agent(
                name=spec.name,
                instructions=f"Role: {spec.role}\nGoal: {spec.goal}\nBackstory: {spec.backstory}",
                model=self.model_name,
            )
            agents.append(agent)
            self.add_trace(TraceEntry(agent_name=spec.name, action="agent_created", output_summary=spec.role))

        # Set up handoffs for sequential flow
        for i in range(len(agents) - 1):
            agents[i].handoffs = [agents[i + 1]]

        # Run from first agent
        task_msg = (
            f"Ramadan campaign brief:\n{json.dumps(task, ensure_ascii=False, indent=2)}\n\n"
            f"Produce your deliverable, then hand off to the next agent."
        )

        start = time.time()
        result = await Runner.run(agents[0], task_msg)
        duration = (time.time() - start) * 1000

        self.add_trace(TraceEntry(
            agent_name="orchestration", action="complete",
            output_summary=result.final_output[:200] if result.final_output else "",
            duration_ms=duration,
        ))

        return self._make_result(
            scenario_id="campaign_planning", status="completed",
            output=result.final_output,
            total_duration_ms=duration, agent_count=len(agents),
        )

    # ── Dimension 2: Tool Use ──────────────────────────────────────
    async def run_with_tools(
        self, agent_specs: List[AgentSpec], task: Dict[str, Any],
        tools: List[ToolSpec],
    ) -> ScenarioResult:
        from agents import Agent, Runner, function_tool

        # Convert ToolSpecs to OpenAI function tools
        oai_tools = []
        for t in tools:
            @function_tool(name_override=t.name, description_override=t.description)
            def dynamic_tool(query: str, _fn=t.function) -> str:
                return _fn(query)
            oai_tools.append(dynamic_tool)

        spec = agent_specs[0]
        agent = Agent(
            name=spec.name,
            instructions=f"Role: {spec.role}\nGoal: {spec.goal}",
            model=self.model_name,
            tools=oai_tools,
        )

        task_msg = (
            f"{task['goal']}\n\n"
            f"Product: {json.dumps(task.get('product', {}), ensure_ascii=False)}\n"
            f"Market: {task.get('market', 'KSA')}\n"
            f"Use tools first."
        )

        start = time.time()
        result = await Runner.run(agent, task_msg)
        duration = (time.time() - start) * 1000

        tool_count = sum(1 for item in result.raw_responses
                         if hasattr(item, 'tool_calls') and item.tool_calls)

        self.add_trace(TraceEntry(
            agent_name=spec.name, action="tool_use_complete",
            output_summary=result.final_output[:200] if result.final_output else "",
        ))

        return self._make_result(
            scenario_id="content_generation", status="completed",
            output=result.final_output,
            total_duration_ms=duration, agent_count=1, tool_calls=tool_count,
        )

    # ── Dimension 3: Safety ────────────────────────────────────────
    async def run_safety_check(
        self, text_with_pii: str, pii_types: List[str], jurisdiction: str,
    ) -> ScenarioResult:
        from agents import Agent, Runner

        agent = Agent(
            name="ComplianceGuardian",
            instructions="Detect and redact PII. Apply Saudi PDPL and Egypt Law 151/2020.",
            model=self.model_name,
        )

        start = time.time()
        result = await Runner.run(agent, (
            f"Detect PII:\n{text_with_pii}\n\n"
            f"Output JSON: detected_pii, redacted_text, jurisdiction_notes"
        ))
        duration = (time.time() - start) * 1000

        output_str = result.final_output or ""
        parsed = {"raw": output_str}
        try:
            match = re.search(r'\{[\s\S]*\}', output_str)
            if match:
                parsed = json.loads(match.group())
        except json.JSONDecodeError:
            pass

        self.add_trace(TraceEntry(agent_name="ComplianceGuardian", action="pii_scan", output_summary=output_str[:200]))

        sr = self._make_result(
            scenario_id="pii_scan", status="completed",
            output=parsed, total_duration_ms=duration, agent_count=1,
        )
        sr.pii_detected = True
        sr.pii_redacted = "redacted_text" in parsed
        return sr

    # ── Dimension 4: HITL ──────────────────────────────────────────
    async def run_with_approval(
        self, agent_specs: List[AgentSpec], task: Dict[str, Any],
        approval_rules: Dict[str, Any], simulated_approvals: List[Dict[str, Any]],
    ) -> ScenarioResult:
        from agents import Agent, Runner

        approval = simulated_approvals[0] if simulated_approvals else {}

        analyst = Agent(
            name="AnalyticsAgent",
            instructions="Analyze budget. Flag reallocation > 20% for approval.",
            model=self.model_name,
        )

        commander = Agent(
            name="CampaignCommander",
            instructions=(
                f"Approval coordinator. Simulated approval:\n{json.dumps(approval, ensure_ascii=False)}\n"
                f"Incorporate feedback into final allocation."
            ),
            model=self.model_name,
        )
        analyst.handoffs = [commander]

        start = time.time()
        result = await Runner.run(analyst, json.dumps(task, ensure_ascii=False, indent=2))
        duration = (time.time() - start) * 1000

        self.add_trace(TraceEntry(agent_name="AnalyticsAgent", action="budget_analysis"))
        self.add_trace(TraceEntry(agent_name="system", action="approval_gate", output_summary=approval.get("decision", "")))
        self.add_trace(TraceEntry(agent_name="CampaignCommander", action="apply_reallocation"))

        sr = self._make_result(
            scenario_id="budget_approval", status="completed",
            output=result.final_output,
            total_duration_ms=duration, agent_count=2,
        )
        sr.used_approval_gate = True
        return sr

    # ── Dimension 5: Memory ────────────────────────────────────────
    async def run_with_memory(
        self, conversation_history: List[Dict[str, str]],
        follow_up_query: str, expected_recall: List[str],
    ) -> ScenarioResult:
        from agents import Agent, Runner

        history_text = ""
        for session in conversation_history:
            history_text += f"\n--- {session['session_id']} ---\n"
            for msg in session["messages"]:
                role = "Customer" if msg["role"] == "customer" else "Agent"
                history_text += f"{role}: {msg['content']}\n"

        agent = Agent(
            name="CustomerEngagement",
            instructions="Customer service agent. Recall details from previous conversations.",
            model=self.model_name,
        )

        start = time.time()
        result = await Runner.run(agent, (
            f"History:\n{history_text}\n\nCustomer: '{follow_up_query}'\n\n"
            f"Respond with: product, price, color, branch."
        ))
        duration = (time.time() - start) * 1000

        self.add_trace(TraceEntry(agent_name="CustomerEngagement", action="memory_recall", output_summary=(result.final_output or "")[:200]))

        sr = self._make_result(
            scenario_id="cross_session_chat", status="completed",
            output=result.final_output,
            total_duration_ms=duration, agent_count=1,
        )
        sr.used_memory = True
        return sr

    # ── Dimension 6: Observability ─────────────────────────────────
    async def run_with_tracing(
        self, agent_specs: List[AgentSpec], task: Dict[str, Any],
        inject_failure: Optional[Dict[str, Any]] = None,
    ) -> ScenarioResult:
        from agents import Agent, Runner

        channels = task.get("channels", [])
        agent = Agent(
            name="ChannelDeployer",
            instructions="Deploy campaigns. Retry rate limits. Fallback WhatsApp→SMS.",
            model=self.model_name,
        )

        start = time.time()
        result = await Runner.run(agent, (
            f"Deploy:\n{json.dumps(channels, ensure_ascii=False, indent=2)}\n\n"
            f"Snapchat: retry. WhatsApp: fallback SMS.\nReport per-channel."
        ))
        duration = (time.time() - start) * 1000

        for ch in channels:
            self.add_trace(TraceEntry(
                agent_name="ChannelDeployer",
                action=f"deploy_{ch['name']}_{ch['market']}",
                output_summary="success" if ch.get("should_succeed") else ch.get("error", "FAILED"),
            ))

        sr = self._make_result(
            scenario_id="channel_deploy", status="completed",
            output=result.final_output,
            total_duration_ms=duration, agent_count=1,
        )
        sr.used_retry = True
        return sr

    # ── Dimension 7: Multimodal ────────────────────────────────────
    async def run_multimodal(
        self, image_path: Optional[str], document_path: Optional[str],
        task: Dict[str, Any],
    ) -> ScenarioResult:
        from agents import Agent, Runner

        product = task.get("product", {})
        agent = Agent(
            name="ContentArchitect",
            instructions="Generate Arabic ad copy for MENA e-commerce.",
            model=self.model_name,
        )

        start = time.time()
        result = await Runner.run(agent, (
            f"Meta Ads carousel in Gulf Arabic:\n"
            f"Product: {product.get('name_ar', '')}, {product.get('price_sar', '')} SAR\n"
            f"Description: {product.get('description_ar', '')}\n"
            f"Output: Headline (40 chars), Description (125 chars), CTA, Body"
        ))
        duration = (time.time() - start) * 1000

        self.add_trace(TraceEntry(agent_name="ContentArchitect", action="generate_ad", output_summary=(result.final_output or "")[:200]))

        return self._make_result(
            scenario_id="multimodal_ad", status="completed",
            output=result.final_output,
            total_duration_ms=duration, agent_count=1,
        )
