
from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class AgentRole(str, Enum):
    CAMPAIGN_COMMANDER = "CampaignCommander"
    CONTENT_ARCHITECT = "ContentArchitect"
    CHANNEL_DEPLOYER = "ChannelDeployer"
    ANALYTICS_ENGINE = "AnalyticsEngine"
    CUSTOMER_ENGAGEMENT = "CustomerEngagement"
    COMPLIANCE_GUARDIAN = "ComplianceGuardian"


class AgentCapability(str, Enum):
    PLANNING = "planning"
    TOOL_CALLING = "tool_calling"
    RAG_SEARCH = "rag_search"
    CODE_EXECUTION = "code_execution"
    PII_DETECTION = "pii_detection"
    STATE_PERSISTENCE = "state_persistence"
    VISION_MULTIMODAL = "vision_multimodal"
    APPROVAL_GATE_REQUEST = "approval_gate_request"


class AgentProfile(BaseModel):
    """Configuration profile for a scenario agent."""
    role: AgentRole
    display_name: str
    system_prompt: str
    capabilities: List[AgentCapability] = Field(default_factory=list)
    available_tools: List[str] = Field(default_factory=list)
    temperature: float = Field(default=0.2, ge=0.0, le=1.0)
    max_iterations: int = Field(default=10, ge=1, le=50)


# Standard Scenario Agent Definitions
SCENARIO_AGENTS: Dict[AgentRole, AgentProfile] = {
    AgentRole.CAMPAIGN_COMMANDER: AgentProfile(
        role=AgentRole.CAMPAIGN_COMMANDER,
        display_name="Campaign Commander (Orchestrator)",
        system_prompt=(
            "You are the Lead Campaign Commander for Ramadan 2026 RetailCo (KSA & Egypt). "
            "Your responsibility is decomposing the campaign brief into structured subtasks, "
            "allocating budget across Saudi and Egyptian channels, delegating tasks to specialist agents, "
            "and requesting human approvals for budget reallocations exceeding 20%."
        ),
        capabilities=[AgentCapability.PLANNING, AgentCapability.APPROVAL_GATE_REQUEST, AgentCapability.STATE_PERSISTENCE],
        available_tools=["create_task", "delegate_task", "request_approval_gate", "query_campaign_state"],
    ),
    AgentRole.CONTENT_ARCHITECT: AgentProfile(
        role=AgentRole.CONTENT_ARCHITECT,
        display_name="Content Architect (Bilingual & Creative Engine)",
        system_prompt=(
            "You are the Content Architect for Ramadan RetailCo. "
            "You produce high-converting, culturally nuanced ad copy in Gulf/Najdi Arabic (KSA) "
            "and Egyptian Arabic (EG), as well as English. You query the product catalog using vector search "
            "and inspect banner images for visual details."
        ),
        capabilities=[AgentCapability.RAG_SEARCH, AgentCapability.VISION_MULTIMODAL, AgentCapability.TOOL_CALLING],
        available_tools=["search_product_catalog", "analyze_creative_image", "format_channel_copy"],
    ),
    AgentRole.CHANNEL_DEPLOYER: AgentProfile(
        role=AgentRole.CHANNEL_DEPLOYER,
        display_name="Channel Deployer (Multi-Channel API & Resilience)",
        system_prompt=(
            "You are the Channel Deployer for Ramadan RetailCo. "
            "You dispatch campaigns across Meta Ads, Google Ads, Snapchat, WhatsApp Business, and SMS. "
            "You handle API rate limits with exponential retries and automatically fall back (e.g. WhatsApp to SMS) on rejections."
        ),
        capabilities=[AgentCapability.TOOL_CALLING, AgentCapability.PLANNING],
        available_tools=["deploy_meta_ads", "deploy_snapchat", "deploy_google_ads", "send_whatsapp", "send_sms"],
    ),
    AgentRole.COMPLIANCE_GUARDIAN: AgentProfile(
        role=AgentRole.COMPLIANCE_GUARDIAN,
        display_name="Compliance Guardian (PII & PDPL Regulator)",
        system_prompt=(
            "You are the Compliance Guardian ensuring strict adherence to Saudi PDPL and Egyptian Law 151/2020. "
            "You intercept and redact all PII (Saudi/Egyptian National IDs, phone numbers, emails), "
            "verify customer opt-in consent before messaging, and maintain an immutable audit trail."
        ),
        capabilities=[AgentCapability.PII_DETECTION, AgentCapability.STATE_PERSISTENCE, AgentCapability.TOOL_CALLING],
        available_tools=["scan_pii", "redact_pii", "verify_consent", "log_audit_event"],
    ),
    AgentRole.CUSTOMER_ENGAGEMENT: AgentProfile(
        role=AgentRole.CUSTOMER_ENGAGEMENT,
        display_name="Customer Engagement (Cross-Session Memory & BNPL)",
        system_prompt=(
            "You are the Customer Engagement Agent handling Ramadan shopper inquiries. "
            "You recall past customer preferences and branch locations across sessions, "
            "and offer localized payment installment plans (Tamara/Tabby in KSA, Fawry/Paymob in EG)."
        ),
        capabilities=[AgentCapability.STATE_PERSISTENCE, AgentCapability.TOOL_CALLING],
        available_tools=["fetch_customer_memory", "save_customer_memory", "calculate_bnpl_schedule"],
    ),
    AgentRole.ANALYTICS_ENGINE: AgentProfile(
        role=AgentRole.ANALYTICS_ENGINE,
        display_name="Analytics & Optimization Engine",
        system_prompt=(
            "You are the Analytics Engine for Ramadan RetailCo. "
            "You monitor real-time campaign performance, execute Python code in sandbox for exact ROAS and CPA calculations, "
            "and compute statistical significance for A/B tests to recommend budget reallocation."
        ),
        capabilities=[AgentCapability.CODE_EXECUTION, AgentCapability.TOOL_CALLING],
        available_tools=["execute_python_analytics", "compute_roas_cpa", "calculate_ab_test_significance"],
    ),
}
