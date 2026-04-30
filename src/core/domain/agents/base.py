from abc import ABC, abstractmethod
from core.domain.entities.agent_helper import Task


class Agent(ABC):

    @abstractmethod
    async def execute(self, task: Task):
        """Execute a Task and return the result."""
        pass
    
  