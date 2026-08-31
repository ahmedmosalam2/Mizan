"""
Core Event & Audit Models for Mizan.

Defines the event lifecycle and immutable compliance audit log entries.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Dict, Optional
from pydantic import BaseModel, Field


class EventType(str, Enum):
    TASK_STARTED = "task_started"
    TASK_COMPLETED = "task_completed"
    TASK_FAILED = "task_failed"
    TOOL_CALLED = "tool_called"
    PII_DETECTED = "pii_detected"
    PII_REDACTED = "pii_redacted"
    CONSENT_VERIFIED = "consent_verified"
    CONSENT_BLOCKED = "consent_blocked"
    GATE_CREATED = "gate_created"
    GATE_RESOLVED = "gate_resolved"
    ERROR_INJECTED = "error_injected"


class BenchmarkEvent(BaseModel):
    """An event emitted during benchmark orchestration."""
    event_id: str
    event_type: EventType
    run_id: str
    task_id: Optional[str] = None
    agent_name: Optional[str] = None
    payload: Dict[str, Any] = Field(default_factory=dict)
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat())


class AuditLogEvent(BaseModel):
    """Immutable regulatory compliance audit record (PDPL / Law 151)."""
    audit_id: str
    customer_id: str
    action: str
    channel: str
    jurisdiction: str  # 'KSA_PDPL' or 'EG_LAW_151'
    details: Dict[str, Any] = Field(default_factory=dict)
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat())
