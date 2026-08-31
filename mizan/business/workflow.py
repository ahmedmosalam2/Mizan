"""Executable six-agent Ramadan retail workflow for the Mizan Sandbox AUT."""

from __future__ import annotations

from pathlib import Path
from typing import Any
from uuid import UUID

from mizan.business.models import CampaignBrief, CampaignExecution, DeploymentEvidence
from mizan.business.repository import SandboxRepository
from mizan.business.tools import ToolGateway
from mizan.core.contracts import (
    ApprovalStatus,
    CampaignStatus,
    ExecutionMode,
    TenantContext,
    ToolAction,
    ToolRequest,
)
from mizan.scenario.loader import load_yaml


class RamadanCampaignWorkflow:
    """Runs a real persisted Sandbox workflow, never an external deployment."""

    _TASKS = [
        {"task_id": "ORCH-PLAN-001", "agent_id": "CampaignCommander"},
        {"task_id": "RAG-PROD-001", "agent_id": "ContentArchitect"},
        {"task_id": "SAFE-PII-001", "agent_id": "ComplianceGuardian"},
        {"task_id": "DEPLOY-RETRY-001", "agent_id": "ChannelDeployer"},
        {"task_id": "MEMORY-CUSTOMER-001", "agent_id": "CustomerEngagement"},
        {"task_id": "ANALYTICS-ROAS-001", "agent_id": "AnalyticsEngine"},
    ]

    def __init__(self, db_path: str | Path):
        self.repository = SandboxRepository(db_path)
        self.tools = ToolGateway(self.repository)

    def bootstrap_company(self, company_id: str) -> None:
        """Seed only the explicit local synthetic fixture catalog for one tenant."""
        self.repository.ensure_company(company_id)
        self.repository.seed_catalog(company_id, load_yaml("products.yaml"))
        self.repository.seed_customers(company_id, load_yaml("customers.yaml"))

    @staticmethod
    def _tenant(company_id: str) -> TenantContext:
        return TenantContext(
            company_id=company_id,
            actor_id="mizan-sandbox-workflow",
            actor_roles={"system"},
            execution_mode=ExecutionMode.SANDBOX,
        )

    def _agent_request(
        self,
        *,
        run_id: str,
        brief: CampaignBrief,
        task_id: str,
        agent_id: str,
        tool_name: str,
        action: ToolAction,
        arguments: dict[str, Any],
        suffix: str,
    ) -> ToolRequest:
        return ToolRequest(
            run_id=UUID(run_id),
            tenant=self._tenant(brief.company_id),
            campaign_id=brief.campaign_id,
            task_id=task_id,
            agent_id=agent_id,
            tool_name=tool_name,
            action=action,
            arguments=arguments,
            idempotency_key=f"{brief.campaign_id}:{task_id}:{suffix}",
        )

    def _run_tool(
        self,
        brief: CampaignBrief,
        task_id: str,
        agent_id: str,
        tool_name: str,
        action: ToolAction,
        arguments: dict[str, Any],
        suffix: str,
        invocation: Any,
    ) -> Any:
        run_id = self.repository.start_agent_run(brief.company_id, brief.campaign_id, task_id, agent_id)
        request = self._agent_request(
            run_id=run_id,
            brief=brief,
            task_id=task_id,
            agent_id=agent_id,
            tool_name=tool_name,
            action=action,
            arguments=arguments,
            suffix=suffix,
        )
        response = invocation(request)
        self.repository.finish_agent_run(run_id, "succeeded" if response.success else "failed")
        return response

    def create_campaign(self, brief: CampaignBrief) -> CampaignExecution:
        """Create the campaign and stop at a required approval gate when applicable."""
        self.bootstrap_company(brief.company_id)
        self.repository.create_campaign(
            brief.campaign_id, brief.company_id, brief.name, brief.target_market, brief.market_budget
        )
        current = CampaignStatus(self.repository.get_campaign(brief.company_id, brief.campaign_id)["status"])
        if current is CampaignStatus.DRAFT:
            self.repository.transition_campaign(brief.company_id, brief.campaign_id, CampaignStatus.PLANNING)
            plan = [
                {**task, "payload": {"campaign_id": brief.campaign_id, "market": brief.target_market}}
                for task in self._TASKS
            ]
            response = self._run_tool(
                brief,
                "ORCH-PLAN-001",
                "CampaignCommander",
                "create_tasks",
                ToolAction.WRITE,
                {"tasks": plan},
                "create-tasks",
                self.tools.create_tasks,
            )
            if not response.success:
                self.repository.transition_campaign(brief.company_id, brief.campaign_id, CampaignStatus.FAILED)
                return CampaignExecution(
                    campaign_id=brief.campaign_id,
                    company_id=brief.company_id,
                    status=CampaignStatus.FAILED,
                    notes=["Campaign Commander could not persist the execution plan."],
                )

            if brief.proposed_reallocation_ratio > 0.20:
                approval = self._run_tool(
                    brief,
                    "HITL-BUDGET-001",
                    "CampaignCommander",
                    "request_approval",
                    ToolAction.REQUEST_APPROVAL,
                    {
                        "requested_action": "Apply campaign budget reallocation above the 20% threshold",
                        "risk": "high",
                        "required_role": "finance_approver",
                        "reason": f"Requested reallocation ratio: {brief.proposed_reallocation_ratio:.2f}",
                    },
                    "budget-approval",
                    self.tools.request_approval,
                )
                if not approval.success:
                    self.repository.transition_campaign(brief.company_id, brief.campaign_id, CampaignStatus.FAILED)
                    return CampaignExecution(
                        campaign_id=brief.campaign_id,
                        company_id=brief.company_id,
                        status=CampaignStatus.FAILED,
                        notes=["The required budget approval could not be created."],
                    )
                self.repository.transition_campaign(
                    brief.company_id, brief.campaign_id, CampaignStatus.AWAITING_APPROVAL
                )
                return CampaignExecution(
                    campaign_id=brief.campaign_id,
                    company_id=brief.company_id,
                    status=CampaignStatus.AWAITING_APPROVAL,
                    approval_id=UUID(approval.result["approval_id"]),
                    approval_status=ApprovalStatus.PENDING,
                    notes=["Execution stopped: the requested budget change exceeds 20%."],
                )

            self.repository.transition_campaign(brief.company_id, brief.campaign_id, CampaignStatus.APPROVED)
        return self.resume_campaign(brief)

    def decide_budget_approval(self, company_id: str, approval_id: UUID, approved_by: str, approved: bool) -> ApprovalStatus:
        """Persist an explicit human decision; this does not silently resume a workflow."""
        status = self.repository.decide_approval(company_id, str(approval_id), approved_by, approved)
        approval = self.repository.get_approval(company_id, str(approval_id))
        if status is ApprovalStatus.APPROVED:
            self.repository.transition_campaign(company_id, approval["campaign_id"], CampaignStatus.APPROVED)
        elif status is ApprovalStatus.REJECTED:
            self.repository.transition_campaign(company_id, approval["campaign_id"], CampaignStatus.PLANNING)
        return status

    def resume_campaign(self, brief: CampaignBrief) -> CampaignExecution:
        """Continue only an approved campaign through six real local agent responsibilities."""
        campaign = self.repository.get_campaign(brief.company_id, brief.campaign_id)
        status = CampaignStatus(campaign["status"])
        if status is CampaignStatus.AWAITING_APPROVAL:
            return CampaignExecution(
                campaign_id=brief.campaign_id,
                company_id=brief.company_id,
                status=status,
                notes=["Workflow remains paused until an approval decision is persisted."],
            )
        if status is not CampaignStatus.APPROVED:
            raise ValueError(f"Campaign cannot resume from {status.value}")

        self.repository.transition_campaign(brief.company_id, brief.campaign_id, CampaignStatus.CONTENT_GENERATION)
        content = self._run_tool(
            brief,
            "RAG-PROD-001",
            "ContentArchitect",
            "product_search",
            ToolAction.READ,
            {"query": brief.product_query, "top_k": 1},
            "product-search",
            self.tools.product_search,
        )
        if not content.success or not content.result["products"]:
            self.repository.transition_campaign(brief.company_id, brief.campaign_id, CampaignStatus.FAILED)
            return CampaignExecution(
                campaign_id=brief.campaign_id,
                company_id=brief.company_id,
                status=CampaignStatus.FAILED,
                notes=["No permitted product could be retrieved for the campaign content."],
            )
        product = content.result["products"][0]
        generated_content = (
            f"Ramadan offer: {product['name_en']} at {product.get('ramadan_price_sar')} SAR. "
            f"{product.get('description_en', '')}"
        )

        self.repository.transition_campaign(brief.company_id, brief.campaign_id, CampaignStatus.COMPLIANCE_CHECK)
        pii = self._run_tool(
            brief,
            "SAFE-PII-001",
            "ComplianceGuardian",
            "pii_redaction",
            ToolAction.EXECUTE,
            {"text": generated_content, "jurisdiction": "KSA" if brief.target_market == "KSA" else "EG"},
            "content-pii",
            self.tools.redact_pii,
        )
        if not pii.success:
            self.repository.transition_campaign(brief.company_id, brief.campaign_id, CampaignStatus.FAILED)
            return CampaignExecution(
                campaign_id=brief.campaign_id,
                company_id=brief.company_id,
                status=CampaignStatus.FAILED,
                selected_product_sku=product["sku"],
                notes=["Compliance validation failed before deployment."],
            )

        permitted_customers = 0
        blocked_customers = 0
        for customer_id in brief.target_customer_ids:
            consent = self._run_tool(
                brief,
                "SAFE-CONSENT-001",
                "ComplianceGuardian",
                "consent_check",
                ToolAction.READ,
                {"customer_id": customer_id, "channel": brief.requested_channels[0]},
                f"consent:{customer_id}",
                self.tools.check_consent,
            )
            if consent.success and consent.result["allowed"]:
                permitted_customers += 1
            else:
                blocked_customers += 1

        self.repository.transition_campaign(brief.company_id, brief.campaign_id, CampaignStatus.READY_TO_DEPLOY)
        self.repository.transition_campaign(brief.company_id, brief.campaign_id, CampaignStatus.DEPLOYING)
        processed_channels: set[str] = set()
        for channel in brief.requested_channels:
            if channel in processed_channels:
                continue
            processed_channels.add(channel)
            first = self._run_tool(
                brief,
                "DEPLOY-RETRY-001",
                "ChannelDeployer",
                "channel_deployment",
                ToolAction.EXECUTE,
                {"channel": channel, "attempt": 1, "content": pii.result["redacted_text"]},
                f"deploy:{channel}:1",
                self.tools.deploy_channel,
            )
            if not first.success and first.error and first.error.code.value == "rate_limit":
                self._run_tool(
                    brief,
                    "DEPLOY-RETRY-001",
                    "ChannelDeployer",
                    "channel_deployment",
                    ToolAction.EXECUTE,
                    {"channel": channel, "attempt": 2, "content": pii.result["redacted_text"]},
                    f"deploy:{channel}:2",
                    self.tools.deploy_channel,
                )
            elif not first.success and channel == "whatsapp":
                processed_channels.add("sms")
                self._run_tool(
                    brief,
                    "DEPLOY-FALLBACK-001",
                    "ChannelDeployer",
                    "channel_deployment",
                    ToolAction.EXECUTE,
                    {"channel": "sms", "attempt": 1, "fallback_from": "whatsapp", "content": pii.result["redacted_text"]},
                    "deploy:sms:fallback",
                    self.tools.deploy_channel,
                )

        self.repository.transition_campaign(brief.company_id, brief.campaign_id, CampaignStatus.DEPLOYED)

        if permitted_customers:
            customer_id = brief.target_customer_ids[0]
            self._run_tool(
                brief,
                "MEMORY-CUSTOMER-001",
                "CustomerEngagement",
                "customer_memory",
                ToolAction.WRITE,
                {"customer_id": customer_id, "key": "last_campaign_product_sku", "value": product["sku"]},
                "customer-memory",
                self.tools.customer_memory,
            )

        self.repository.transition_campaign(brief.company_id, brief.campaign_id, CampaignStatus.ANALYZING)
        metric_defaults = {"spend": 1.0, "revenue": 0.0, "clicks": 0.0, "impressions": 1.0, "conversions": 1.0}
        analytics_input = {**metric_defaults, **brief.analytics_input}
        analytics = self._run_tool(
            brief,
            "ANALYTICS-ROAS-001",
            "AnalyticsEngine",
            "campaign_analytics",
            ToolAction.EXECUTE,
            analytics_input,
            "campaign-metrics",
            self.tools.campaign_analytics,
        )
        if not analytics.success:
            self.repository.transition_campaign(brief.company_id, brief.campaign_id, CampaignStatus.FAILED)
            return CampaignExecution(
                campaign_id=brief.campaign_id,
                company_id=brief.company_id,
                status=CampaignStatus.FAILED,
                selected_product_sku=product["sku"],
                compliant_customer_count=permitted_customers,
                blocked_customer_count=blocked_customers,
                notes=["Analytics failed; no optimization action was applied."],
            )

        self.repository.transition_campaign(brief.company_id, brief.campaign_id, CampaignStatus.COMPLETED)
        deployments = [
            DeploymentEvidence(
                channel=entry["channel"],
                status=entry["status"],
                attempt=entry["attempt"],
                fallback_from=entry["fallback_from"],
            )
            for entry in self.repository.list_deployments(brief.company_id, brief.campaign_id)
        ]
        return CampaignExecution(
            campaign_id=brief.campaign_id,
            company_id=brief.company_id,
            status=CampaignStatus.COMPLETED,
            selected_product_sku=product["sku"],
            compliant_customer_count=permitted_customers,
            blocked_customer_count=blocked_customers,
            deployments=deployments,
            metrics=analytics.result["metrics"],
            notes=["All deployment records are explicit sandbox outcomes; no external provider was called."],
        )
