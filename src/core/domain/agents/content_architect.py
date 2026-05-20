from typing import Optional
import time
from core.domain.agents.base import Agent
from core.domain.agents.agent_result import AgentResultBuilder
from core.domain.agents.agent_context import AgentContext
from core.domain.entities.agent_helper import Task
from core.ports.llm_ports import LLMPort

class ContentArchitectAgent(Agent):
    def __init__(self, llm: LLMPort):
        self.name = "ContentArchitect"
        self.llm = llm

    async def execute(self, task: Task, context: Optional[AgentContext] = None):
        start = time.time()
        brief = task.context.get("brief", {})
        details = task.context.get("details", "")

        prompt = f"Generate campaign content for: {brief.get('name')}\nDetails: {details}"
        result = await self.llm.generate(prompt)

        if context:
            context.set_data("generated_content", result)
            context.add_message(self.name, "content_generation", {"content": result})

        elapsed = (time.time() - start) * 1000
        return AgentResultBuilder(agent_name=self.name, task_id=task.goal) \
            .success({"content": result, "details": details}) \
            .with_execution_time(elapsed) \
            .build()