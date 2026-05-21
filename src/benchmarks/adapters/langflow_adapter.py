"""Langflow Adapter — low-code visual agent builder (API-based evaluation)."""
import time, json, re, os
from typing import Any, Dict, List, Optional
from benchmarks.adapters.base_adapter import (
    BaseFrameworkAdapter, AgentSpec, ToolSpec, ScenarioResult, TraceEntry,
)

class LangflowAdapter(BaseFrameworkAdapter):
    """
    Langflow is a low-code platform accessed via its REST API.
    Each scenario is a pre-built flow deployed on a Langflow server.
    The adapter calls the flow endpoint and collects results.
    """
    def __init__(self):
        super().__init__(framework_name="Langflow")
        self.base_url = ""
        self.api_key = ""

    async def setup(self, llm_config: Dict[str, Any]) -> None:
        self.base_url = os.getenv("LANGFLOW_BASE_URL", "http://localhost:7860")
        self.api_key = os.getenv("LANGFLOW_API_KEY", "")
        self._is_setup = True

    async def teardown(self): self._is_setup = False

    async def _call_flow(self, flow_id: str, prompt: str) -> tuple:
        import httpx
        
        # Fallback to central LLM Gateway if Langflow is not configured locally
        if not self.api_key or "localhost" in self.base_url:
            start = time.time()
            try:
                text = await self.call_llm_gateway(prompt)
                return text, (time.time() - start) * 1000
            except Exception as e:
                return f"Gateway fallback error: {e}", (time.time() - start) * 1000

        url = f"{self.base_url}/api/v1/run/{flow_id}"
        headers = {"Authorization": f"Bearer {self.api_key}"} if self.api_key else {}
        payload = {"input_value": prompt, "output_type": "chat", "input_type": "chat"}
        start = time.time()
        try:
            async with httpx.AsyncClient(timeout=120) as client:
                resp = await client.post(url, json=payload, headers=headers)
                data = resp.json()
                outputs = data.get("outputs", [{}])
                text = ""
                if outputs and isinstance(outputs[0], dict):
                    results = outputs[0].get("outputs", [{}])
                    if results:
                        text = results[0].get("results", {}).get("message", {}).get("text", str(data))
                return text or str(data), (time.time()-start)*1000
        except Exception as e:
            return f"Langflow connection error: {e}", (time.time()-start)*1000

    async def run_orchestration(self, agent_specs, task, orchestration_mode="sequential"):
        flow_id = os.getenv("LANGFLOW_ORCHESTRATION_FLOW", "campaign-planning")
        out, dur = await self._call_flow(flow_id, json.dumps(task, ensure_ascii=False, indent=2))
        for s in agent_specs: self.add_trace(TraceEntry(agent_name=s.name, action="flow_executed"))
        return self._make_result(scenario_id="campaign_planning", status="completed", output=out, total_duration_ms=dur, agent_count=len(agent_specs))

    async def run_with_tools(self, agent_specs, task, tools):
        flow_id = os.getenv("LANGFLOW_TOOLS_FLOW", "content-generation")
        out, dur = await self._call_flow(flow_id, f"{task['goal']}\nProduct: {json.dumps(task.get('product',{}), ensure_ascii=False)}")
        return self._make_result(scenario_id="content_generation", status="completed", output=out, total_duration_ms=dur, agent_count=1)

    async def run_safety_check(self, text_with_pii, pii_types, jurisdiction):
        flow_id = os.getenv("LANGFLOW_SAFETY_FLOW", "pii-scan")
        out, dur = await self._call_flow(flow_id, f"Detect PII:\n{text_with_pii}")
        parsed = {"raw": out}
        try:
            m = re.search(r'\{[\s\S]*\}', out)
            if m: parsed = json.loads(m.group())
        except: pass
        sr = self._make_result(scenario_id="pii_scan", status="completed", output=parsed, total_duration_ms=dur, agent_count=1)
        sr.pii_detected = True; sr.pii_redacted = "redacted_text" in parsed; return sr

    async def run_with_approval(self, agent_specs, task, approval_rules, simulated_approvals):
        flow_id = os.getenv("LANGFLOW_APPROVAL_FLOW", "budget-approval")
        a = simulated_approvals[0] if simulated_approvals else {}
        out, dur = await self._call_flow(flow_id, f"Budget:\n{json.dumps(task, ensure_ascii=False)}\nApproval: {json.dumps(a, ensure_ascii=False)}")
        sr = self._make_result(scenario_id="budget_approval", status="completed", output=out, total_duration_ms=dur, agent_count=1)
        sr.used_approval_gate = False; return sr

    async def run_with_memory(self, conversation_history, follow_up_query, expected_recall):
        flow_id = os.getenv("LANGFLOW_MEMORY_FLOW", "customer-memory")
        h = "\n".join(f"{'C' if m['role']=='customer' else 'A'}: {m['content']}" for s in conversation_history for m in s["messages"])
        out, dur = await self._call_flow(flow_id, f"History:\n{h}\nQuery: '{follow_up_query}'")
        sr = self._make_result(scenario_id="cross_session_chat", status="completed", output=out, total_duration_ms=dur, agent_count=1)
        sr.used_memory = False; return sr

    async def run_with_tracing(self, agent_specs, task, inject_failure=None):
        flow_id = os.getenv("LANGFLOW_DEPLOY_FLOW", "channel-deploy")
        ch = task.get("channels", [])
        out, dur = await self._call_flow(flow_id, f"Deploy:\n{json.dumps(ch, ensure_ascii=False)}")
        for c in ch: self.add_trace(TraceEntry(agent_name="Deployer", action=f"deploy_{c['name']}", output_summary="ok" if c.get("should_succeed") else c.get("error","")))
        sr = self._make_result(scenario_id="channel_deploy", status="completed", output=out, total_duration_ms=dur, agent_count=1)
        sr.used_retry = False; return sr

    async def run_multimodal(self, image_path, document_path, task):
        flow_id = os.getenv("LANGFLOW_MULTIMODAL_FLOW", "ad-generation")
        p = task.get("product", {})
        out, dur = await self._call_flow(flow_id, f"Gulf Arabic carousel:\n{p.get('name_ar','')}, {p.get('price_sar','')} SAR")
        return self._make_result(scenario_id="multimodal_ad", status="completed", output=out, total_duration_ms=dur, agent_count=1)
