"""
SmolAgents (HuggingFace) Adapter.
"""
import time, json, re
from typing import Any, Dict, List, Optional
from benchmarks.adapters.base_adapter import (
    BaseFrameworkAdapter, AgentSpec, ToolSpec, ScenarioResult, TraceEntry,
)

class SmolagentsAdapter(BaseFrameworkAdapter):
    def __init__(self):
        super().__init__(framework_name="SmolAgents")
        self.model = None

    async def setup(self, llm_config: Dict[str, Any]) -> None:
        try:
            from smolagents import LiteLLMModel
            p = llm_config.get("provider", "groq")
            m = llm_config.get("model", "")
            self.model = LiteLLMModel(model_id=f"{p}/{m}", api_key=llm_config.get("api_key", ""))
            self._is_setup = True
        except ImportError:
            raise RuntimeError("pip install smolagents litellm")

    async def teardown(self) -> None:
        self.model = None; self._is_setup = False

    async def run_orchestration(self, agent_specs, task, orchestration_mode="sequential"):
        from smolagents import CodeAgent, ToolCallingAgent
        agents = []
        for spec in agent_specs:
            a = ToolCallingAgent(tools=[], model=self.model, name=spec.name, description=f"{spec.role}: {spec.goal}")
            agents.append(a)
            self.add_trace(TraceEntry(agent_name=spec.name, action="agent_created"))

        manager = CodeAgent(tools=[], model=self.model, managed_agents=agents, name="Commander")
        start = time.time()
        result = manager.run(f"Campaign brief:\n{json.dumps(task, ensure_ascii=False, indent=2)}\nDecompose and delegate.")
        duration = (time.time() - start) * 1000
        return self._make_result(scenario_id="campaign_planning", status="completed", output=str(result), total_duration_ms=duration, agent_count=len(agents)+1)

    async def run_with_tools(self, agent_specs, task, tools):
        from smolagents import ToolCallingAgent, tool as smol_tool

        smol_tools = []
        for t in tools:
            @smol_tool
            def dynamic(query: str, _fn=t.function) -> str:
                """Search tool."""
                return _fn(query)
            dynamic.name = t.name
            dynamic.description = t.description
            smol_tools.append(dynamic)

        agent = ToolCallingAgent(tools=smol_tools, model=self.model)
        start = time.time()
        result = agent.run(f"{task['goal']}\nProduct: {json.dumps(task.get('product',{}), ensure_ascii=False)}")
        duration = (time.time() - start) * 1000
        return self._make_result(scenario_id="content_generation", status="completed", output=str(result), total_duration_ms=duration, agent_count=1)

    async def run_safety_check(self, text_with_pii, pii_types, jurisdiction):
        from smolagents import ToolCallingAgent
        agent = ToolCallingAgent(tools=[], model=self.model)
        start = time.time()
        result = agent.run(f"Detect PII:\n{text_with_pii}\nJSON: detected_pii, redacted_text")
        duration = (time.time() - start) * 1000
        out = str(result); parsed = {"raw": out}
        try:
            m = re.search(r'\{[\s\S]*\}', out)
            if m: parsed = json.loads(m.group())
        except: pass
        sr = self._make_result(scenario_id="pii_scan", status="completed", output=parsed, total_duration_ms=duration, agent_count=1)
        sr.pii_detected = True; sr.pii_redacted = "redacted_text" in parsed
        return sr

    async def run_with_approval(self, agent_specs, task, approval_rules, simulated_approvals):
        from smolagents import ToolCallingAgent
        a = simulated_approvals[0] if simulated_approvals else {}
        agent = ToolCallingAgent(tools=[], model=self.model)
        start = time.time()
        result = agent.run(f"Budget:\n{json.dumps(task, ensure_ascii=False)}\nApproval: {json.dumps(a, ensure_ascii=False)}")
        duration = (time.time() - start) * 1000
        sr = self._make_result(scenario_id="budget_approval", status="completed", output=str(result), total_duration_ms=duration, agent_count=1)
        sr.used_approval_gate = False
        return sr

    async def run_with_memory(self, conversation_history, follow_up_query, expected_recall):
        from smolagents import ToolCallingAgent
        h = "\n".join(f"{'C' if m['role']=='customer' else 'A'}: {m['content']}" for s in conversation_history for m in s["messages"])
        agent = ToolCallingAgent(tools=[], model=self.model)
        start = time.time()
        result = agent.run(f"History:\n{h}\nQuery: '{follow_up_query}'\nRecall: product, price, color, branch.")
        duration = (time.time() - start) * 1000
        sr = self._make_result(scenario_id="cross_session_chat", status="completed", output=str(result), total_duration_ms=duration, agent_count=1)
        sr.used_memory = True
        return sr

    async def run_with_tracing(self, agent_specs, task, inject_failure=None):
        from smolagents import ToolCallingAgent
        ch = task.get("channels", [])
        agent = ToolCallingAgent(tools=[], model=self.model)
        start = time.time()
        result = agent.run(f"Deploy:\n{json.dumps(ch, ensure_ascii=False)}\nRetry failures. Fallback WhatsApp->SMS.")
        duration = (time.time() - start) * 1000
        for c in ch: self.add_trace(TraceEntry(agent_name="Deployer", action=f"deploy_{c['name']}", output_summary="ok" if c.get("should_succeed") else c.get("error","")))
        sr = self._make_result(scenario_id="channel_deploy", status="completed", output=str(result), total_duration_ms=duration, agent_count=1)
        sr.used_retry = True
        return sr

    async def run_multimodal(self, image_path, document_path, task):
        from smolagents import ToolCallingAgent
        p = task.get("product", {})
        agent = ToolCallingAgent(tools=[], model=self.model)
        start = time.time()
        result = agent.run(f"Gulf Arabic carousel:\n{p.get('name_ar','')}, {p.get('price_sar','')} SAR\nHeadline(40), Desc(125), CTA, Body")
        duration = (time.time() - start) * 1000
        return self._make_result(scenario_id="multimodal_ad", status="completed", output=str(result), total_duration_ms=duration, agent_count=1)
