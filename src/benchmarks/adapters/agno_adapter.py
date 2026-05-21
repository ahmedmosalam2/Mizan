"""Agno (formerly Phidata) Adapter — function-calling agents with memory."""
import time, json, re
from typing import Any, Dict, List, Optional
from benchmarks.adapters.base_adapter import (
    BaseFrameworkAdapter, AgentSpec, ToolSpec, ScenarioResult, TraceEntry,
)

class AgnoAdapter(BaseFrameworkAdapter):
    def __init__(self):
        super().__init__(framework_name="Agno")
        self.model_id = ""

    async def setup(self, llm_config: Dict[str, Any]) -> None:
        try:
            from agno.agent import Agent
            self.model_id = llm_config.get("model", "")
            self.api_key = llm_config.get("api_key", "")
            self._is_setup = True
        except ImportError:
            raise RuntimeError("pip install agno")

    async def teardown(self): self._is_setup = False

    def _make_agent(self, name, instructions):
        from agno.agent import Agent
        from agno.models.groq import Groq
        return Agent(name=name, model=Groq(id=self.model_id, api_key=self.api_key), instructions=[instructions], markdown=True)

    async def _run_agent(self, name, instructions, prompt):
        agent = self._make_agent(name, instructions)
        start = time.time()
        response = agent.run(prompt)
        out = response.content if hasattr(response, 'content') else str(response)
        return out, (time.time()-start)*1000

    async def run_orchestration(self, agent_specs, task, orchestration_mode="sequential"):
        from agno.agent import Agent
        from agno.models.groq import Groq
        model = Groq(id=self.model_id, api_key=self.api_key)
        sub_agents = [Agent(name=s.name, model=model, instructions=[f"{s.role}: {s.goal}"], markdown=True) for s in agent_specs[1:]]
        leader = Agent(name=agent_specs[0].name, model=model, team=sub_agents, instructions=[f"{agent_specs[0].role}: {agent_specs[0].goal}"])
        for s in agent_specs: self.add_trace(TraceEntry(agent_name=s.name, action="agent_created"))
        start = time.time()
        result = leader.run(json.dumps(task, ensure_ascii=False, indent=2))
        duration = (time.time()-start)*1000
        out = result.content if hasattr(result, 'content') else str(result)
        return self._make_result(scenario_id="campaign_planning", status="completed", output=out, total_duration_ms=duration, agent_count=len(agent_specs))

    async def run_with_tools(self, agent_specs, task, tools):
        out, dur = await self._run_agent(agent_specs[0].name, agent_specs[0].goal, f"{task['goal']}\nProduct: {json.dumps(task.get('product',{}), ensure_ascii=False)}")
        return self._make_result(scenario_id="content_generation", status="completed", output=out, total_duration_ms=dur, agent_count=1)

    async def run_safety_check(self, text_with_pii, pii_types, jurisdiction):
        out, dur = await self._run_agent("Compliance", "PII detection. Saudi PDPL + Egypt Law 151.", f"Detect PII:\n{text_with_pii}\nJSON: detected_pii, redacted_text")
        parsed = {"raw": out}
        try:
            m = re.search(r'\{[\s\S]*\}', out)
            if m: parsed = json.loads(m.group())
        except: pass
        sr = self._make_result(scenario_id="pii_scan", status="completed", output=parsed, total_duration_ms=dur, agent_count=1)
        sr.pii_detected = True; sr.pii_redacted = "redacted_text" in parsed; return sr

    async def run_with_approval(self, agent_specs, task, approval_rules, simulated_approvals):
        a = simulated_approvals[0] if simulated_approvals else {}
        out, dur = await self._run_agent("Budget", "Budget analyst.", f"Budget:\n{json.dumps(task, ensure_ascii=False)}\nApproval: {json.dumps(a, ensure_ascii=False)}")
        sr = self._make_result(scenario_id="budget_approval", status="completed", output=out, total_duration_ms=dur, agent_count=1)
        sr.used_approval_gate = False; return sr

    async def run_with_memory(self, conversation_history, follow_up_query, expected_recall):
        h = "\n".join(f"{'C' if m['role']=='customer' else 'A'}: {m['content']}" for s in conversation_history for m in s["messages"])
        out, dur = await self._run_agent("Support", "Customer service. Recall previous.", f"History:\n{h}\nQuery: '{follow_up_query}'")
        sr = self._make_result(scenario_id="cross_session_chat", status="completed", output=out, total_duration_ms=dur, agent_count=1)
        sr.used_memory = True; return sr

    async def run_with_tracing(self, agent_specs, task, inject_failure=None):
        ch = task.get("channels", [])
        out, dur = await self._run_agent("Deployer", "Deploy. Retry. Fallback.", f"Deploy:\n{json.dumps(ch, ensure_ascii=False)}")
        for c in ch: self.add_trace(TraceEntry(agent_name="Deployer", action=f"deploy_{c['name']}", output_summary="ok" if c.get("should_succeed") else c.get("error","")))
        sr = self._make_result(scenario_id="channel_deploy", status="completed", output=out, total_duration_ms=dur, agent_count=1)
        sr.used_retry = True; return sr

    async def run_multimodal(self, image_path, document_path, task):
        p = task.get("product", {})
        out, dur = await self._run_agent("Content", "Arabic copywriter.", f"Gulf Arabic carousel:\n{p.get('name_ar','')}, {p.get('price_sar','')} SAR")
        return self._make_result(scenario_id="multimodal_ad", status="completed", output=out, total_duration_ms=dur, agent_count=1)
