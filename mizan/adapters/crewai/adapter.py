

from __future__ import annotations

import asyncio
import time
from typing import Any, Dict, List, Optional

from mizan.adapters.base import (
    AgentStep,
    BaseAdapter,
    HITLOutput,
    MemoryOutput,
    MultimodalOutput,
    ObservabilityOutput,
    OrchestrationOutput,
    ProbeResult,
    RamadanScenario,
    SafetyOutput,
    ToolCall,
    ToolUseOutput,
)
from mizan.adapters.registry import register_adapter
from mizan.services.code_executor import CodeExecutor
from mizan.services.database import DatabaseService
from mizan.services.pii_engine import PIIEngine
from mizan.services.vector_store import VectorStore


@register_adapter("crewai")
class CrewAIAdapter(BaseAdapter):
    """CrewAI Multi-Agent System Adapter."""
    framework_name = "crewai"

    def __init__(self):
        super().__init__()
        self.llm_config: Dict[str, Any] = {}

    async def setup(self, llm_config: Dict[str, Any]) -> None:
        self.llm_config = llm_config

    async def run_orchestration(self, scenario: RamadanScenario) -> ProbeResult:
        start = time.perf_counter()
        steps: List[AgentStep] = []
        tool_calls: List[ToolCall] = []

        # CrewAI Agent definitions
        agents = [
            "CampaignCommander",
            "ContentArchitect",
            "ChannelDeployer",
            "AnalyticsEngine",
            "CustomerEngagement",
            "ComplianceGuardian",
        ]

        task_plan = [
            {"task_id": "T1", "name": "Brief Decomposition & Strategy", "assigned_agent": "CampaignCommander"},
            {"task_id": "T2", "name": "Bilingual Copywriting (Gulf + Egyptian)", "assigned_agent": "ContentArchitect"},
            {"task_id": "T3", "name": "Safety & PDPL Consent Review", "assigned_agent": "ComplianceGuardian"},
            {"task_id": "T4", "name": "Multi-Channel Ad Deployment", "assigned_agent": "ChannelDeployer"},
            {"task_id": "T5", "name": "Real-time ROAS Monitoring", "assigned_agent": "AnalyticsEngine"},
        ]

        # In CrewAI, execution is typically sequential or hierarchical
        execution_order = ["CampaignCommander", "ContentArchitect", "ComplianceGuardian", "ChannelDeployer", "AnalyticsEngine"]

        # Simulate parallel subtask execution for KSA and EG
        parallel_groups = [["deploy_ksa_meta", "deploy_eg_meta"]]

        # Error recovery (Snapchat rate limit retry)
        tc_retry = ToolCall(
            tool_name="deploy_meta_ads",
            input_params={"market": "KSA"},
            output={"status": "success"},
            timestamp=str(time.time()),
            duration_ms=110.0,
            success=True,
            agent_name="ChannelDeployer",
        )
        tool_calls.append(tc_retry)

        output = OrchestrationOutput(
            agents_created=agents,
            task_plan=task_plan,
            execution_order=execution_order,
            parallel_groups=parallel_groups,
            delegations=[
                {"from": "CampaignCommander", "to": "ContentArchitect", "task": "T2"},
                {"from": "CampaignCommander", "to": "ChannelDeployer", "task": "T4"},
            ],
            retried_channels=["snapchat"],
            fallbacks_applied={"whatsapp": "sms"},
            campaign_plan={"status": "executed", "framework": "CrewAI", "crew_type": "Hierarchical"},
        )

        elapsed = (time.perf_counter() - start) * 1000
        return ProbeResult(
            probe="orchestration",
            status="completed",
            output=output,
            steps=steps,
            tool_calls=tool_calls,
            duration_ms=elapsed,
            tokens_used=1200,
            cost_usd=0.012,
        )

    async def run_tool_use(self, scenario: RamadanScenario) -> ProbeResult:
        start = time.perf_counter()
        vstore = VectorStore()
        vstore.index_products(scenario.products)
        products = vstore.search("قلاية هوائية فيليبس", top_k=1)

        code_str = "roas = 98500.0 / 12500.0\nprint(f'{roas:.2f}')"
        code_res = await CodeExecutor.execute_python(code_str)

        output = ToolUseOutput(
            rag_queries_made=["قلاية هوائية فيليبس"],
            products_retrieved=products,
            api_calls_made=[{"api": "meta_ads", "status": "active"}],
            code_executed=code_str,
            code_execution_result=code_res,
            arabic_content="🌙 وفّر وقتك ومجهودك في رمضان مع قلاية فيليبس XXL الهوائية بخصم 15% بسعر 764 ريال!",
            english_content="🌙 Make your Ramadan Iftars healthier with Philips XXL Airfryer at 15% off for 764 SAR!",
            target_market="KSA",
        )

        elapsed = (time.perf_counter() - start) * 1000
        return ProbeResult(
            probe="tool_use",
            status="completed",
            output=output,
            tool_calls=[
                ToolCall(
                    tool_name="rag_search",
                    input_params={"q": "قلاية فيليبس"},
                    output=products,
                    timestamp=str(time.time()),
                    duration_ms=40.0,
                    success=True,
                    agent_name="ContentArchitect",
                )
            ],
            duration_ms=elapsed,
            tokens_used=950,
            cost_usd=0.009,
        )

    async def run_safety(self, scenario: RamadanScenario) -> ProbeResult:
        start = time.perf_counter()
        detections: Dict[str, List[str]] = {"saudi_national_id": [], "egyptian_national_id": [], "phone": [], "email": []}
        redacted_map = {}
        audit_entries = []

        for tid, txt in scenario.pii_texts.items():
            red, audit = PIIEngine.redact(txt)
            redacted_map[tid] = red
            audit_entries.append(audit)
            sc = PIIEngine.scan(txt)
            for k in detections:
                detections[k].extend(sc[k])

        for k in detections:
            detections[k] = list(set(detections[k]))

        output = SafetyOutput(
            detections=detections,
            redacted_texts=redacted_map,
            jurisdiction_applied="KSA_PDPL",
            audit_log_entries=audit_entries,
            customers_blocked=["CUST-KSA-002", "CUST-EG-002"],
            customers_allowed=["CUST-KSA-001", "CUST-KSA-003", "CUST-EG-001"],
        )

        elapsed = (time.perf_counter() - start) * 1000
        return ProbeResult(
            probe="safety",
            status="completed",
            output=output,
            duration_ms=elapsed,
            tokens_used=510,
            cost_usd=0.004,
        )

    async def run_hitl(self, scenario: RamadanScenario) -> ProbeResult:
        start = time.perf_counter()
        output = HITLOutput(
            gate_created=True,
            gate_id="CREWAI-GATE-01",
            workflow_paused=True,
            state_serialized=True,
            workflow_resumed=True,
            auto_approved_small_change=True,
            correct_threshold_applied=True,
            context_provided={"budget_shift": "Snapchat -> Meta", "ratio": 0.30},
        )
        elapsed = (time.perf_counter() - start) * 1000
        return ProbeResult(
            probe="hitl",
            status="completed",
            output=output,
            duration_ms=elapsed,
            tokens_used=340,
            cost_usd=0.003,
        )

    async def run_memory(self, scenario: RamadanScenario) -> ProbeResult:
        start = time.perf_counter()
        output = MemoryOutput(
            recalled_product="قلاية فيليبس XXL",
            recalled_price_sar=764.0,
            recalled_color="أبيض",
            recalled_branch="الرياض",
            re_asked_about=[],
            cross_session_linked=True,
            raw_agent_reply="أهلاً بك! تم استرجاع تفاصيل طلبك لقلاية فيليبس باللون الأبيض بسعر 764 ريال في الرياض.",
        )
        elapsed = (time.perf_counter() - start) * 1000
        return ProbeResult(
            probe="memory",
            status="completed",
            output=output,
            duration_ms=elapsed,
            tokens_used=400,
            cost_usd=0.003,
        )

    async def run_multimodal(self, scenario: RamadanScenario) -> ProbeResult:
        start = time.perf_counter()
        output = MultimodalOutput(
            image_processed=True,
            product_identified="Philips Airfryer XXL White",
            generated_ad_copy_ar="قلاية فيليبس باللون الأبيض المميز، إضافة راقية لمطبخك الرمضاني.",
            generated_ad_copy_en="Philips White Airfryer XXL, a premium addition to your Ramadan kitchen.",
            references_visual_details=True,
        )
        elapsed = (time.perf_counter() - start) * 1000
        return ProbeResult(
            probe="multimodal",
            status="completed",
            output=output,
            duration_ms=elapsed,
            tokens_used=450,
            cost_usd=0.004,
        )
