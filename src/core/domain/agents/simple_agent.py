from typing import Any
from core.domain.agents.base import Agent
from src.core.domain.entities.agent_helper import Task 

class SimpleAgent(Agent):
    """Simple framework-agnostic agent adapter for Week‑1 tests."""

    def __init__(self, llm_client: Any) -> None:
        self.llm = llm_client

    async def execute(self, task: Task) -> Any:
        """Execute a Task using the injected LLM client (expects async generate)."""
        prompt = self._build_prompt(task)
        return await self.llm.generate(prompt)

    def _build_prompt(self, task: Task) -> str:
        return (
            f"You are an AI agent.\n\n"
            f"Goal:\n{task.goal}\n\n"
            f"Context:\n{task.context}\n\n"
            f"Constraints:\n{task.constraints}\n\n"
            f"Expected Output:\n{task.expected_output}\n"
        )