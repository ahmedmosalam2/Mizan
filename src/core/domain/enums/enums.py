from enum import Enum


class AgentType(str, Enum):
    CAMPAIGN_COMMANDER = "CampaignCommander"
    CONTENT_ARCHITECT = "ContentArchitect"
    CHANNEL_DEPLOYER = "ChannelDeployer"
    ANALYTICS_ENGINE = "AnalyticsEngine"
    CUSTOMER_ENGAGEMENT = "CustomerEngagement"
    COMPLIANCE_GUARDIAN = "ComplianceGuardian"


class Priority(str, Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class ApprovalGate(str, Enum):
    CAMPAIGN_BRIEF = "campaign_brief_approval"
    CONTENT_REVIEW = "content_review_approval"
    BUDGET_REALLOCATION = "budget_reallocation_approval"
    CUSTOMER_ESCALATION = "customer_escalation"
    PII_INCIDENT = "pii_incident_response"
