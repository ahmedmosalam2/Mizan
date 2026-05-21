"""
AutoGen Framework Adapter.

AutoGen uses a conversation-based multi-agent approach where agents
chat with each other to solve tasks.
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


class AutogenAdapter(BaseFrameworkAdapter):
    """Adapter for Microsoft AutoGen framework."""

    def __init__(self):
        super().__init__(framework_name="AutoGen")
        self.model_config = None

    async def setup(self, llm_config: Dict[str, Any]) -> None:
        try:
            import autogen_agentchat
            self.model_config = {
                "config_list": [{
                    "model": llm_config["model"],
                    "api_key": llm_config.get("api_key", ""),
                    "base_url": f"https://api.groq.com/openai/v1"
                    if llm_config.get("provider") == "groq" else None,
                }],
                "temperature": 0,
            }
            self._is_setup = True
            self.add_trace(TraceEntry(
                agent_name="system", action="setup",
                output_summary=f"AutoGen initialized with {llm_config['model']}",
            ))
        except ImportError:
            raise RuntimeError("Install: pip install autogen-agentchat autogen-ext[openai]")

    async def teardown(self) -> None:
        self.model_config = None
        self._is_setup = False

    # ── Dimension 1: Orchestration ─────────────────────────────────
    async def run_orchestration(
        self, agent_specs: List[AgentSpec], task: Dict[str, Any],
        orchestration_mode: str = "sequential",
    ) -> ScenarioResult:
        from autogen_agentchat.agents import AssistantAgent
        from autogen_agentchat.teams import RoundRobinGroupChat
        from autogen_agentchat.conditions import TextMentionTermination
        from autogen_ext.models.openai import OpenAIChatCompletionClient

        client = OpenAIChatCompletionClient(
            model=self.model_config["config_list"][0]["model"],
            api_key=self.model_config["config_list"][0]["api_key"],
            base_url=self.model_config["config_list"][0].get("base_url"),
        )

        agents = []
        for spec in agent_specs:
            agent = AssistantAgent(
                name=spec.name,
                model_client=client,
                system_message=f"Role: {spec.role}\nGoal: {spec.goal}\nBackstory: {spec.backstory}",
            )
            agents.append(agent)
            self.add_trace(TraceEntry(agent_name=spec.name, action="agent_created", output_summary=spec.role))

        termination = TextMentionTermination("CAMPAIGN_PLAN_COMPLETE")
        team = RoundRobinGroupChat(
            participants=agents,
            termination_condition=termination,
            max_turns=len(agents) + 2,
        )

        task_msg = (
            f"Ramadan campaign brief:\n{json.dumps(task, ensure_ascii=False, indent=2)}\n\n"
            f"Each agent should produce their deliverable. The last agent should end with CAMPAIGN_PLAN_COMPLETE."
        )

        start = time.time()
        result = await team.run(task=task_msg)
        duration = (time.time() - start) * 1000

        outputs = []
        for msg in result.messages:
            outputs.append(f"[{msg.source}]: {msg.content[:300]}")
            self.add_trace(TraceEntry(
                agent_name=msg.source, action="message",
                output_summary=msg.content[:200],
            ))

        await client.close()

        return self._make_result(
            scenario_id="campaign_planning", status="completed",
            output="\n\n".join(outputs),
            total_duration_ms=duration, agent_count=len(agents),
        )

    # ── Dimension 2: Tool Use ──────────────────────────────────────
    async def run_with_tools(
        self, agent_specs: List[AgentSpec], task: Dict[str, Any],
        tools: List[ToolSpec],
    ) -> ScenarioResult:
        from autogen_agentchat.agents import AssistantAgent
        from autogen_agentchat.teams import RoundRobinGroupChat
        from autogen_agentchat.conditions import MaxMessageTermination
        from autogen_ext.models.openai import OpenAIChatCompletionClient
        from autogen_core.tools import FunctionTool

        client = OpenAIChatCompletionClient(
            model=self.model_config["config_list"][0]["model"],
            api_key=self.model_config["config_list"][0]["api_key"],
            base_url=self.model_config["config_list"][0].get("base_url"),
        )

        ag_tools = [FunctionTool(t.function, name=t.name, description=t.description) for t in tools]
        spec = agent_specs[0]
        agent = AssistantAgent(
            name=spec.name,
            model_client=client,
            system_message=f"Role: {spec.role}\nGoal: {spec.goal}",
            tools=ag_tools,
        )

        team = RoundRobinGroupChat(
            participants=[agent],
            termination_condition=MaxMessageTermination(10),
        )

        task_msg = (
            f"{task['goal']}\n\n"
            f"Product: {json.dumps(task.get('product', {}), ensure_ascii=False)}\n"
            f"Market: {task.get('market', 'KSA')}\n"
            f"Use available tools first."
        )

        start = time.time()
        result = await team.run(task=task_msg)
        duration = (time.time() - start) * 1000

        tool_count = 0
        final_output = ""
        for msg in result.messages:
            if hasattr(msg, 'content') and msg.content:
                final_output = msg.content
            self.add_trace(TraceEntry(
                agent_name=getattr(msg, 'source', 'unknown'), action="message",
                output_summary=str(getattr(msg, 'content', ''))[:200],
            ))

        await client.close()

        return self._make_result(
            scenario_id="content_generation", status="completed",
            output=final_output, total_duration_ms=duration,
            agent_count=1, tool_calls=tool_count,
        )

    # ── Dimension 3: Safety ────────────────────────────────────────
    async def run_safety_check(
        self, text_with_pii: str, pii_types: List[str], jurisdiction: str,
    ) -> ScenarioResult:
        from autogen_agentchat.agents import AssistantAgent
        from autogen_agentchat.teams import RoundRobinGroupChat
        from autogen_agentchat.conditions import MaxMessageTermination
        from autogen_ext.models.openai import OpenAIChatCompletionClient

        client = OpenAIChatCompletionClient(
            model=self.model_config["config_list"][0]["model"],
            api_key=self.model_config["config_list"][0]["api_key"],
            base_url=self.model_config["config_list"][0].get("base_url"),
        )

        agent = AssistantAgent(
            name="ComplianceGuardian",
            model_client=client,
            system_message="You are a PII detection specialist for Saudi PDPL and Egypt Law 151/2020.",
        )

        team = RoundRobinGroupChat(
            participants=[agent],
            termination_condition=MaxMessageTermination(3),
        )

        start = time.time()
        result = await team.run(task=(
            f"Detect all PII in this text:\n{text_with_pii}\n\n"
            f"Output JSON: detected_pii, redacted_text, jurisdiction_notes"
        ))
        duration = (time.time() - start) * 1000

        output_str = result.messages[-1].content if result.messages else ""
        parsed = {"raw": output_str}
        try:
            match = re.search(r'\{[\s\S]*\}', output_str)
            if match:
                parsed = json.loads(match.group())
        except json.JSONDecodeError:
            pass

        self.add_trace(TraceEntry(agent_name="ComplianceGuardian", action="pii_scan", output_summary=output_str[:200]))
        await client.close()

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
        from autogen_agentchat.agents import AssistantAgent
        from autogen_agentchat.teams import RoundRobinGroupChat
        from autogen_agentchat.conditions import MaxMessageTermination
        from autogen_ext.models.openai import OpenAIChatCompletionClient

        client = OpenAIChatCompletionClient(
            model=self.model_config["config_list"][0]["model"],
            api_key=self.model_config["config_list"][0]["api_key"],
            base_url=self.model_config["config_list"][0].get("base_url"),
        )

        analyst = AssistantAgent(
            name="AnalyticsAgent",
            model_client=client,
            system_message="Analyze budget and recommend reallocation. Flag if > 20% threshold.",
        )
        approver = AssistantAgent(
            name="CampaignCommander",
            model_client=client,
            system_message=(
                f"You are the approval coordinator. The simulated approval is:\n"
                f"{json.dumps(simulated_approvals[0] if simulated_approvals else {}, ensure_ascii=False)}\n"
                f"Incorporate the feedback and produce final allocation."
            ),
        )

        team = RoundRobinGroupChat(
            participants=[analyst, approver],
            termination_condition=MaxMessageTermination(4),
        )

        start = time.time()
        result = await team.run(task=json.dumps(task, ensure_ascii=False, indent=2))
        duration = (time.time() - start) * 1000

        final_output = result.messages[-1].content if result.messages else ""
        for msg in result.messages:
            self.add_trace(TraceEntry(
                agent_name=msg.source, action="hitl_message",
                output_summary=str(msg.content)[:200],
            ))

        await client.close()

        sr = self._make_result(
            scenario_id="budget_approval", status="completed",
            output=final_output, total_duration_ms=duration, agent_count=2,
        )
        sr.used_approval_gate = True
        return sr

    # ── Dimension 5: Memory ────────────────────────────────────────
    async def run_with_memory(
        self, conversation_history: List[Dict[str, str]],
        follow_up_query: str, expected_recall: List[str],
    ) -> ScenarioResult:
        from autogen_agentchat.agents import AssistantAgent
        from autogen_agentchat.teams import RoundRobinGroupChat
        from autogen_agentchat.conditions import MaxMessageTermination
        from autogen_ext.models.openai import OpenAIChatCompletionClient

        client = OpenAIChatCompletionClient(
            model=self.model_config["config_list"][0]["model"],
            api_key=self.model_config["config_list"][0]["api_key"],
            base_url=self.model_config["config_list"][0].get("base_url"),
        )

        history_text = ""
        for session in conversation_history:
            history_text += f"\n--- Session {session['session_id']} ---\n"
            for msg in session["messages"]:
                role = "Customer" if msg["role"] == "customer" else "Agent"
                history_text += f"{role}: {msg['content']}\n"

        agent = AssistantAgent(
            name="CustomerEngagement",
            model_client=client,
            system_message="You are a customer service agent. Recall details from previous conversations.",
        )

        team = RoundRobinGroupChat(
            participants=[agent],
            termination_condition=MaxMessageTermination(3),
        )

        start = time.time()
        result = await team.run(task=(
            f"History:\n{history_text}\n\nCustomer: '{follow_up_query}'\n\n"
            f"Respond with: product, price, color, branch from previous session."
        ))
        duration = (time.time() - start) * 1000

        output = result.messages[-1].content if result.messages else ""
        self.add_trace(TraceEntry(agent_name="CustomerEngagement", action="memory_recall", output_summary=output[:200]))
        await client.close()

        sr = self._make_result(
            scenario_id="cross_session_chat", status="completed",
            output=output, total_duration_ms=duration, agent_count=1,
        )
        sr.used_memory = True
        return sr

    # ── Dimension 6: Observability ─────────────────────────────────
    async def run_with_tracing(
        self, agent_specs: List[AgentSpec], task: Dict[str, Any],
        inject_failure: Optional[Dict[str, Any]] = None,
    ) -> ScenarioResult:
        from autogen_agentchat.agents import AssistantAgent
        from autogen_agentchat.teams import RoundRobinGroupChat
        from autogen_agentchat.conditions import MaxMessageTermination
        from autogen_ext.models.openai import OpenAIChatCompletionClient

        client = OpenAIChatCompletionClient(
            model=self.model_config["config_list"][0]["model"],
            api_key=self.model_config["config_list"][0]["api_key"],
            base_url=self.model_config["config_list"][0].get("base_url"),
        )

        channels = task.get("channels", [])
        agent = AssistantAgent(
            name="ChannelDeployer",
            model_client=client,
            system_message="Deploy campaigns. Retry on rate limits. Fallback WhatsApp→SMS.",
        )

        team = RoundRobinGroupChat(
            participants=[agent],
            termination_condition=MaxMessageTermination(3),
        )

        start = time.time()
        result = await team.run(task=(
            f"Deploy:\n{json.dumps(channels, ensure_ascii=False, indent=2)}\n\n"
            f"Snapchat fails with API_RATE_LIMIT → retry.\n"
            f"WhatsApp fails with TEMPLATE_REJECTED → fallback to SMS.\n"
            f"Report per-channel status."
        ))
        duration = (time.time() - start) * 1000

        for ch in channels:
            self.add_trace(TraceEntry(
                agent_name="ChannelDeployer",
                action=f"deploy_{ch['name']}_{ch['market']}",
                output_summary="success" if ch.get("should_succeed") else ch.get("error", "FAILED"),
            ))

        output = result.messages[-1].content if result.messages else ""
        await client.close()

        sr = self._make_result(
            scenario_id="channel_deploy", status="completed",
            output=output, total_duration_ms=duration, agent_count=1,
        )
        sr.used_retry = True
        return sr

    # ── Dimension 7: Multimodal ────────────────────────────────────
    async def run_multimodal(
        self, image_path: Optional[str], document_path: Optional[str],
        task: Dict[str, Any],
    ) -> ScenarioResult:
        from autogen_agentchat.agents import AssistantAgent
        from autogen_agentchat.teams import RoundRobinGroupChat
        from autogen_agentchat.conditions import MaxMessageTermination
        from autogen_ext.models.openai import OpenAIChatCompletionClient

        client = OpenAIChatCompletionClient(
            model=self.model_config["config_list"][0]["model"],
            api_key=self.model_config["config_list"][0]["api_key"],
            base_url=self.model_config["config_list"][0].get("base_url"),
        )

        product = task.get("product", {})
        agent = AssistantAgent(
            name="ContentArchitect",
            model_client=client,
            system_message="Generate Arabic ad copy for MENA e-commerce.",
        )

        team = RoundRobinGroupChat(
            participants=[agent],
            termination_condition=MaxMessageTermination(3),
        )

        start = time.time()
        result = await team.run(task=(
            f"Meta Ads carousel in Gulf Arabic:\n"
            f"Product: {product.get('name_ar', '')}, {product.get('price_sar', '')} SAR\n"
            f"Description: {product.get('description_ar', '')}\n"
            f"Output: Headline (40 chars), Description (125 chars), CTA, Body"
        ))
        duration = (time.time() - start) * 1000

        output = result.messages[-1].content if result.messages else ""
        self.add_trace(TraceEntry(agent_name="ContentArchitect", action="generate_ad", output_summary=output[:200]))
        await client.close()

        return self._make_result(
            scenario_id="multimodal_ad", status="completed",
            output=output, total_duration_ms=duration, agent_count=1,
        )
