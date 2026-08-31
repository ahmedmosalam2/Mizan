"""
Core Task Models & TaskContract Specification for Mizan.

Defines the formal schema for Atomic Benchmark Tasks across the 7 evaluation dimensions.
Adheres strictly to deterministic inputs, expected behaviors, and mathematical rubrics.
"""

from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class TaskCategory(str, Enum):
    ORCHESTRATION = "orchestration"
    TOOL_USE = "tool_use"
    SAFETY = "safety"
    HUMAN_IN_THE_LOOP = "hitl"
    MEMORY = "memory"
    OBSERVABILITY = "observability"
    MULTIMODAL = "multimodal"


class TaskStatus(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    BLOCKED_HITL = "blocked_hitl"
    SKIPPED = "skipped"


class TaskInput(BaseModel):
    """Immutable input payload presented to the agent for task execution."""
    brief: Dict[str, Any] = Field(default_factory=dict, description="Campaign brief or customer context")
    market: str = Field(default="KSA", description="Target market: 'KSA' or 'EG'")
    channel: Optional[str] = Field(default=None, description="Target channel: meta_ads, snapchat, whatsapp, etc.")
    session_id: Optional[str] = Field(default=None, description="Active session ID for stateful tasks")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Auxiliary parameters")


class ExpectedOutcome(BaseModel):
    """Ground-truth expected behavior and assertions for deterministic evaluation."""
    required_tools: List[str] = Field(default_factory=list, description="Tools that MUST be invoked")
    prohibited_tools: List[str] = Field(default_factory=list, description="Tools that MUST NOT be invoked")
    expected_state_transitions: List[str] = Field(default_factory=list, description="State changes expected")
    must_detect_pii_types: List[str] = Field(default_factory=list, description="PII types requiring redaction")
    must_block_customer_ids: List[str] = Field(default_factory=list, description="Customers lacking consent")
    expected_output_schema: Dict[str, Any] = Field(default_factory=dict, description="JSON schema for final output")


class EvaluationCriterion(BaseModel):
    """Sub-criterion for mathematical scoring."""
    name: str
    weight: float = Field(ge=0.0, le=1.0)
    description: str
    pass_condition: str


class TaskContract(BaseModel):
    """
    Formal Task Contract.
    Every atomic benchmark task MUST be an instance of TaskContract.
    """
    task_id: str = Field(..., description="Unique immutable ID, e.g. 'SAFE-PII-001'")
    version: str = Field(default="1.0.0", description="Semantic version of task definition")
    category: TaskCategory = Field(..., description="Benchmark dimension")
    title: str = Field(..., description="Human-readable title")
    description: str = Field(..., description="Detailed task prompt / instructions")
    assigned_agent_role: str = Field(..., description="Target scenario agent (e.g. 'ComplianceGuardian')")
    input_data: TaskInput = Field(default_factory=TaskInput)
    expected_outcome: ExpectedOutcome = Field(default_factory=ExpectedOutcome)
    rubric: List[EvaluationCriterion] = Field(default_factory=list)
    timeout_seconds: int = Field(default=120, ge=5, le=600)
    max_retries: int = Field(default=2, ge=0, le=5)
    requires_hitl: bool = Field(default=False)
