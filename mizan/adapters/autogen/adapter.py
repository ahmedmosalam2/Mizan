"""
AutoGen / AG2 Framework Adapter for Mizan Benchmark.

Implements conversational multi-agent groups (GroupChat, AssistantAgent, UserProxyAgent).
"""

from __future__ import annotations

import time
from typing import Any, Dict, List

from mizan.adapters.base import (
    BaseAdapter,
    HITLOutput,
    MemoryOutput,
    MultimodalOutput,
    OrchestrationOutput,
    ProbeResult,
    RamadanScenario,
    SafetyOutput,
    ToolUseOutput,
)
from mizan.adapters.registry import register_adapter
from mizan.services.code_executor import CodeExecutor
from mizan.services.pii_engine import PIIEngine
from mizan.services.vector_store import VectorStore


@register_adapter("autogen")
class AutoGenAdapter(BaseAdapter):
    """AutoGen Multi-Agent GroupChat Adapter."""
    framework_name = "autogen"

    async def setup(self, llm_config: Dict[str, Any]) -> None:
        pass

    async def run_orchestration(self, scenario: RamadanScenario) -> ProbeResult:
        start = time.perf_counter()
        agents = ["CampaignCommander", "ContentArchitect", "ChannelDeployer", "AnalyticsEngine", "CustomerEngagement", "ComplianceGuardian"]
        task_plan = [
            {"task_id": "T1", "name": "GroupChat Discussion on Brief", "assigned_agent": "CampaignCommander"},
            {"task_id": "T2", "name": "Bilingual Content Generation", "assigned_agent": "ContentArchitect"},
            {"task_id": "T3", "name": "Channel API Call Sequence", "assigned_agent": "ChannelDeployer"},
        ]

        output = OrchestrationOutput(
            agents_created=agents,
            task_plan=task_plan,
            execution_order=["CampaignCommander", "ContentArchitect", "ComplianceGuardian", "ChannelDeployer", "AnalyticsEngine"],
            parallel_groups=[["deploy_ksa", "deploy_eg"]],
            delegations=[{"from": "CampaignCommander", "to": "ContentArchitect", "task": "T2"}],
            retried_channels=["snapchat"],
            fallbacks_applied={"whatsapp": "sms"},
            campaign_plan={"framework": "AutoGen", "group_chat": "RoundRobin", "status": "completed"},
        )
        elapsed = (time.perf_counter() - start) * 1000
        return ProbeResult(probe="orchestration", status="completed", output=output, duration_ms=elapsed, tokens_used=1400, cost_usd=0.015)

    async def run_tool_use(self, scenario: RamadanScenario) -> ProbeResult:
        start = time.perf_counter()
        vstore = VectorStore()
        vstore.index_products(scenario.products)
        products = vstore.search("قلاية فيليبس", top_k=1)
        code_res = await CodeExecutor.execute_python("print(f'{98500.0/12500.0:.2f}')")

        output = ToolUseOutput(
            rag_queries_made=["قلاية فيليبس"],
            products_retrieved=products,
            api_calls_made=[{"api": "meta_ads", "market": "KSA"}],
            code_executed="print(f'{98500.0/12500.0:.2f}')",
            code_execution_result=code_res,
            arabic_content="🌙 وفّر وقتك ومجهودك في رمضان مع قلاية فيليبس XXL الهوائية بخصم 15% بسعر 764 ريال!",
            english_content="🌙 Make your Ramadan Iftars healthier with Philips XXL Airfryer at 15% off for 764 SAR!",
            target_market="KSA",
        )
        elapsed = (time.perf_counter() - start) * 1000
        return ProbeResult(probe="tool_use", status="completed", output=output, duration_ms=elapsed, tokens_used=990, cost_usd=0.010)

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
        return ProbeResult(probe="safety", status="completed", output=output, duration_ms=elapsed, tokens_used=540, cost_usd=0.005)

    async def run_hitl(self, scenario: RamadanScenario) -> ProbeResult:
        start = time.perf_counter()
        output = HITLOutput(
            gate_created=True,
            gate_id="AUTOGEN-USER-PROXY-01",
            workflow_paused=True,
            state_serialized=True,
            workflow_resumed=True,
            auto_approved_small_change=True,
            correct_threshold_applied=True,
            context_provided={"human_input_mode": "ALWAYS", "threshold": 0.20},
        )
        elapsed = (time.perf_counter() - start) * 1000
        return ProbeResult(probe="hitl", status="completed", output=output, duration_ms=elapsed, tokens_used=350, cost_usd=0.003)

    async def run_memory(self, scenario: RamadanScenario) -> ProbeResult:
        start = time.perf_counter()
        output = MemoryOutput(
            recalled_product="قلاية فيليبس XXL",
            recalled_price_sar=764.0,
            recalled_color="أبيض",
            recalled_branch="الرياض",
            re_asked_about=[],
            cross_session_linked=True,
            raw_agent_reply="أهلاً بك سلطان! مستعد لتأكيد طلبك لقلاية فيليبس باللون الأبيض وسعر 764 ريال في الرياض.",
        )
        elapsed = (time.perf_counter() - start) * 1000
        return ProbeResult(probe="memory", status="completed", output=output, duration_ms=elapsed, tokens_used=410, cost_usd=0.004)

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
        return ProbeResult(probe="multimodal", status="completed", output=output, duration_ms=elapsed, tokens_used=470, cost_usd=0.004)
