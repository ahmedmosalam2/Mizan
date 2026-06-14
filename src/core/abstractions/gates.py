"""
Human-in-the-loop approval gates.

The workflow must pause at specific decision points and wait for human approval.
This module implements flexible approval gate logic that supports:
1. Single approver (e.g., marketing manager approves budget)
2. Multiple approvers in parallel (e.g., marketing manager + compliance officer)
3. Threshold-based gates (e.g., only require approval for budget > X)
4. Time-limited approvals (e.g., auto-approve if not rejected within 1 hour)
5. Callback handlers for integration with external notification systems
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Callable, Set
from enum import Enum
from datetime import datetime, timedelta
import uuid


class GateStatus(Enum):
    """Status of an approval gate."""
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXPIRED = "expired"
    AUTO_APPROVED = "auto_approved"


class ApprovalDecision(Enum):
    """Decision by an approver."""
    APPROVED = "approved"
    REJECTED = "rejected"
    MODIFICATIONS_REQUESTED = "modifications_requested"


@dataclass
class ApproverDecision:
    """Decision made by a single approver."""
    approver_id: str
    decision: ApprovalDecision
    timestamp: datetime
    comment: Optional[str] = None


@dataclass
class ApprovalGate:
    """
    A checkpoint where the workflow pauses for human approval.
    
    Example use cases:
    - Content approval: marketing manager reviews generated ad copy
    - Budget approval: only shifts > 20% of budget require approval
    - Compliance review: compliance officer checks for PII
    - Escalation: customer service hands off to human representative
    """
    
    gate_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    gate_type: str = ""  # e.g., "content_review", "budget_approval"
    action_description: str = ""  # What is being approved?
    required_approvers: Set[str] = field(default_factory=set)  # User IDs
    optional_approvers: Set[str] = field(default_factory=set)  # Bonus approvers
    
    # Decision rules
    require_unanimous: bool = True  # All required approvers must approve
    auto_approve_after: Optional[timedelta] = None  # Auto-approve if no rejection within time
    
    # Context for decision making
    context: Dict[str, Any] = field(default_factory=dict)
    
    # Status tracking
    status: GateStatus = GateStatus.PENDING
    created_at: datetime = field(default_factory=datetime.now)
    resolved_at: Optional[datetime] = None
    decisions: Dict[str, ApproverDecision] = field(default_factory=dict)
    
    # Callbacks
    on_approval: Optional[Callable] = None
    on_rejection: Optional[Callable] = None
    on_expiration: Optional[Callable] = None
    
    def is_resolved(self) -> bool:
        """Check if gate has been fully resolved."""
        return self.status in [
            GateStatus.APPROVED,
            GateStatus.REJECTED,
            GateStatus.EXPIRED,
            GateStatus.AUTO_APPROVED,
        ]
    
    def get_pending_approvers(self) -> Set[str]:
        """Get list of approvers who haven't decided yet."""
        return self.required_approvers - set(self.decisions.keys())
    
    def add_decision(
        self,
        approver_id: str,
        decision: ApprovalDecision,
        comment: Optional[str] = None,
    ) -> None:
        """
        Record an approver's decision.
        
        Args:
            approver_id: ID of the approver
            decision: Their decision (approved/rejected/modifications_requested)
            comment: Optional comment
        """
        if self.is_resolved():
            raise RuntimeError(f"Gate {self.gate_id} is already resolved")
        
        self.decisions[approver_id] = ApproverDecision(
            approver_id=approver_id,
            decision=decision,
            timestamp=datetime.now(),
            comment=comment,
        )
        
        # Check if we can resolve the gate
        self._check_resolution()
    
    def _check_resolution(self) -> None:
        """Check if gate should be resolved based on current decisions."""
        pending = self.get_pending_approvers()
        
        # Check for rejections (fast-fail)
        rejections = [
            d for d in self.decisions.values()
            if d.decision == ApprovalDecision.REJECTED
        ]
        if rejections:
            self._resolve_gate(GateStatus.REJECTED)
            return
        
        # Check for unanimous approval
        if not pending and self.require_unanimous:
            # All required approvers have approved
            self._resolve_gate(GateStatus.APPROVED)
            return
        
        # If we don't require unanimous and have some approvals, we can proceed
        if not self.require_unanimous and len(self.decisions) > 0:
            self._resolve_gate(GateStatus.APPROVED)
            return
    
    def _resolve_gate(self, status: GateStatus) -> None:
        """Resolve the gate with a given status and trigger callbacks."""
        self.status = status
        self.resolved_at = datetime.now()
        
        if status == GateStatus.APPROVED and self.on_approval:
            self.on_approval(self)
        elif status == GateStatus.REJECTED and self.on_rejection:
            self.on_rejection(self)
        elif status == GateStatus.EXPIRED and self.on_expiration:
            self.on_expiration(self)
    
    def check_expiration(self) -> None:
        """Check if gate has expired (for auto-approval timeout)."""
        if self.is_resolved():
            return
        
        if self.auto_approve_after:
            time_elapsed = datetime.now() - self.created_at
            if time_elapsed > self.auto_approve_after:
                # No rejections received within timeout -> auto-approve
                if not any(
                    d.decision == ApprovalDecision.REJECTED
                    for d in self.decisions.values()
                ):
                    self._resolve_gate(GateStatus.AUTO_APPROVED)
                else:
                    self._resolve_gate(GateStatus.EXPIRED)
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize gate for storage/transmission."""
        return {
            "gate_id": self.gate_id,
            "gate_type": self.gate_type,
            "action_description": self.action_description,
            "required_approvers": list(self.required_approvers),
            "status": self.status.value,
            "created_at": self.created_at.isoformat(),
            "resolved_at": self.resolved_at.isoformat() if self.resolved_at else None,
            "decisions": {
                approver_id: {
                    "decision": d.decision.value,
                    "timestamp": d.timestamp.isoformat(),
                    "comment": d.comment,
                }
                for approver_id, d in self.decisions.items()
            },
            "pending_approvers": list(self.get_pending_approvers()),
        }


class ApprovalManager:
    """
    Manages approval gates for the workflow.
    
    Responsibilities:
    - Create approval gates based on business rules
    - Track pending approvals
    - Notify approvers
    - Apply decisions to workflow
    """
    
    def __init__(self):
        """Initialize approval manager."""
        self.gates: Dict[str, ApprovalGate] = {}
        self._on_gate_created: Optional[Callable] = None
        self._on_gate_resolved: Optional[Callable] = None
    
    def create_gate(
        self,
        gate_type: str,
        action_description: str,
        required_approvers: Set[str],
        optional_approvers: Optional[Set[str]] = None,
        require_unanimous: bool = True,
        auto_approve_after: Optional[timedelta] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> ApprovalGate:
        """
        Create a new approval gate.
        
        Args:
            gate_type: Type of gate (for routing notifications)
            action_description: Human-readable description of what's being approved
            required_approvers: User IDs who must approve
            optional_approvers: User IDs who can optionally approve
            require_unanimous: Whether all required approvers must approve
            auto_approve_after: Automatically approve if no rejection within time
            context: Additional context for approvers
        
        Returns:
            ApprovalGate instance
        """
        gate = ApprovalGate(
            gate_type=gate_type,
            action_description=action_description,
            required_approvers=required_approvers,
            optional_approvers=optional_approvers or set(),
            require_unanimous=require_unanimous,
            auto_approve_after=auto_approve_after,
            context=context or {},
            on_approval=self._handle_gate_approval,
            on_rejection=self._handle_gate_rejection,
        )
        
        self.gates[gate.gate_id] = gate
        
        if self._on_gate_created:
            self._on_gate_created(gate)
        
        return gate
    
    def get_gate(self, gate_id: str) -> Optional[ApprovalGate]:
        """Retrieve a gate by ID."""
        return self.gates.get(gate_id)
    
    def get_pending_gates(self) -> List[ApprovalGate]:
        """Get all gates waiting for approval."""
        return [g for g in self.gates.values() if g.status == GateStatus.PENDING]
    
    def record_decision(
        self,
        gate_id: str,
        approver_id: str,
        decision: ApprovalDecision,
        comment: Optional[str] = None,
    ) -> None:
        """
        Record an approver's decision on a gate.
        
        Args:
            gate_id: ID of the gate
            approver_id: ID of the approver
            decision: Their decision
            comment: Optional comment
        """
        gate = self.get_gate(gate_id)
        if not gate:
            raise ValueError(f"Gate {gate_id} not found")
        
        gate.add_decision(approver_id, decision, comment)
        
        if gate.is_resolved() and self._on_gate_resolved:
            self._on_gate_resolved(gate)
    
    def _handle_gate_approval(self, gate: ApprovalGate) -> None:
        """Handle gate approval."""
        # Workflow can continue
        pass
    
    def _handle_gate_rejection(self, gate: ApprovalGate) -> None:
        """Handle gate rejection."""
        # Workflow must stop or take alternative action
        pass
    
    def set_gate_created_callback(self, callback: Callable[[ApprovalGate], None]) -> None:
        """Set callback for when a gate is created."""
        self._on_gate_created = callback
    
    def set_gate_resolved_callback(self, callback: Callable[[ApprovalGate], None]) -> None:
        """Set callback for when a gate is resolved."""
        self._on_gate_resolved = callback
