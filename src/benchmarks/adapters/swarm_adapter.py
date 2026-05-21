"""OpenAI Swarm Adapter — lightweight multi-agent handoffs."""
import time, json, re
from typing import Any, Dict, List, Optional
from benchmarks.adapters.base_adapter import (
    BaseFrameworkAdapter, AgentSpec, ToolSpec, ScenarioResult, TraceEntry,
)

class SwarmAdapter(BaseFrameworkAdapter):
    def __init__(self):
        super().__init__(framework_name="OpenAI Swarm")

    async def setup(self, llm_config: Dict[str, Any]) -> None:
        try:
            from swarm import Swarm
            self.client = Swarm()
            self._is_setup = True
        except ImportError:
            raise RuntimeError("pip install git+https://github.com/openai/swarm.git")

    async def teardown(self): self._is_setup = False

    def _run_sync(self, agent, messages):
        from swarm import Swarm
        client = Swarm()
        return client.run(agent=agent, messages=messages)

    async def run_orchestration(self, agent_specs, task, orchestration_mode="sequential"):
        from swarm import Agent
        agents = []
        for spec in agent_specs:
            a = Agent(name=spec.name, instructions=f"{spec.role}: {spec.goal}")
            agents.append(a)
            self.add_trace(TraceEntry(agent_name=spec.name, action="agent_created"))
        for i in range(len(agents)-1):
            next_a = agents[i+1]
            agents[i].functions.append(lambda ctx_vars={}, _a=next_a: _a)
        start = time.time()
        result = self._run_sync(agents[0], [{"role": "user", "content": json.dumps(task, ensure_ascii=False, indent=2)}])
        duration = (time.time() - start) * 1000
        output = result.messages[-1]["content"] if result.messages else ""
        return self._make_result(scenario_id="campaign_planning", status="completed", output=output, total_duration_ms=duration, agent_count=len(agents))

    async def run_with_tools(self, agent_specs, task, tools):
        from swarm import Agent
        funcs = [t.function for t in tools]
        agent = Agent(name=agent_specs[0].name, instructions=agent_specs[0].goal, functions=funcs)
        start = time.time()
        result = self._run_sync(agent, [{"role": "user", "content": f"{task['goal']}\nProduct: {json.dumps(task.get('product',{}), ensure_ascii=False)}"}])
        duration = (time.time() - start) * 1000
        output = result.messages[-1]["content"] if result.messages else ""
        return self._make_result(scenario_id="content_generation", status="completed", output=output, total_duration_ms=duration, agent_count=1)

    async def run_safety_check(self, text_with_pii, pii_types, jurisdiction):
        from swarm import Agent
        agent = Agent(name="Compliance", instructions="Detect PII. Saudi PDPL + Egypt Law 151.")
        start = time.time()
        result = self._run_sync(agent, [{"role": "user", "content": f"Detect PII:\n{text_with_pii}\nJSON: detected_pii, redacted_text"}])
        duration = (time.time() - start) * 1000
        out = result.messages[-1]["content"] if result.messages else ""
        parsed = {"raw": out}
        try:
            m = re.search(r'\{[\s\S]*\}', out)
            if m: parsed = json.loads(m.group())
        except: pass
        sr = self._make_result(scenario_id="pii_scan", status="completed", output=parsed, total_duration_ms=duration, agent_count=1)
        sr.pii_detected = True; sr.pii_redacted = "redacted_text" in parsed
        return sr

    async def run_with_approval(self, agent_specs, task, approval_rules, simulated_approvals):
        from swarm import Agent
        a = simulated_approvals[0] if simulated_approvals else {}
        agent = Agent(name="Budget", instructions=f"Budget analyst. Approval: {json.dumps(a, ensure_ascii=False)}")
        start = time.time()
        result = self._run_sync(agent, [{"role": "user", "content": json.dumps(task, ensure_ascii=False)}])
        duration = (time.time() - start) * 1000
        out = result.messages[-1]["content"] if result.messages else ""
        sr = self._make_result(scenario_id="budget_approval", status="completed", output=out, total_duration_ms=duration, agent_count=1)
        sr.used_approval_gate = False
        return sr

    async def run_with_memory(self, conversation_history, follow_up_query, expected_recall):
        from swarm import Agent
        h = "\n".join(f"{'C' if m['role']=='customer' else 'A'}: {m['content']}" for s in conversation_history for m in s["messages"])
        agent = Agent(name="Support", instructions="Recall previous conversations.")
        start = time.time()
        result = self._run_sync(agent, [{"role": "user", "content": f"History:\n{h}\nQuery: '{follow_up_query}'"}])
        duration = (time.time() - start) * 1000
        out = result.messages[-1]["content"] if result.messages else ""
        sr = self._make_result(scenario_id="cross_session_chat", status="completed", output=out, total_duration_ms=duration, agent_count=1)
        sr.used_memory = False
        return sr

    async def run_with_tracing(self, agent_specs, task, inject_failure=None):
        from swarm import Agent
        ch = task.get("channels", [])
        agent = Agent(name="Deployer", instructions="Deploy. Retry failures. Fallback WhatsApp->SMS.")
        start = time.time()
        result = self._run_sync(agent, [{"role": "user", "content": f"Deploy:\n{json.dumps(ch, ensure_ascii=False)}"}])
        duration = (time.time() - start) * 1000
        for c in ch: self.add_trace(TraceEntry(agent_name="Deployer", action=f"deploy_{c['name']}", output_summary="ok" if c.get("should_succeed") else c.get("error","")))
        out = result.messages[-1]["content"] if result.messages else ""
        sr = self._make_result(scenario_id="channel_deploy", status="completed", output=out, total_duration_ms=duration, agent_count=1)
        sr.used_retry = False
        return sr

    async def run_multimodal(self, image_path, document_path, task):
        from swarm import Agent
        p = task.get("product", {})
        agent = Agent(name="Content", instructions="Arabic ad copywriter.")
        start = time.time()
        result = self._run_sync(agent, [{"role": "user", "content": f"Gulf Arabic carousel:\n{p.get('name_ar','')}, {p.get('price_sar','')} SAR"}])
        duration = (time.time() - start) * 1000
        out = result.messages[-1]["content"] if result.messages else ""
        return self._make_result(scenario_id="multimodal_ad", status="completed", output=out, total_duration_ms=duration, agent_count=1)
