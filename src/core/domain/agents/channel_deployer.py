from typing import Optional
import time
from core.domain.agents.base import Agent
from core.domain.agents.agent_result import AgentResultBuilder
from core.domain.agents.agent_context import AgentContext
from core.domain.entities.agent_helper import Task
from core.ports.llm_ports import LLMPort


class ChannelDeployerAgent(Agent):
    def __init__(self, llm: LLMPort):
        self.name = "ChannelDeployer"
        self.llm = llm

    async def execute(self, task: Task, context: Optional[AgentContext] = None):
        start = time.time()
        brief = task.context.get("brief", {})
        details = task.context.get("details", "")

        prompt = f"""You are a channel deployer for a MENA Ramadan campaign.
Use the campaign brief and deployment details below to create a simple deployment plan.

Campaign Brief:
{brief}

Deployment Details:
{details}

Return a JSON object with:
- "channel"
- "action"
- "steps"
- "note"

Return ONLY valid JSON, no markdown."""
        deployment_plan = await self.llm.generate(prompt)

        if context:
            context.set_data("deployment_plan", deployment_plan)
            context.add_message(self.name, "deployment_plan", {
                "plan": deployment_plan,
                "details": details
            })

        elapsed = (time.time() - start) * 1000
        return (
            AgentResultBuilder(agent_name=self.name, task_id=task.goal)
            .success({"deployment_plan": deployment_plan, "details": details})
            .with_execution_time(elapsed)
            .build()
        )