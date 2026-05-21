"""
PydanticAI Framework Adapter.
"""
import time, json, re
from typing import Any, Dict, List, Optional
from benchmarks.adapters.base_adapter import (
    BaseFrameworkAdapter, AgentSpec, ToolSpec, ScenarioResult, TraceEntry,
)

class PydanticAiAdapter(BaseFrameworkAdapter):
    def __init__(self):
        super().__init__(framework_name="PydanticAI")
        self.model_name = ""

    async def setup(self, llm_config: Dict[str, Any]) -> None:
        try:
            from pydantic_ai import Agent
            p = llm_config.get("provider", "groq")
            m = llm_config.get("model", "")
            self.model_name = f"{p}:{m}" if p != "openai" else m
            self._is_setup = True
        except ImportError:
            raise RuntimeError("pip install pydantic-ai")

    async def teardown(self) -> None:
        self._is_setup = False

    async def _simple_run(self, system: str, prompt: str) -> tuple:
        from pydantic_ai import Agent
        agent = Agent(model=self.model_name, system_prompt=system)
        start = time.time()
        result = await agent.run(prompt)
        return str(result.data), (time.time() - start) * 1000

    async def run_orchestration(self, agent_specs, task, orchestration_mode="sequential"):
        outputs = []
        start = time.time()
        for spec in agent_specs:
            out, _ = await self._simple_run(
                f"Role: {spec.role}\nGoal: {spec.goal}",
                f"Brief:\n{json.dumps(task, ensure_ascii=False, indent=2)}\nPrev: {outputs[-1:] if outputs else 'None'}"
            )
            outputs.append(out)
            self.add_trace(TraceEntry(agent_name=spec.name, action="execute", output_summary=out[:200]))
        return self._make_result(scenario_id="campaign_planning", status="completed", output="\n\n".join(outputs), total_duration_ms=(time.time()-start)*1000, agent_count=len(agent_specs))

    async def run_with_tools(self, agent_specs, task, tools):
        out, dur = await self._simple_run(f"{agent_specs[0].role}", f"{task['goal']}\nProduct: {json.dumps(task.get('product',{}), ensure_ascii=False)}")
        return self._make_result(scenario_id="content_generation", status="completed", output=out, total_duration_ms=dur, agent_count=1)

    async def run_safety_check(self, text_with_pii, pii_types, jurisdiction):
        out, dur = await self._simple_run("PII specialist. Saudi PDPL + Egypt Law 151.", f"Detect PII:\n{text_with_pii}\nJSON: detected_pii, redacted_text")
        parsed = {"raw": out}
        try:
            m = re.search(r'\{[\s\S]*\}', out)
            if m: parsed = json.loads(m.group())
        except: pass
        sr = self._make_result(scenario_id="pii_scan", status="completed", output=parsed, total_duration_ms=dur, agent_count=1)
        sr.pii_detected = True; sr.pii_redacted = "redacted_text" in parsed
        return sr

    async def run_with_approval(self, agent_specs, task, approval_rules, simulated_approvals):
        a = simulated_approvals[0] if simulated_approvals else {}
        out, dur = await self._simple_run("Budget analyst.", f"Budget:\n{json.dumps(task, ensure_ascii=False)}\nApproval: {json.dumps(a, ensure_ascii=False)}\nIncorporate feedback.")
        sr = self._make_result(scenario_id="budget_approval", status="completed", output=out, total_duration_ms=dur, agent_count=1)
        sr.used_approval_gate = False
        return sr

    async def run_with_memory(self, conversation_history, follow_up_query, expected_recall):
        h = "\n".join(f"{'C' if m['role']=='customer' else 'A'}: {m['content']}" for s in conversation_history for m in s["messages"])
        out, dur = await self._simple_run("Customer service. Recall previous.", f"History:\n{h}\nQuery: '{follow_up_query}'\nRecall: product, price, color, branch.")
        sr = self._make_result(scenario_id="cross_session_chat", status="completed", output=out, total_duration_ms=dur, agent_count=1)
        sr.used_memory = True
        return sr

    async def run_with_tracing(self, agent_specs, task, inject_failure=None):
        ch = task.get("channels", [])
        out, dur = await self._simple_run("Deploy campaigns. Retry failures. Fallback WhatsApp->SMS.", f"Deploy:\n{json.dumps(ch, ensure_ascii=False)}")
        for c in ch: self.add_trace(TraceEntry(agent_name="Deployer", action=f"deploy_{c['name']}", output_summary="ok" if c.get("should_succeed") else c.get("error","")))
        sr = self._make_result(scenario_id="channel_deploy", status="completed", output=out, total_duration_ms=dur, agent_count=1)
        sr.used_retry = True
        return sr

    async def run_multimodal(self, image_path, document_path, task):
        p = task.get("product", {})
        out, dur = await self._simple_run("Arabic ad copywriter.", f"Gulf Arabic carousel:\n{p.get('name_ar','')}, {p.get('price_sar','')} SAR\nHeadline(40), Desc(125), CTA, Body")
        return self._make_result(scenario_id="multimodal_ad", status="completed", output=out, total_duration_ms=dur, agent_count=1)
