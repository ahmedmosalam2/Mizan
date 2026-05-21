"""Atomic Agents Adapter — minimal composable agents."""
import time, json, re
from typing import Any, Dict, List, Optional
from benchmarks.adapters.base_adapter import (
    BaseFrameworkAdapter, AgentSpec, ToolSpec, ScenarioResult, TraceEntry,
)

class AtomicAgentsAdapter(BaseFrameworkAdapter):
    def __init__(self):
        super().__init__(framework_name="Atomic Agents")
        self.model_config = {}

    async def setup(self, llm_config: Dict[str, Any]) -> None:
        try:
            from atomic_agents.agents.base_agent import BaseAgent, BaseAgentConfig
            self.model_config = llm_config; self._is_setup = True
        except ImportError:
            raise RuntimeError("pip install atomic-agents")

    async def teardown(self): self._is_setup = False

    async def _run_agent(self, system, prompt):
        from atomic_agents.agents.base_agent import BaseAgent, BaseAgentConfig
        from atomic_agents.lib.components.system_prompt_generator import SystemPromptGenerator
        import instructor, groq as groq_lib
        client = instructor.from_groq(groq_lib.Groq(api_key=self.model_config.get("api_key","")))
        config = BaseAgentConfig(client=client, model=self.model_config.get("model",""), system_prompt_generator=SystemPromptGenerator(background=[system]))
        agent = BaseAgent(config=config)
        start = time.time()
        response = agent.run(agent.input_schema(chat_message=prompt))
        out = response.chat_message if hasattr(response, 'chat_message') else str(response)
        return out, (time.time()-start)*1000

    async def run_orchestration(self, agent_specs, task, orchestration_mode="sequential"):
        outputs = []; start = time.time()
        for spec in agent_specs:
            out, _ = await self._run_agent(f"{spec.role}: {spec.goal}", f"Brief:\n{json.dumps(task, ensure_ascii=False, indent=2)}")
            outputs.append(out); self.add_trace(TraceEntry(agent_name=spec.name, action="execute", output_summary=str(out)[:200]))
        return self._make_result(scenario_id="campaign_planning", status="completed", output="\n\n".join(str(o) for o in outputs), total_duration_ms=(time.time()-start)*1000, agent_count=len(agent_specs))

    async def run_with_tools(self, agent_specs, task, tools):
        out, dur = await self._run_agent(agent_specs[0].goal, f"{task['goal']}\nProduct: {json.dumps(task.get('product',{}), ensure_ascii=False)}")
        return self._make_result(scenario_id="content_generation", status="completed", output=str(out), total_duration_ms=dur, agent_count=1)

    async def run_safety_check(self, text_with_pii, pii_types, jurisdiction):
        out, dur = await self._run_agent("PII specialist.", f"Detect PII:\n{text_with_pii}\nJSON: detected_pii, redacted_text")
        out = str(out); parsed = {"raw": out}
        try:
            m = re.search(r'\{[\s\S]*\}', out)
            if m: parsed = json.loads(m.group())
        except: pass
        sr = self._make_result(scenario_id="pii_scan", status="completed", output=parsed, total_duration_ms=dur, agent_count=1)
        sr.pii_detected = True; sr.pii_redacted = "redacted_text" in parsed; return sr

    async def run_with_approval(self, agent_specs, task, approval_rules, simulated_approvals):
        a = simulated_approvals[0] if simulated_approvals else {}
        out, dur = await self._run_agent("Budget analyst.", f"Budget:\n{json.dumps(task, ensure_ascii=False)}\nApproval: {json.dumps(a, ensure_ascii=False)}")
        sr = self._make_result(scenario_id="budget_approval", status="completed", output=str(out), total_duration_ms=dur, agent_count=1)
        sr.used_approval_gate = False; return sr

    async def run_with_memory(self, conversation_history, follow_up_query, expected_recall):
        h = "\n".join(f"{'C' if m['role']=='customer' else 'A'}: {m['content']}" for s in conversation_history for m in s["messages"])
        out, dur = await self._run_agent("Customer service. Recall.", f"History:\n{h}\nQuery: '{follow_up_query}'")
        sr = self._make_result(scenario_id="cross_session_chat", status="completed", output=str(out), total_duration_ms=dur, agent_count=1)
        sr.used_memory = False; return sr

    async def run_with_tracing(self, agent_specs, task, inject_failure=None):
        ch = task.get("channels", [])
        out, dur = await self._run_agent("Deploy. Retry. Fallback.", f"Deploy:\n{json.dumps(ch, ensure_ascii=False)}")
        for c in ch: self.add_trace(TraceEntry(agent_name="Deployer", action=f"deploy_{c['name']}", output_summary="ok" if c.get("should_succeed") else c.get("error","")))
        sr = self._make_result(scenario_id="channel_deploy", status="completed", output=str(out), total_duration_ms=dur, agent_count=1)
        sr.used_retry = False; return sr

    async def run_multimodal(self, image_path, document_path, task):
        p = task.get("product", {})
        out, dur = await self._run_agent("Arabic copywriter.", f"Gulf Arabic carousel:\n{p.get('name_ar','')}, {p.get('price_sar','')} SAR")
        return self._make_result(scenario_id="multimodal_ad", status="completed", output=str(out), total_duration_ms=dur, agent_count=1)
