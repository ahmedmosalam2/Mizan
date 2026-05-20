from abc import ABC, abstractmethod
from typing import Any, Dict, Optional
from pydantic import BaseModel


class ApprovalRequest(BaseModel):
    gate_name: str
    description: str
    data_to_review: Dict[str, Any]
    requested_by: str = "system"


class ApprovalResponse(BaseModel):
    approved: bool
    reviewer: str
    feedback: Optional[str] = None
    modifications: Dict[str, Any] = {}


class HumanApprovalPort(ABC):
    @abstractmethod
    async def request_approval(
        self, request: ApprovalRequest
    ) -> ApprovalResponse:
        pass
