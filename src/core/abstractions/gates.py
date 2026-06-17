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
    
    gate_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    gate_type: str = ""
    action_description: str = ""
    required_approvers: Set[str] = field(default_factory=set)
    optional_approvers: Set[str] = field(default_factory=set)
    
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

    
    def __init__(self):

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
