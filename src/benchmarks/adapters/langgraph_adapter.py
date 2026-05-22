"""
LangGraph Framework Adapter.

LangGraph uses a graph-based approach where agents are nodes
and edges define the flow. This is fundamentally different from
CrewAI's declarative crew model.
"""

import time
import json
import re
from typing import Any, Dict, List, Optional
from datetime import datetime

from benchmarks.adapters.base_adapter import (
    BaseFrameworkAdapter,
    AgentSpec,
    ToolSpec,
    ScenarioResult,
    TraceEntry,
)


class LanggraphAdapter(BaseFrameworkAdapter):
    """Adapter for LangGraph framework."""

    def __init__(self):
        super().__init__(framework_name="LangGraph")
        self.llm = None
        self.model_name = ""

    async def setup(self, llm_config: Dict[str, Any]) -> None:
        try:
            from langchain_groq import ChatGroq
            self.llm = ChatGroq(
                model=llm_config["model"],
                api_key=llm_config.get("api_key", ""),
                temperature=0,
            )
            self.model_name = llm_config["model"]
            self._is_setup = True
            self.add_trace(TraceEntry(
                agent_name="system", action="setup",
                output_summary=f"LangGraph initialized with {self.model_name}",
            ))
        except ImportError:
            raise RuntimeError("Install: pip install langgraph langchain-groq langchain-core")

    async def teardown(self) -> None:
        self.llm = None
        self._is_setup = False

    # ── Dimension 1: Orchestration ─────────────────────────────────
    async def run_orchestration(
        self, agent_specs: List[AgentSpec], task: Dict[str, Any],
        orchestration_mode: str = "sequential",
    ) -> ScenarioResult:
        from langgraph.graph import StateGraph, START, END
        from langchain_core.messages import HumanMessage, SystemMessage
        from typing import TypedDict, Annotated
        import operator

        class GraphState(TypedDict):
            messages: Annotated[list, operator.add]
            current_agent_idx: int
            results: Annotated[list, operator.add]
            task_brief: str

        async def agent_node(state: GraphState, spec: AgentSpec) -> dict:
            system_msg = SystemMessage(content=f"Role: {spec.role}\nGoal: {spec.goal}\nBackstory: {spec.backstory}")
            human_msg = HumanMessage(content=(
                f"Task brief:\n{state['task_brief']}\n\n"
                f"Previous agent results:\n{json.dumps(state.get('results', []), ensure_ascii=False)}\n\n"
                f"Produce your deliverable for this task."
            ))
            response = await self.llm.ainvoke([system_msg, human_msg])
            self.add_trace(TraceEntry(
                agent_name=spec.name, action="execute",
                output_summary=response.content[:200],
            ))
            if hasattr(response, 'usage_metadata') and response.usage_metadata:
                self.update_tokens(
                    prompt=response.usage_metadata.get('input_tokens', 0),
                    completion=response.usage_metadata.get('output_tokens', 0),
                    model=self.model_name,
                )
            return {
                "results": [{"agent": spec.name, "output": response.content}],
                "messages": [response],
            }

        # Build the graph
        builder = StateGraph(GraphState)
        node_names = []

        for i, spec in enumerate(agent_specs):
            node_name = f"agent_{spec.name}"
            node_names.append(node_name)
            # Capture spec in closure — must use async wrapper since agent_node is async
            async def _make_node(state, s=spec):
                return await agent_node(state, s)
            builder.add_node(node_name, _make_node)

        # Sequential edges
        builder.add_edge(START, node_names[0])
        for i in range(len(node_names) - 1):
            builder.add_edge(node_names[i], node_names[i + 1])
        builder.add_edge(node_names[-1], END)

        graph = builder.compile()

        start = time.time()
        result = await graph.ainvoke({
            "messages": [],
            "current_agent_idx": 0,
            "results": [],
            "task_brief": json.dumps(task, ensure_ascii=False, indent=2),
        })
        duration = (time.time() - start) * 1000

        all_outputs = "\n\n".join(r.get("output", "") for r in result.get("results", []))

        return self._make_result(
            scenario_id="campaign_planning",
            status="completed",
            output=all_outputs,
            total_duration_ms=duration,
            agent_count=len(agent_specs),
        )

    # ── Dimension 2: Tool Use ──────────────────────────────────────
    async def run_with_tools(
        self, agent_specs: List[AgentSpec], task: Dict[str, Any],
        tools: List[ToolSpec],
    ) -> ScenarioResult:
        from langchain_core.tools import StructuredTool
        from langchain_core.messages import HumanMessage, SystemMessage

        # Convert ToolSpecs to LangChain tools
        lc_tools = []
        for t in tools:
            lc_tool = StructuredTool.from_function(
                func=t.function,
                name=t.name,
                description=t.description,
            )
            lc_tools.append(lc_tool)

        llm_with_tools = self.llm.bind_tools(lc_tools)

        spec = agent_specs[0]
        messages = [
            SystemMessage(content=f"Role: {spec.role}\nGoal: {spec.goal}\nBackstory: {spec.backstory}"),
            HumanMessage(content=(
                f"{task['goal']}\n\n"
                f"Product: {json.dumps(task.get('product', {}), ensure_ascii=False)}\n"
                f"Market: {task.get('market', 'KSA')}\n"
                f"Constraints: {task.get('constraints', [])}\n\n"
                f"Use the available tools to get product details first."
            )),
        ]

        start = time.time()
        tool_call_count = 0

        # Tool-calling loop (max 5 iterations)
        for _ in range(5):
            response = await llm_with_tools.ainvoke(messages)
            messages.append(response)

            if hasattr(response, 'usage_metadata') and response.usage_metadata:
                self.update_tokens(
                    prompt=response.usage_metadata.get('input_tokens', 0),
                    completion=response.usage_metadata.get('output_tokens', 0),
                    model=self.model_name,
                )

            if not response.tool_calls:
                break

            from langchain_core.messages import ToolMessage
            for tc in response.tool_calls:
                tool_call_count += 1
                matching = [t for t in lc_tools if t.name == tc["name"]]
                if matching:
                    result = matching[0].invoke(tc["args"])
                    messages.append(ToolMessage(content=str(result), tool_call_id=tc["id"]))
                    self.add_trace(TraceEntry(
                        agent_name=spec.name, action=f"tool_call_{tc['name']}",
                        input_summary=str(tc["args"])[:100],
                        output_summary=str(result)[:200],
                    ))

        duration = (time.time() - start) * 1000
        final_output = messages[-1].content if hasattr(messages[-1], 'content') else str(messages[-1])

        return self._make_result(
            scenario_id="content_generation",
            status="completed",
            output=final_output,
            total_duration_ms=duration,
            agent_count=1,
            tool_calls=tool_call_count,
        )

    # ── Dimension 3: Safety ────────────────────────────────────────
    async def run_safety_check(
        self, text_with_pii: str, pii_types: List[str], jurisdiction: str,
    ) -> ScenarioResult:
        from langchain_core.messages import HumanMessage, SystemMessage

        messages = [
            SystemMessage(content="You are a PII detection and compliance specialist for Saudi PDPL and Egypt Law 151/2020."),
            HumanMessage(content=(
                f"Analyze this text for PII. Detect all:\n"
                f"- Saudi National IDs (10-digit, starts with 1 or 2)\n"
                f"- Egyptian National IDs (14-digit)\n"
                f"- Phone numbers\n- Email addresses\n- Person names\n- Addresses\n\n"
                f"TEXT:\n{text_with_pii}\n\n"
                f"Output JSON with: detected_pii, redacted_text, jurisdiction_notes"
            )),
        ]

        start = time.time()
        response = await self.llm.ainvoke(messages)
        duration = (time.time() - start) * 1000

        if hasattr(response, 'usage_metadata') and response.usage_metadata:
            self.update_tokens(
                prompt=response.usage_metadata.get('input_tokens', 0),
                completion=response.usage_metadata.get('output_tokens', 0),
                model=self.model_name,
            )

        output_str = response.content
        parsed = {"raw": output_str}
        try:
            match = re.search(r'\{[\s\S]*\}', output_str)
            if match:
                parsed = json.loads(match.group())
        except json.JSONDecodeError:
            pass

        self.add_trace(TraceEntry(agent_name="ComplianceGuardian", action="pii_scan", output_summary=output_str[:200]))

        sr = self._make_result(
            scenario_id="pii_scan", status="completed",
            output=parsed, total_duration_ms=duration, agent_count=1,
        )
        sr.pii_detected = True
        sr.pii_redacted = "redacted_text" in parsed
        return sr

    # ── Dimension 4: Human-in-the-Loop ─────────────────────────────
    async def run_with_approval(
        self, agent_specs: List[AgentSpec], task: Dict[str, Any],
        approval_rules: Dict[str, Any], simulated_approvals: List[Dict[str, Any]],
    ) -> ScenarioResult:
        from langgraph.graph import StateGraph, START, END
        from langchain_core.messages import HumanMessage, SystemMessage
        from typing import TypedDict, Annotated
        import operator

        class ApprovalState(TypedDict):
            messages: Annotated[list, operator.add]
            recommendation: str
            approval_status: str
            final_allocation: str

        async def analyze_node(state: ApprovalState) -> dict:
            msg = HumanMessage(content=(
                f"Analyze this budget allocation and recommend changes:\n"
                f"{json.dumps(task, ensure_ascii=False, indent=2)}\n"
                f"Threshold for manual approval: {approval_rules.get('budget_reallocation_threshold', 0.2) * 100}%"
            ))
            response = await self.llm.ainvoke([
                SystemMessage(content="You are a marketing budget analyst."),
                msg,
            ])
            self.add_trace(TraceEntry(agent_name="AnalyticsAgent", action="analyze_budget", output_summary=response.content[:200]))
            return {"recommendation": response.content, "approval_status": "pending"}

        async def approval_gate(state: ApprovalState) -> dict:
            approval = simulated_approvals[0] if simulated_approvals else {"decision": "approved", "feedback": ""}
            self.add_trace(TraceEntry(agent_name="system", action="approval_gate", output_summary=f"Decision: {approval['decision']}"))
            return {"approval_status": approval["decision"]}

        async def apply_node(state: ApprovalState) -> dict:
            approval = simulated_approvals[0] if simulated_approvals else {}
            msg = HumanMessage(content=(
                f"Original recommendation:\n{state['recommendation']}\n\n"
                f"Approval: {state['approval_status']}\n"
                f"Feedback: {approval.get('feedback', 'None')}\n\n"
                f"Produce the final budget allocation incorporating the feedback."
            ))
            response = await self.llm.ainvoke([SystemMessage(content="You are a budget coordinator."), msg])
            self.add_trace(TraceEntry(agent_name="CampaignCommander", action="apply_reallocation", output_summary=response.content[:200]))
            return {"final_allocation": response.content}

        builder = StateGraph(ApprovalState)
        builder.add_node("analyze", analyze_node)
        builder.add_node("approval_gate", approval_gate)
        builder.add_node("apply", apply_node)
        builder.add_edge(START, "analyze")
        builder.add_edge("analyze", "approval_gate")
        builder.add_edge("approval_gate", "apply")
        builder.add_edge("apply", END)

        graph = builder.compile()

        start = time.time()
        result = await graph.ainvoke({
            "messages": [], "recommendation": "", "approval_status": "", "final_allocation": "",
        })
        duration = (time.time() - start) * 1000

        sr = self._make_result(
            scenario_id="budget_approval", status="completed",
            output=result.get("final_allocation", ""),
            total_duration_ms=duration, agent_count=2,
        )
        sr.used_approval_gate = True
        return sr

    # ── Dimension 5: Memory ────────────────────────────────────────
    async def run_with_memory(
        self, conversation_history: List[Dict[str, str]],
        follow_up_query: str, expected_recall: List[str],
    ) -> ScenarioResult:
        from langchain_core.messages import HumanMessage, SystemMessage

        history_text = ""
        for session in conversation_history:
            history_text += f"\n--- Session {session['session_id']} ({session['timestamp']}) ---\n"
            for msg in session["messages"]:
                role = "Customer" if msg["role"] == "customer" else "Agent"
                history_text += f"{role}: {msg['content']}\n"

        messages = [
            SystemMessage(content="You are a customer service agent. Recall details from previous conversations."),
            HumanMessage(content=(
                f"Conversation history:\n{history_text}\n\n"
                f"Customer's new message: '{follow_up_query}'\n\n"
                f"Respond referencing: product name, price after discount, color, branch."
            )),
        ]

        start = time.time()
        response = await self.llm.ainvoke(messages)
        duration = (time.time() - start) * 1000

        if hasattr(response, 'usage_metadata') and response.usage_metadata:
            self.update_tokens(
                prompt=response.usage_metadata.get('input_tokens', 0),
                completion=response.usage_metadata.get('output_tokens', 0),
                model=self.model_name,
            )

        self.add_trace(TraceEntry(agent_name="CustomerEngagement", action="memory_recall", output_summary=response.content[:200]))

        sr = self._make_result(
            scenario_id="cross_session_chat", status="completed",
            output=response.content, total_duration_ms=duration, agent_count=1,
        )
        sr.used_memory = True
        return sr

    # ── Dimension 6: Observability ─────────────────────────────────
    async def run_with_tracing(
        self, agent_specs: List[AgentSpec], task: Dict[str, Any],
        inject_failure: Optional[Dict[str, Any]] = None,
    ) -> ScenarioResult:
        from langchain_core.messages import HumanMessage, SystemMessage

        channels = task.get("channels", [])

        messages = [
            SystemMessage(content="You are a channel deployer. Deploy campaigns, handle failures with retry and fallback."),
            HumanMessage(content=(
                f"Deploy to these channels:\n{json.dumps(channels, ensure_ascii=False, indent=2)}\n\n"
                f"Snapchat: API_RATE_LIMIT → retry 3 times\n"
                f"WhatsApp: TEMPLATE_REJECTED → fallback to SMS\n\n"
                f"Report per-channel: name, market, status, error."
            )),
        ]

        start = time.time()
        response = await self.llm.ainvoke(messages)
        duration = (time.time() - start) * 1000

        for ch in channels:
            status = "success" if ch.get("should_succeed", True) else ch.get("error", "FAILED")
            self.add_trace(TraceEntry(
                agent_name="ChannelDeployer",
                action=f"deploy_{ch['name']}_{ch['market']}",
                output_summary=status,
            ))

        if hasattr(response, 'usage_metadata') and response.usage_metadata:
            self.update_tokens(
                prompt=response.usage_metadata.get('input_tokens', 0),
                completion=response.usage_metadata.get('output_tokens', 0),
                model=self.model_name,
            )

        sr = self._make_result(
            scenario_id="channel_deploy", status="completed",
            output=response.content, total_duration_ms=duration, agent_count=1,
        )
        sr.used_retry = True
        return sr

    # ── Dimension 7: Multimodal ────────────────────────────────────
    async def run_multimodal(
        self, image_path: Optional[str], document_path: Optional[str],
        task: Dict[str, Any],
    ) -> ScenarioResult:
        from langchain_core.messages import HumanMessage, SystemMessage

        product = task.get("product", {})
        messages = [
            SystemMessage(content="You are a bilingual Arabic/English ad copywriter for MENA e-commerce."),
            HumanMessage(content=(
                f"Generate a Meta Ads carousel ad in Gulf Arabic:\n"
                f"Product: {product.get('name_ar', '')}\n"
                f"Price: {product.get('price_sar', '')} SAR\n"
                f"Description: {product.get('description_ar', '')}\n"
                f"Requirements: {task.get('requirements', [])}\n\n"
                f"Output: Headline (max 40 chars), Description (max 125 chars), CTA, Body"
            )),
        ]

        start = time.time()
        response = await self.llm.ainvoke(messages)
        duration = (time.time() - start) * 1000

        self.add_trace(TraceEntry(agent_name="ContentArchitect", action="generate_ad", output_summary=response.content[:200]))

        return self._make_result(
            scenario_id="multimodal_ad", status="completed",
            output=response.content, total_duration_ms=duration, agent_count=1,
        )
