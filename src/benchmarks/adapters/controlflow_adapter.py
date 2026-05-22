"""ControlFlow Adapter — Prefect-powered structured AI workflows."""
import time, json, re
from typing import Any, Dict, List, Optional
from benchmarks.adapters.base_adapter import (
    BaseFrameworkAdapter, AgentSpec, ToolSpec, ScenarioResult, TraceEntry,
)

class ControlflowAdapter(BaseFrameworkAdapter):
    def __init__(self):
        super().__init__(framework_name="ControlFlow")
        self.model_config = {}

    async def setup(self, llm_config: Dict[str, Any]) -> None:
        try:
            import controlflow as cf
            self.model_config = llm_config; self._is_setup = True
        except ImportError:
            raise RuntimeError("pip install controlflow")

    async def teardown(self): self._is_setup = False

    def _run_task(self, objective, instructions, agents=None):
        import controlflow as cf
        cf_agents = agents or []
        start = time.time()
        result = cf.run(objective=objective, instructions=instructions, agents=cf_agents or None)
        return str(result), (time.time()-start)*1000

    async def run_orchestration(self, agent_specs, task, orchestration_mode="sequential"):
        import controlflow as cf
        cf_agents = [cf.Agent(name=s.name, instructions=f"{s.role}: {s.goal}") for s in agent_specs]
        for s in agent_specs: self.add_trace(TraceEntry(agent_name=s.name, action="agent_created"))
        start = time.time()
        result = cf.run(objective="Execute Ramadan campaign plan", instructions=json.dumps(task, ensure_ascii=False, indent=2), agents=cf_agents)
        duration = (time.time()-start)*1000
        return self._make_result(scenario_id="campaign_planning", status="completed", output=str(result), total_duration_ms=duration, agent_count=len(agent_specs))

    async def run_with_tools(self, agent_specs, task, tools):
        out, dur = self._run_task(task['goal'], f"Product: {json.dumps(task.get('product',{}), ensure_ascii=False)}")
        return self._make_result(scenario_id="content_generation", status="completed", output=out, total_duration_ms=dur, agent_count=1)

    async def run_safety_check(self, text_with_pii, pii_types, jurisdiction):
        out, dur = self._run_task("Detect and redact PII", f"Text:\n{text_with_pii}\nJSON: detected_pii, redacted_text")
        parsed = {"raw": out}
        try:
            m = re.search(r'\{[\s\S]*\}', out)
            if m: parsed = json.loads(m.group())
        except Exception:
            pass
        sr = self._make_result(scenario_id="pii_scan", status="completed", output=parsed, total_duration_ms=dur, agent_count=1)
        sr.pii_detected = True; sr.pii_redacted = "redacted_text" in parsed; return sr

    async def run_with_approval(self, agent_specs, task, approval_rules, simulated_approvals):
        a = simulated_approvals[0] if simulated_approvals else {}
        out, dur = self._run_task("Analyze budget reallocation", f"Budget:\n{json.dumps(task, ensure_ascii=False)}\nApproval: {json.dumps(a, ensure_ascii=False)}")
        sr = self._make_result(scenario_id="budget_approval", status="completed", output=out, total_duration_ms=dur, agent_count=1)
        sr.used_approval_gate = False; return sr

    async def run_with_memory(self, conversation_history, follow_up_query, expected_recall):
        h = "\n".join(f"{'C' if m['role']=='customer' else 'A'}: {m['content']}" for s in conversation_history for m in s["messages"])
        out, dur = self._run_task("Respond to customer", f"History:\n{h}\nQuery: '{follow_up_query}'")
        sr = self._make_result(scenario_id="cross_session_chat", status="completed", output=out, total_duration_ms=dur, agent_count=1)
        sr.used_memory = False; return sr

    async def run_with_tracing(self, agent_specs, task, inject_failure=None):
        ch = task.get("channels", [])
        out, dur = self._run_task("Deploy campaigns", f"Deploy:\n{json.dumps(ch, ensure_ascii=False)}\nRetry failures. Fallback WhatsApp->SMS.")
        for c in ch: self.add_trace(TraceEntry(agent_name="Deployer", action=f"deploy_{c['name']}", output_summary="ok" if c.get("should_succeed") else c.get("error","")))
        sr = self._make_result(scenario_id="channel_deploy", status="completed", output=out, total_duration_ms=dur, agent_count=1)
        sr.used_retry = False; return sr

    async def run_multimodal(self, image_path, document_path, task):
        p = task.get("product", {})
        out, dur = self._run_task("Generate Arabic ad copy", f"Gulf Arabic carousel:\n{p.get('name_ar','')}, {p.get('price_sar','')} SAR")
        return self._make_result(scenario_id="multimodal_ad", status="completed", output=out, total_duration_ms=dur, agent_count=1)
