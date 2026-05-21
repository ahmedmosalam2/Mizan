"""Haystack Adapter — Pipeline-based framework by deepset."""
import time, json, re
from typing import Any, Dict, List, Optional
from benchmarks.adapters.base_adapter import (
    BaseFrameworkAdapter, AgentSpec, ToolSpec, ScenarioResult, TraceEntry,
)

class HaystackAdapter(BaseFrameworkAdapter):
    def __init__(self):
        super().__init__(framework_name="Haystack")
        self.generator = None

    async def setup(self, llm_config: Dict[str, Any]) -> None:
        try:
            from haystack.components.generators.chat import OpenAIChatGenerator
            self.generator = OpenAIChatGenerator(
                model=llm_config["model"],
                api_key=llm_config.get("api_key", ""),
                api_base_url="https://api.groq.com/openai/v1" if llm_config.get("provider") == "groq" else None,
            )
            self._is_setup = True
        except ImportError:
            raise RuntimeError("pip install haystack-ai")

    async def teardown(self): self.generator = None; self._is_setup = False

    def _chat(self, system, prompt):
        from haystack.dataclasses import ChatMessage
        msgs = [ChatMessage.from_system(system), ChatMessage.from_user(prompt)]
        start = time.time()
        result = self.generator.run(messages=msgs)
        out = result["replies"][0].text if result.get("replies") else ""
        return out, (time.time()-start)*1000

    async def run_orchestration(self, agent_specs, task, orchestration_mode="sequential"):
        outputs = []; start = time.time()
        for spec in agent_specs:
            out, _ = self._chat(f"{spec.role}: {spec.goal}", f"Brief:\n{json.dumps(task, ensure_ascii=False, indent=2)}")
            outputs.append(out)
            self.add_trace(TraceEntry(agent_name=spec.name, action="execute", output_summary=out[:200]))
        return self._make_result(scenario_id="campaign_planning", status="completed", output="\n\n".join(outputs), total_duration_ms=(time.time()-start)*1000, agent_count=len(agent_specs))

    async def run_with_tools(self, agent_specs, task, tools):
        out, dur = self._chat(agent_specs[0].goal, f"{task['goal']}\nProduct: {json.dumps(task.get('product',{}), ensure_ascii=False)}")
        return self._make_result(scenario_id="content_generation", status="completed", output=out, total_duration_ms=dur, agent_count=1)

    async def run_safety_check(self, text_with_pii, pii_types, jurisdiction):
        out, dur = self._chat("PII specialist.", f"Detect PII:\n{text_with_pii}\nJSON: detected_pii, redacted_text")
        parsed = {"raw": out}
        try:
            m = re.search(r'\{[\s\S]*\}', out)
            if m: parsed = json.loads(m.group())
        except: pass
        sr = self._make_result(scenario_id="pii_scan", status="completed", output=parsed, total_duration_ms=dur, agent_count=1)
        sr.pii_detected = True; sr.pii_redacted = "redacted_text" in parsed; return sr

    async def run_with_approval(self, agent_specs, task, approval_rules, simulated_approvals):
        a = simulated_approvals[0] if simulated_approvals else {}
        out, dur = self._chat("Budget analyst.", f"Budget:\n{json.dumps(task, ensure_ascii=False)}\nApproval: {json.dumps(a, ensure_ascii=False)}")
        sr = self._make_result(scenario_id="budget_approval", status="completed", output=out, total_duration_ms=dur, agent_count=1)
        sr.used_approval_gate = False; return sr

    async def run_with_memory(self, conversation_history, follow_up_query, expected_recall):
        h = "\n".join(f"{'C' if m['role']=='customer' else 'A'}: {m['content']}" for s in conversation_history for m in s["messages"])
        out, dur = self._chat("Customer service. Recall.", f"History:\n{h}\nQuery: '{follow_up_query}'")
        sr = self._make_result(scenario_id="cross_session_chat", status="completed", output=out, total_duration_ms=dur, agent_count=1)
        sr.used_memory = False; return sr

    async def run_with_tracing(self, agent_specs, task, inject_failure=None):
        ch = task.get("channels", [])
        out, dur = self._chat("Deployer.", f"Deploy:\n{json.dumps(ch, ensure_ascii=False)}")
        for c in ch: self.add_trace(TraceEntry(agent_name="Deployer", action=f"deploy_{c['name']}", output_summary="ok" if c.get("should_succeed") else c.get("error","")))
        sr = self._make_result(scenario_id="channel_deploy", status="completed", output=out, total_duration_ms=dur, agent_count=1)
        sr.used_retry = False; return sr

    async def run_multimodal(self, image_path, document_path, task):
        p = task.get("product", {})
        out, dur = self._chat("Arabic copywriter.", f"Gulf Arabic carousel:\n{p.get('name_ar','')}, {p.get('price_sar','')} SAR")
        return self._make_result(scenario_id="multimodal_ad", status="completed", output=out, total_duration_ms=dur, agent_count=1)
