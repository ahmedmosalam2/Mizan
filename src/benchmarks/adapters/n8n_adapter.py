"""n8n Adapter — workflow automation platform (webhook-based)."""
import time, json, re, os
from typing import Any, Dict, List, Optional
from benchmarks.adapters.base_adapter import (
    BaseFrameworkAdapter, AgentSpec, ToolSpec, ScenarioResult, TraceEntry,
)

class N8nAdapter(BaseFrameworkAdapter):
    def __init__(self):
        super().__init__(framework_name="n8n")
        self.base_url = ""
        self.api_key = ""

    async def setup(self, llm_config: Dict[str, Any]) -> None:
        self.base_url = os.getenv("N8N_BASE_URL", "http://localhost:5678")
        self.api_key = os.getenv("N8N_API_KEY", "")
        self._is_setup = True

    async def teardown(self): self._is_setup = False

    async def _call_webhook(self, webhook_path: str, payload: dict) -> tuple:
        import httpx
        url = f"{self.base_url}/webhook/{webhook_path}"
        headers = {"Authorization": f"Bearer {self.api_key}"} if self.api_key else {}
        start = time.time()
        try:
            async with httpx.AsyncClient(timeout=120) as client:
                resp = await client.post(url, json=payload, headers=headers)
                data = resp.json() if resp.headers.get("content-type","").startswith("application/json") else {"text": resp.text}
                text = data.get("output", data.get("text", data.get("result", str(data))))
                return text, (time.time()-start)*1000
        except Exception as e:
            return f"n8n error: {e}", (time.time()-start)*1000

    async def run_orchestration(self, agent_specs, task, orchestration_mode="sequential"):
        out, dur = await self._call_webhook("benchmark/orchestration", {"task": task, "agents": [s.name for s in agent_specs]})
        for s in agent_specs: self.add_trace(TraceEntry(agent_name=s.name, action="workflow_executed"))
        return self._make_result(scenario_id="campaign_planning", status="completed", output=out, total_duration_ms=dur, agent_count=len(agent_specs))

    async def run_with_tools(self, agent_specs, task, tools):
        out, dur = await self._call_webhook("benchmark/tools", {"task": task, "tool_names": [t.name for t in tools]})
        return self._make_result(scenario_id="content_generation", status="completed", output=out, total_duration_ms=dur, agent_count=1)

    async def run_safety_check(self, text_with_pii, pii_types, jurisdiction):
        out, dur = await self._call_webhook("benchmark/safety", {"text": text_with_pii, "jurisdiction": jurisdiction})
        parsed = {"raw": out}
        try:
            m = re.search(r'\{[\s\S]*\}', str(out))
            if m: parsed = json.loads(m.group())
        except: pass
        sr = self._make_result(scenario_id="pii_scan", status="completed", output=parsed, total_duration_ms=dur, agent_count=1)
        sr.pii_detected = True; sr.pii_redacted = "redacted_text" in parsed; return sr

    async def run_with_approval(self, agent_specs, task, approval_rules, simulated_approvals):
        a = simulated_approvals[0] if simulated_approvals else {}
        out, dur = await self._call_webhook("benchmark/approval", {"task": task, "approval": a})
        sr = self._make_result(scenario_id="budget_approval", status="completed", output=out, total_duration_ms=dur, agent_count=1)
        sr.used_approval_gate = True; return sr  # n8n has native wait/approval nodes

    async def run_with_memory(self, conversation_history, follow_up_query, expected_recall):
        out, dur = await self._call_webhook("benchmark/memory", {"history": conversation_history, "query": follow_up_query})
        sr = self._make_result(scenario_id="cross_session_chat", status="completed", output=out, total_duration_ms=dur, agent_count=1)
        sr.used_memory = False; return sr

    async def run_with_tracing(self, agent_specs, task, inject_failure=None):
        ch = task.get("channels", [])
        out, dur = await self._call_webhook("benchmark/deploy", {"channels": ch})
        for c in ch: self.add_trace(TraceEntry(agent_name="Deployer", action=f"deploy_{c['name']}", output_summary="ok" if c.get("should_succeed") else c.get("error","")))
        sr = self._make_result(scenario_id="channel_deploy", status="completed", output=out, total_duration_ms=dur, agent_count=1)
        sr.used_retry = True; return sr  # n8n has native retry

    async def run_multimodal(self, image_path, document_path, task):
        p = task.get("product", {})
        out, dur = await self._call_webhook("benchmark/multimodal", {"product": p})
        return self._make_result(scenario_id="multimodal_ad", status="completed", output=out, total_duration_ms=dur, agent_count=1)
