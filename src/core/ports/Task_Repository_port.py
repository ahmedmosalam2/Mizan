from abc import ABC, abstractmethod
from typing import List, Optional
from core.domain.entities.agent_helper import Task


class TaskRepositoryPort(ABC):
    """عقد وسيط بين Core Logic والـ Database للـ Tasks"""
    
    @abstractmethod
    async def get_by_id(self, task_id: str) -> Optional[Task]:

        pass
    
    @abstractmethod
    async def save(self, task: Task) -> Task:

        pass
    
    @abstractmethod
    async def update(self, task_id: str, task: Task) -> Task:

        pass
    
    @abstractmethod
    async def delete(self, task_id: str) -> bool:

        pass
    
    @abstractmethod
    async def list_all(self) -> List[Task]:
   
        pass