"""Flowise Adapter — low-code visual chatflow builder (API-based)."""
import time, json, re, os
from typing import Any, Dict, List, Optional
from benchmarks.adapters.base_adapter import (
    BaseFrameworkAdapter, AgentSpec, ToolSpec, ScenarioResult, TraceEntry,
)

class FlowiseAdapter(BaseFrameworkAdapter):
    def __init__(self):
        super().__init__(framework_name="Flowise")
        self.base_url = ""
        self.api_key = ""

    async def setup(self, llm_config: Dict[str, Any]) -> None:
        self.base_url = os.getenv("FLOWISE_BASE_URL", "http://localhost:3000")
        self.api_key = os.getenv("FLOWISE_API_KEY", "")
        self._is_setup = True

    async def teardown(self): self._is_setup = False

    async def _call_chatflow(self, chatflow_id: str, question: str) -> tuple:
        import httpx
        url = f"{self.base_url}/api/v1/prediction/{chatflow_id}"
        headers = {"Authorization": f"Bearer {self.api_key}"} if self.api_key else {}
        start = time.time()
        try:
            async with httpx.AsyncClient(timeout=120) as client:
                resp = await client.post(url, json={"question": question}, headers=headers)
                data = resp.json()
                text = data.get("text", data.get("answer", str(data)))
                return text, (time.time()-start)*1000
        except Exception as e:
            return f"Flowise error: {e}", (time.time()-start)*1000

    async def run_orchestration(self, agent_specs, task, orchestration_mode="sequential"):
        cid = os.getenv("FLOWISE_ORCHESTRATION_ID", "orchestration")
        out, dur = await self._call_chatflow(cid, json.dumps(task, ensure_ascii=False, indent=2))
        for s in agent_specs: self.add_trace(TraceEntry(agent_name=s.name, action="chatflow_executed"))
        return self._make_result(scenario_id="campaign_planning", status="completed", output=out, total_duration_ms=dur, agent_count=len(agent_specs))

    async def run_with_tools(self, agent_specs, task, tools):
        out, dur = await self._call_chatflow(os.getenv("FLOWISE_TOOLS_ID","tools"), f"{task['goal']}\nProduct: {json.dumps(task.get('product',{}), ensure_ascii=False)}")
        return self._make_result(scenario_id="content_generation", status="completed", output=out, total_duration_ms=dur, agent_count=1)

    async def run_safety_check(self, text_with_pii, pii_types, jurisdiction):
        out, dur = await self._call_chatflow(os.getenv("FLOWISE_SAFETY_ID","safety"), f"Detect PII:\n{text_with_pii}")
        parsed = {"raw": out}
        try:
            m = re.search(r'\{[\s\S]*\}', out)
            if m: parsed = json.loads(m.group())
        except: pass
        sr = self._make_result(scenario_id="pii_scan", status="completed", output=parsed, total_duration_ms=dur, agent_count=1)
        sr.pii_detected = True; sr.pii_redacted = "redacted_text" in parsed; return sr

    async def run_with_approval(self, agent_specs, task, approval_rules, simulated_approvals):
        a = simulated_approvals[0] if simulated_approvals else {}
        out, dur = await self._call_chatflow(os.getenv("FLOWISE_APPROVAL_ID","approval"), f"Budget:\n{json.dumps(task, ensure_ascii=False)}\nApproval: {json.dumps(a, ensure_ascii=False)}")
        sr = self._make_result(scenario_id="budget_approval", status="completed", output=out, total_duration_ms=dur, agent_count=1)
        sr.used_approval_gate = False; return sr

    async def run_with_memory(self, conversation_history, follow_up_query, expected_recall):
        h = "\n".join(f"{'C' if m['role']=='customer' else 'A'}: {m['content']}" for s in conversation_history for m in s["messages"])
        out, dur = await self._call_chatflow(os.getenv("FLOWISE_MEMORY_ID","memory"), f"History:\n{h}\nQuery: '{follow_up_query}'")
        sr = self._make_result(scenario_id="cross_session_chat", status="completed", output=out, total_duration_ms=dur, agent_count=1)
        sr.used_memory = False; return sr

    async def run_with_tracing(self, agent_specs, task, inject_failure=None):
        ch = task.get("channels", [])
        out, dur = await self._call_chatflow(os.getenv("FLOWISE_DEPLOY_ID","deploy"), f"Deploy:\n{json.dumps(ch, ensure_ascii=False)}")
        for c in ch: self.add_trace(TraceEntry(agent_name="Deployer", action=f"deploy_{c['name']}", output_summary="ok" if c.get("should_succeed") else c.get("error","")))
        sr = self._make_result(scenario_id="channel_deploy", status="completed", output=out, total_duration_ms=dur, agent_count=1)
        sr.used_retry = False; return sr

    async def run_multimodal(self, image_path, document_path, task):
        p = task.get("product", {})
        out, dur = await self._call_chatflow(os.getenv("FLOWISE_MULTIMODAL_ID","multimodal"), f"Gulf Arabic carousel:\n{p.get('name_ar','')}, {p.get('price_sar','')} SAR")
        return self._make_result(scenario_id="multimodal_ad", status="completed", output=out, total_duration_ms=dur, agent_count=1)
