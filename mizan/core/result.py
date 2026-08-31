"""
Core Result & Evaluation Models for Mizan.

Defines the structured output, metric aggregations, and per-dimension scores.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from mizan.core.message import AgentMessage, ToolCallRecord
from mizan.core.task import TaskCategory, TaskStatus


class DimensionScore(BaseModel):
    """Mathematical score for one benchmark dimension."""
    dimension: TaskCategory
    score: float = Field(ge=0.0, le=10.0, description="Normalized score 0.0 to 10.0")
    weight: float = Field(ge=0.0, le=1.0)
    weighted_score: float = 0.0
    sub_scores: Dict[str, float] = Field(default_factory=dict)
    feedback: List[str] = Field(default_factory=list)


class TaskResult(BaseModel):
    """Outcome of a single atomic task execution."""
    task_id: str
    run_id: str
    framework_name: str
    model_name: str
    category: TaskCategory
    status: TaskStatus
    output_payload: Dict[str, Any] = Field(default_factory=dict)
    messages: List[AgentMessage] = Field(default_factory=list)
    tool_calls: List[ToolCallRecord] = Field(default_factory=list)
    duration_ms: float = 0.0
    tokens_prompt: int = 0
    tokens_completion: int = 0
    tokens_total: int = 0
    cost_usd: float = 0.0
    error_message: Optional[str] = None
    started_at: str = Field(default_factory=lambda: datetime.now().isoformat())
    finished_at: Optional[str] = None


class FrameworkRunResult(BaseModel):
    """Complete aggregated evaluation report for one framework across all tasks."""
    run_id: str
    framework_name: str
    framework_version: str = "1.0.0"
    model_name: str
    total_score: float = Field(default=0.0, ge=0.0, le=10.0)
    dimension_scores: Dict[str, DimensionScore] = Field(default_factory=dict)
    task_results: List[TaskResult] = Field(default_factory=list)
    tasks_passed: int = 0
    tasks_failed: int = 0
    total_duration_ms: float = 0.0
    total_tokens: int = 0
    total_cost_usd: float = 0.0
    evaluated_at: str = Field(default_factory=lambda: datetime.now().isoformat())
