"""
Core Approval Gate Models for Mizan Human-in-the-Loop (HITL).

Defines approval triggers, thresholds, authorization levels, and resolution states.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Dict, Optional
from pydantic import BaseModel, Field


class GateType(str, Enum):
    BUDGET_SHIFT = "budget_shift"
    PII_EXEMPTION = "pii_exemption"
    CREATIVE_OVERRIDE = "creative_override"
    DISCOUNT_APPROVAL = "discount_approval"


class GateStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    AUTO_APPROVED = "auto_approved"


class ApprovalGate(BaseModel):
    """A formal Human-in-the-Loop approval gate."""
    gate_id: str
    task_id: str
    gate_type: GateType
    action_description: str
    shift_amount: Optional[float] = None
    shift_ratio: Optional[float] = None
    threshold_ratio: float = 0.20  # Changes > 20% require manual approval
    required_role: str = "marketing_lead"
    status: GateStatus = GateStatus.PENDING
    context: Dict[str, Any] = Field(default_factory=dict)
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat())
    resolved_at: Optional[str] = None
    resolved_by: Optional[str] = None
    resolution_notes: Optional[str] = None

    def evaluate_auto_approval(self) -> bool:
        """Determines if change is within auto-approval threshold."""
        if self.shift_ratio is not None and self.shift_ratio <= self.threshold_ratio:
            self.status = GateStatus.AUTO_APPROVED
            self.resolved_at = datetime.now().isoformat()
            self.resolved_by = "SYSTEM_AUTO_THRESHOLD"
            return True
        return False
