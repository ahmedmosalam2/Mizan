import json
import time
from typing import Any, Dict, List, Optional
from core.domain.agents.base import Agent
from core.domain.agents.agent_result import AgentResult, AgentResultBuilder
from core.domain.agents.agent_context import AgentContext
from core.domain.entities.agent_helper import Task
from core.domain.entities.campaign_brief import CampaignBrief
from core.ports.llm_ports import LLMPort
from core.ports.human_approval_port import (
    HumanApprovalPort,
    ApprovalRequest,
)
from core.domain.enums.enums import ApprovalGate, AgentType, Priority


class CampaignCommanderAgent(Agent):

    def __init__(
        self,
        llm: LLMPort,
        approval_port: HumanApprovalPort,
    ):
        self.name = "CampaignCommander"
        self.llm = llm
        self.approval_port = approval_port

    async def execute(
        self, task: Task, context: Optional[AgentContext] = None
    ) -> AgentResult:
        start = time.time()

        brief_data = task.context.get("brief", {})
        brief = CampaignBrief(**brief_data)

        approval = await self.approval_port.request_approval(
            ApprovalRequest(
                gate_name=ApprovalGate.CAMPAIGN_BRIEF,
                description=f"Approve campaign: {brief.name}",
                data_to_review=brief_data,
                requested_by=AgentType.CAMPAIGN_COMMANDER,
            )
        )

        if not approval.approved:
            elapsed = (time.time() - start) * 1000
            return (
                AgentResultBuilder(agent_name=self.name, task_id=task.goal)
                .failure(approval.feedback or "Brief rejected by reviewer")
                .with_execution_time(elapsed)
                .build()
            )

        if approval.modifications:
            brief_data.update(approval.modifications)
            brief = CampaignBrief(**brief_data)

        prompt = f"""You are a Campaign Commander for a MENA e-commerce retailer.
Given this Ramadan campaign brief, decompose it into sub-tasks.

Brief:
- Name: {brief.name}
- Market: {brief.market}
- Budget: {brief.total_budget} {brief.currency}
- Channels: {', '.join(brief.channels)}
- Audience: {brief.target_audience}
- Objectives: {', '.join(brief.objectives)}

Return a JSON array of sub-tasks. Each task should have:
- "agent": which agent handles it (ContentArchitect, ChannelDeployer, AnalyticsEngine)
- "action": what to do
- "priority": high/medium/low
- "details": specific instructions

Return ONLY valid JSON array, no markdown."""

        llm_response = await self.llm.generate(prompt)

        try:
            sub_tasks = json.loads(llm_response)
        except json.JSONDecodeError:
            sub_tasks = [{"agent": "unknown", "action": llm_response, "priority": "medium"}]

        if context:
            context.set_data("campaign_brief", brief_data)
            context.set_data("sub_tasks", sub_tasks)
            context.add_message(self.name, "task_decomposition", f"Decomposed brief into {len(sub_tasks)} sub-tasks")

        elapsed = (time.time() - start) * 1000
        return (
            AgentResultBuilder(agent_name=self.name, task_id=task.goal)
            .success({
                "brief_name": brief.name,
                "market": brief.market,
                "sub_tasks_count": len(sub_tasks),
                "sub_tasks": sub_tasks,
                "approval_reviewer": approval.reviewer,
            })
            .with_execution_time(elapsed)
            .build()
        )
