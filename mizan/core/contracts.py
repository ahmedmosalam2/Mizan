"""Canonical, framework-neutral contracts shared by the Mizan AUT and benchmark.

The models in this module are the only payloads that may cross the business
system, runtime-adapter, tool-gateway, evaluator, and persistence boundaries.
They intentionally capture observable execution data only; hidden model
reasoning is never a contract field.
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Literal
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field, field_validator


def utc_now() -> datetime:
    """Return an explicit UTC timestamp for persisted contract events."""
    return datetime.now(timezone.utc)


class StrictModel(BaseModel):
    """Base model that rejects undeclared boundary fields."""

    model_config = ConfigDict(extra="forbid", validate_assignment=True, validate_default=True)


class ExecutionMode(str, Enum):
    """Whether an invocation is fixture-backed, sandboxed, or externally real."""

    TEST = "test"
    SANDBOX = "sandbox"
    REAL = "real"


class ErrorCode(str, Enum):
    VALIDATION_ERROR = "validation_error"
    TOOL_ERROR = "tool_error"
    TIMEOUT = "timeout"
    RATE_LIMIT = "rate_limit"
    AUTH_ERROR = "auth_error"
    PERMISSION_DENIED = "permission_denied"
    COMPLIANCE_BLOCK = "compliance_block"
    APPROVAL_REQUIRED = "approval_required"
    DATABASE_ERROR = "database_error"
    MODEL_ERROR = "model_error"
    FRAMEWORK_ERROR = "framework_error"
    IDEMPOTENCY_CONFLICT = "idempotency_conflict"
    UNKNOWN_ERROR = "unknown_error"


class RunStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    BLOCKED = "blocked"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    TIMED_OUT = "timed_out"
    CANCELLED = "cancelled"


class CampaignStatus(str, Enum):
    DRAFT = "draft"
    PLANNING = "planning"
    AWAITING_APPROVAL = "awaiting_approval"
    APPROVED = "approved"
    CONTENT_GENERATION = "content_generation"
    COMPLIANCE_CHECK = "compliance_check"
    READY_TO_DEPLOY = "ready_to_deploy"
    DEPLOYING = "deploying"
    PARTIALLY_DEPLOYED = "partially_deployed"
    DEPLOYED = "deployed"
    ANALYZING = "analyzing"
    OPTIMIZATION_PROPOSED = "optimization_proposed"
    COMPLETED = "completed"
    FAILED = "failed"


class ApprovalStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXPIRED = "expired"
    CANCELLED = "cancelled"


class ToolAction(str, Enum):
    READ = "read"
    WRITE = "write"
    EXECUTE = "execute"
    REQUEST_APPROVAL = "request_approval"


class RiskLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ErrorRecord(StrictModel):
    """Sanitized, classifiable error information returned across boundaries."""

    code: ErrorCode
    message: str = Field(min_length=1, max_length=1_000)
    retryable: bool = False
    retry_after_seconds: float | None = Field(default=None, ge=0)
    details: dict[str, Any] = Field(default_factory=dict)


class TenantContext(StrictModel):
    """Mandatory scoped identity for every business and tool operation."""

    company_id: str = Field(min_length=1, max_length=128)
    actor_id: str = Field(min_length=1, max_length=128)
    actor_roles: set[str] = Field(default_factory=set)
    execution_mode: ExecutionMode
    correlation_id: UUID = Field(default_factory=uuid4)
    trace_id: str | None = Field(default=None, max_length=128)


class ToolPermission(StrictModel):
    tool_name: str = Field(min_length=1, max_length=128)
    action: ToolAction
    required_roles: set[str] = Field(default_factory=set)


class ToolRequest(StrictModel):
    """A permissioned, idempotent request through the tool gateway."""

    request_id: UUID = Field(default_factory=uuid4)
    run_id: UUID
    tenant: TenantContext
    campaign_id: str = Field(min_length=1, max_length=128)
    task_id: str = Field(min_length=1, max_length=128)
    agent_id: str = Field(min_length=1, max_length=128)
    tool_name: str = Field(min_length=1, max_length=128)
    action: ToolAction
    arguments: dict[str, Any] = Field(default_factory=dict)
    idempotency_key: str = Field(min_length=8, max_length=255)
    timeout_seconds: float = Field(default=30, gt=0, le=600)
    max_retries: int = Field(default=0, ge=0, le=5)
    requested_at: datetime = Field(default_factory=utc_now)


class ToolResponse(StrictModel):
    request_id: UUID
    success: bool
    result: dict[str, Any] = Field(default_factory=dict)
    error: ErrorRecord | None = None
    duration_ms: float = Field(ge=0)
    retry_count: int = Field(default=0, ge=0)
    completed_at: datetime = Field(default_factory=utc_now)

    @field_validator("error")
    @classmethod
    def failure_has_error(cls, value: ErrorRecord | None, info: Any) -> ErrorRecord | None:
        if info.data.get("success") is False and value is None:
            raise ValueError("Failed tool responses must include a classified error")
        return value


class TaskInput(StrictModel):
    """Stable input presented to an agent for one atomic task."""

    payload: dict[str, Any] = Field(default_factory=dict)
    locale: Literal["ar-SA", "ar-EG", "en"] | None = None
    market: Literal["KSA", "EG"] | None = None
    fixture_id: str | None = Field(default=None, max_length=128)


class TaskOutput(StrictModel):
    """Validated task outcome, separated from transport or tracing concerns."""

    status: RunStatus
    payload: dict[str, Any] = Field(default_factory=dict)
    errors: list[ErrorRecord] = Field(default_factory=list)
    approval_id: UUID | None = None


class EvaluationMetric(StrictModel):
    name: str = Field(min_length=1, max_length=128)
    value: float
    unit: str = Field(min_length=1, max_length=64)
    raw_value: float | None = None


class AtomicTask(StrictModel):
    """Versioned, framework-agnostic definition of one benchmarkable task."""

    task_id: str = Field(pattern=r"^[A-Z][A-Z0-9-]{2,127}$")
    version: str = Field(pattern=r"^\d+\.\d+\.\d+$")
    objective: str = Field(min_length=1, max_length=4_000)
    input: TaskInput
    allowed_tools: set[str] = Field(default_factory=set)
    forbidden_behavior: list[str] = Field(default_factory=list)
    success_criteria: list[str] = Field(min_length=1)
    evaluation_metrics: list[EvaluationMetric] = Field(min_length=1)
    difficulty: float = Field(ge=0, le=1)
    deterministic_fixture_id: str | None = Field(default=None, max_length=128)
    timeout_seconds: float = Field(default=120, gt=0, le=600)
    max_steps: int = Field(default=12, ge=1, le=100)


class AgentRequest(StrictModel):
    run_id: UUID = Field(default_factory=uuid4)
    tenant: TenantContext
    campaign_id: str = Field(min_length=1, max_length=128)
    task: AtomicTask
    agent_id: str = Field(min_length=1, max_length=128)
    permissions: list[ToolPermission] = Field(default_factory=list)
    model: str = Field(min_length=1, max_length=256)
    model_version: str = Field(min_length=1, max_length=256)
    temperature: float = Field(ge=0, le=2)
    token_budget: int = Field(gt=0, le=1_000_000)


class AgentResponse(StrictModel):
    run_id: UUID
    status: RunStatus
    output: TaskOutput
    tool_responses: list[ToolResponse] = Field(default_factory=list)
    observable_events: list[dict[str, Any]] = Field(default_factory=list)
    input_tokens: int = Field(default=0, ge=0)
    output_tokens: int = Field(default=0, ge=0)
    latency_ms: float = Field(default=0, ge=0)
    cost_usd: float = Field(default=0, ge=0)


class ApprovalRequest(StrictModel):
    approval_id: UUID = Field(default_factory=uuid4)
    tenant: TenantContext
    campaign_id: str = Field(min_length=1, max_length=128)
    task_id: str = Field(min_length=1, max_length=128)
    requested_action: str = Field(min_length=1, max_length=2_000)
    reason: str = Field(min_length=1, max_length=2_000)
    risk: RiskLevel
    requested_by: str = Field(min_length=1, max_length=128)
    required_roles: set[str] = Field(min_length=1)
    requested_at: datetime = Field(default_factory=utc_now)


class ApprovalDecision(StrictModel):
    approval_id: UUID
    status: ApprovalStatus
    approved_by: str | None = Field(default=None, max_length=128)
    reason: str | None = Field(default=None, max_length=2_000)
    decided_at: datetime = Field(default_factory=utc_now)

    @field_validator("approved_by")
    @classmethod
    def approver_is_required_for_decision(cls, value: str | None, info: Any) -> str | None:
        if info.data.get("status") in {ApprovalStatus.APPROVED, ApprovalStatus.REJECTED} and not value:
            raise ValueError("An approved or rejected decision requires an approver")
        return value


class Campaign(StrictModel):
    campaign_id: str = Field(min_length=1, max_length=128)
    company_id: str = Field(min_length=1, max_length=128)
    name: str = Field(min_length=1, max_length=256)
    market_budgets: dict[Literal["KSA", "EG"], float] = Field(default_factory=dict)
    status: CampaignStatus = CampaignStatus.DRAFT
    created_at: datetime = Field(default_factory=utc_now)

    @field_validator("market_budgets")
    @classmethod
    def budgets_are_non_negative(cls, value: dict[str, float]) -> dict[str, float]:
        if any(amount < 0 for amount in value.values()):
            raise ValueError("Campaign budgets cannot be negative")
        return value


class CampaignResult(StrictModel):
    campaign_id: str
    company_id: str
    status: CampaignStatus
    task_results: list[AgentResponse] = Field(default_factory=list)
    approvals: list[ApprovalDecision] = Field(default_factory=list)
    metrics: list[EvaluationMetric] = Field(default_factory=list)


class ExperimentProvenance(StrictModel):
    experiment_id: UUID = Field(default_factory=uuid4)
    git_commit: str = Field(min_length=7, max_length=128)
    framework: str = Field(min_length=1, max_length=128)
    framework_version: str = Field(min_length=1, max_length=128)
    model: str = Field(min_length=1, max_length=256)
    model_version: str = Field(min_length=1, max_length=256)
    dataset_version: str = Field(min_length=1, max_length=128)
    task_set_version: str = Field(min_length=1, max_length=128)
    configuration_hash: str = Field(min_length=8, max_length=256)
    environment: ExecutionMode
    seed: int
    run_count: int = Field(ge=1)
    created_at: datetime = Field(default_factory=utc_now)


class EvaluationResult(StrictModel):
    task_id: str
    run_id: UUID
    success: bool
    metrics: list[EvaluationMetric] = Field(default_factory=list)
    safety_violations: list[ErrorRecord] = Field(default_factory=list)
    score: float = Field(ge=0, le=1)
    evaluated_at: datetime = Field(default_factory=utc_now)


class BenchmarkResult(StrictModel):
    provenance: ExperimentProvenance
    evaluations: list[EvaluationResult] = Field(default_factory=list)
    status: RunStatus
    completed_at: datetime | None = None


class CampaignStateMachine:
    """Single source of truth for legal AUT campaign transitions."""

    _ALLOWED: dict[CampaignStatus, set[CampaignStatus]] = {
        CampaignStatus.DRAFT: {CampaignStatus.PLANNING, CampaignStatus.FAILED},
        CampaignStatus.PLANNING: {
            CampaignStatus.AWAITING_APPROVAL,
            CampaignStatus.APPROVED,
            CampaignStatus.FAILED,
        },
        CampaignStatus.AWAITING_APPROVAL: {
            CampaignStatus.PLANNING,
            CampaignStatus.APPROVED,
            CampaignStatus.FAILED,
        },
        CampaignStatus.APPROVED: {CampaignStatus.CONTENT_GENERATION, CampaignStatus.FAILED},
        CampaignStatus.CONTENT_GENERATION: {CampaignStatus.COMPLIANCE_CHECK, CampaignStatus.FAILED},
        CampaignStatus.COMPLIANCE_CHECK: {
            CampaignStatus.AWAITING_APPROVAL,
            CampaignStatus.READY_TO_DEPLOY,
            CampaignStatus.FAILED,
        },
        CampaignStatus.READY_TO_DEPLOY: {CampaignStatus.DEPLOYING, CampaignStatus.FAILED},
        CampaignStatus.DEPLOYING: {
            CampaignStatus.PARTIALLY_DEPLOYED,
            CampaignStatus.DEPLOYED,
            CampaignStatus.FAILED,
        },
        CampaignStatus.PARTIALLY_DEPLOYED: {
            CampaignStatus.DEPLOYING,
            CampaignStatus.ANALYZING,
            CampaignStatus.FAILED,
        },
        CampaignStatus.DEPLOYED: {CampaignStatus.ANALYZING, CampaignStatus.FAILED},
        CampaignStatus.ANALYZING: {
            CampaignStatus.OPTIMIZATION_PROPOSED,
            CampaignStatus.COMPLETED,
            CampaignStatus.FAILED,
        },
        CampaignStatus.OPTIMIZATION_PROPOSED: {
            CampaignStatus.AWAITING_APPROVAL,
            CampaignStatus.COMPLETED,
            CampaignStatus.FAILED,
        },
        CampaignStatus.COMPLETED: set(),
        CampaignStatus.FAILED: set(),
    }

    @classmethod
    def can_transition(cls, current: CampaignStatus, target: CampaignStatus) -> bool:
        return target in cls._ALLOWED[current]

    @classmethod
    def require_transition(cls, current: CampaignStatus, target: CampaignStatus) -> None:
        if not cls.can_transition(current, target):
            raise ValueError(f"Illegal campaign state transition: {current.value} -> {target.value}")
