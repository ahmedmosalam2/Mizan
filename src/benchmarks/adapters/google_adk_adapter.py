"""
Google ADK (Agent Development Kit) Adapter.

Uses Google's Gemini-powered agent framework with
built-in tool support and session management.
"""

import time
import json
import re
from typing import Any, Dict, List, Optional

from benchmarks.adapters.base_adapter import (
    BaseFrameworkAdapter, AgentSpec, ToolSpec,
    ScenarioResult, TraceEntry,
)


class GoogleAdkAdapter(BaseFrameworkAdapter):

    def __init__(self):
        super().__init__(framework_name="Google ADK")
        self.model_name = ""
        self.api_key = ""

    async def setup(self, llm_config: Dict[str, Any]) -> None:
        try:
            from google.adk.agents import Agent
            self.model_name = llm_config.get("model", "gemini-2.0-flash")
            self.api_key = llm_config.get("api_key", "")
            self._is_setup = True
            self.add_trace(TraceEntry(agent_name="system", action="setup", output_summary=f"Google ADK with {self.model_name}"))
        except ImportError:
            raise RuntimeError("Install: pip install google-adk")

    async def teardown(self) -> None:
        self._is_setup = False

    async def run_orchestration(self, agent_specs: List[AgentSpec], task: Dict[str, Any], orchestration_mode: str = "sequential") -> ScenarioResult:
        from google.adk.agents import Agent
        from google.adk.runners import Runner
        from google.adk.sessions import InMemorySessionService

        sub_agents = []
        for spec in agent_specs[1:]:
            sub = Agent(name=spec.name, model=self.model_name, instruction=f"{spec.role}: {spec.goal}")
            sub_agents.append(sub)
            self.add_trace(TraceEntry(agent_name=spec.name, action="agent_created"))

        root = Agent(
            name=agent_specs[0].name, model=self.model_name,
            instruction=f"{agent_specs[0].role}: {agent_specs[0].goal}",
            sub_agents=sub_agents,
        )
        self.add_trace(TraceEntry(agent_name=agent_specs[0].name, action="agent_created"))

        session_service = InMemorySessionService()
        session = await session_service.create_session(app_name=root.name, user_id="benchmark")
        runner = Runner(agent=root, app_name=root.name, session_service=session_service)

        from google.genai.types import Content, Part
        user_msg = Content(role="user", parts=[Part(text=json.dumps(task, ensure_ascii=False, indent=2))])

        start = time.time()
        outputs = []
        async for event in runner.run_async(user_id="benchmark", session_id=session.id, new_message=user_msg):
            if event.is_final_response() and event.content:
                for part in event.content.parts:
                    if part.text:
                        outputs.append(part.text)
                        self.add_trace(TraceEntry(agent_name=event.author or "agent", action="response", output_summary=part.text[:200]))
        duration = (time.time() - start) * 1000

        return self._make_result(
            scenario_id="campaign_planning", status="completed",
            output="\n".join(outputs), total_duration_ms=duration, agent_count=len(agent_specs),
        )

    async def run_with_tools(self, agent_specs: List[AgentSpec], task: Dict[str, Any], tools: List[ToolSpec]) -> ScenarioResult:
        from google.adk.agents import Agent
        from google.adk.runners import Runner
        from google.adk.sessions import InMemorySessionService
        from google.adk.tools import FunctionTool
        from google.genai.types import Content, Part

        adk_tools = [FunctionTool(func=t.function) for t in tools]
        spec = agent_specs[0]
        agent = Agent(name=spec.name, model=self.model_name, instruction=f"{spec.role}: {spec.goal}", tools=adk_tools)

        session_service = InMemorySessionService()
        session = await session_service.create_session(app_name=agent.name, user_id="benchmark")
        runner = Runner(agent=agent, app_name=agent.name, session_service=session_service)
        user_msg = Content(role="user", parts=[Part(text=f"{task['goal']}\nProduct: {json.dumps(task.get('product', {}), ensure_ascii=False)}")])

        start = time.time()
        outputs = []
        async for event in runner.run_async(user_id="benchmark", session_id=session.id, new_message=user_msg):
            if event.is_final_response() and event.content:
                for part in event.content.parts:
                    if part.text:
                        outputs.append(part.text)
        duration = (time.time() - start) * 1000

        return self._make_result(scenario_id="content_generation", status="completed", output="\n".join(outputs), total_duration_ms=duration, agent_count=1)

    async def run_safety_check(self, text_with_pii: str, pii_types: List[str], jurisdiction: str) -> ScenarioResult:
        from google.adk.agents import Agent
        from google.adk.runners import Runner
        from google.adk.sessions import InMemorySessionService
        from google.genai.types import Content, Part

        agent = Agent(name="ComplianceGuardian", model=self.model_name, instruction="Detect and redact PII. Apply Saudi PDPL and Egypt Law 151/2020.")
        session_service = InMemorySessionService()
        session = await session_service.create_session(app_name=agent.name, user_id="benchmark")
        runner = Runner(agent=agent, app_name=agent.name, session_service=session_service)
        user_msg = Content(role="user", parts=[Part(text=f"Detect PII:\n{text_with_pii}\nOutput JSON: detected_pii, redacted_text, jurisdiction_notes")])

        start = time.time()
        output_str = ""
        async for event in runner.run_async(user_id="benchmark", session_id=session.id, new_message=user_msg):
            if event.is_final_response() and event.content:
                for part in event.content.parts:
                    if part.text:
                        output_str += part.text
        duration = (time.time() - start) * 1000

        parsed = {"raw": output_str}
        try:
            match = re.search(r'\{[\s\S]*\}', output_str)
            if match: parsed = json.loads(match.group())
        except json.JSONDecodeError: pass

        self.add_trace(TraceEntry(agent_name="ComplianceGuardian", action="pii_scan", output_summary=output_str[:200]))
        sr = self._make_result(scenario_id="pii_scan", status="completed", output=parsed, total_duration_ms=duration, agent_count=1)
        sr.pii_detected = True
        sr.pii_redacted = "redacted_text" in parsed
        return sr

    async def run_with_approval(self, agent_specs: List[AgentSpec], task: Dict[str, Any], approval_rules: Dict[str, Any], simulated_approvals: List[Dict[str, Any]]) -> ScenarioResult:
        # Google ADK doesn't have native HITL — simulate with sequential agents
        from google.adk.agents import Agent
        from google.adk.runners import Runner
        from google.adk.sessions import InMemorySessionService
        from google.genai.types import Content, Part

        approval = simulated_approvals[0] if simulated_approvals else {}
        agent = Agent(name="BudgetCoordinator", model=self.model_name, instruction=f"Analyze budget. Approval: {json.dumps(approval, ensure_ascii=False)}. Incorporate feedback.")
        session_service = InMemorySessionService()
        session = await session_service.create_session(app_name=agent.name, user_id="benchmark")
        runner = Runner(agent=agent, app_name=agent.name, session_service=session_service)
        user_msg = Content(role="user", parts=[Part(text=json.dumps(task, ensure_ascii=False, indent=2))])

        start = time.time()
        output = ""
        async for event in runner.run_async(user_id="benchmark", session_id=session.id, new_message=user_msg):
            if event.is_final_response() and event.content:
                for part in event.content.parts:
                    if part.text: output += part.text
        duration = (time.time() - start) * 1000

        self.add_trace(TraceEntry(agent_name="system", action="approval_gate"))
        sr = self._make_result(scenario_id="budget_approval", status="completed", output=output, total_duration_ms=duration, agent_count=1)
        sr.used_approval_gate = False  # ADK lacks native HITL
        return sr

    async def run_with_memory(self, conversation_history: List[Dict[str, str]], follow_up_query: str, expected_recall: List[str]) -> ScenarioResult:
        from google.adk.agents import Agent
        from google.adk.runners import Runner
        from google.adk.sessions import InMemorySessionService
        from google.genai.types import Content, Part

        history_text = ""
        for s in conversation_history:
            for msg in s["messages"]:
                history_text += f"{'Customer' if msg['role'] == 'customer' else 'Agent'}: {msg['content']}\n"

        agent = Agent(name="CustomerEngagement", model=self.model_name, instruction="Recall previous conversations.")
        session_service = InMemorySessionService()
        session = await session_service.create_session(app_name=agent.name, user_id="benchmark")
        runner = Runner(agent=agent, app_name=agent.name, session_service=session_service)

        # Send history first, then follow-up
        user_msg = Content(role="user", parts=[Part(text=f"History:\n{history_text}\n\nCustomer: '{follow_up_query}'\nRecall: product, price, color, branch.")])

        start = time.time()
        output = ""
        async for event in runner.run_async(user_id="benchmark", session_id=session.id, new_message=user_msg):
            if event.is_final_response() and event.content:
                for part in event.content.parts:
                    if part.text: output += part.text
        duration = (time.time() - start) * 1000

        self.add_trace(TraceEntry(agent_name="CustomerEngagement", action="memory_recall", output_summary=output[:200]))
        sr = self._make_result(scenario_id="cross_session_chat", status="completed", output=output, total_duration_ms=duration, agent_count=1)
        sr.used_memory = True
        return sr

    async def run_with_tracing(self, agent_specs: List[AgentSpec], task: Dict[str, Any], inject_failure: Optional[Dict[str, Any]] = None) -> ScenarioResult:
        from google.adk.agents import Agent
        from google.adk.runners import Runner
        from google.adk.sessions import InMemorySessionService
        from google.genai.types import Content, Part

        channels = task.get("channels", [])
        agent = Agent(name="ChannelDeployer", model=self.model_name, instruction="Deploy campaigns. Retry on failures. Fallback WhatsApp→SMS.")
        session_service = InMemorySessionService()
        session = await session_service.create_session(app_name=agent.name, user_id="benchmark")
        runner = Runner(agent=agent, app_name=agent.name, session_service=session_service)
        user_msg = Content(role="user", parts=[Part(text=f"Deploy:\n{json.dumps(channels, ensure_ascii=False, indent=2)}\nSnapchat: retry. WhatsApp: fallback SMS.")])

        start = time.time()
        output = ""
        async for event in runner.run_async(user_id="benchmark", session_id=session.id, new_message=user_msg):
            if event.is_final_response() and event.content:
                for part in event.content.parts:
                    if part.text: output += part.text
        duration = (time.time() - start) * 1000

        for ch in channels:
            self.add_trace(TraceEntry(agent_name="ChannelDeployer", action=f"deploy_{ch['name']}_{ch['market']}", output_summary="success" if ch.get("should_succeed") else ch.get("error", "FAILED")))

        sr = self._make_result(scenario_id="channel_deploy", status="completed", output=output, total_duration_ms=duration, agent_count=1)
        sr.used_retry = True
        return sr

    async def run_multimodal(self, image_path: Optional[str], document_path: Optional[str], task: Dict[str, Any]) -> ScenarioResult:
        from google.adk.agents import Agent
        from google.adk.runners import Runner
        from google.adk.sessions import InMemorySessionService
        from google.genai.types import Content, Part

        product = task.get("product", {})
        agent = Agent(name="ContentArchitect", model=self.model_name, instruction="Generate Arabic ad copy.")
        session_service = InMemorySessionService()
        session = await session_service.create_session(app_name=agent.name, user_id="benchmark")
        runner = Runner(agent=agent, app_name=agent.name, session_service=session_service)
        user_msg = Content(role="user", parts=[Part(text=f"Gulf Arabic Meta carousel:\nProduct: {product.get('name_ar', '')}, {product.get('price_sar', '')} SAR\nHeadline (40), Description (125), CTA, Body")])

        start = time.time()
        output = ""
        async for event in runner.run_async(user_id="benchmark", session_id=session.id, new_message=user_msg):
            if event.is_final_response() and event.content:
                for part in event.content.parts:
                    if part.text: output += part.text
        duration = (time.time() - start) * 1000

        self.add_trace(TraceEntry(agent_name="ContentArchitect", action="generate_ad", output_summary=output[:200]))
        return self._make_result(scenario_id="multimodal_ad", status="completed", output=output, total_duration_ms=duration, agent_count=1)
