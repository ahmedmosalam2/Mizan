"""Typed, non-secret configuration contracts for Mizan execution.

Values are resolved by the application layer in this order: explicit CLI/API
input, environment variables or secret references, environment configuration,
then suite/task defaults. This module deliberately contains no environment I/O.
"""

from __future__ import annotations

from pydantic import Field, field_validator

from mizan.core.contracts import ExecutionMode, StrictModel


class RetryPolicy(StrictModel):
    max_retries: int = Field(default=2, ge=0, le=5)
    initial_backoff_seconds: float = Field(default=1, gt=0, le=60)
    max_backoff_seconds: float = Field(default=30, gt=0, le=300)
    retryable_error_codes: set[str] = Field(
        default_factory=lambda: {"rate_limit", "timeout", "tool_error"}
    )

    @field_validator("max_backoff_seconds")
    @classmethod
    def backoff_is_not_smaller_than_initial(cls, value: float, info: object) -> float:
        initial = getattr(info, "data", {}).get("initial_backoff_seconds")
        if initial is not None and value < initial:
            raise ValueError("max_backoff_seconds cannot be less than initial_backoff_seconds")
        return value


class ModelConfiguration(StrictModel):
    provider: str = Field(min_length=1, max_length=64)
    model: str = Field(min_length=1, max_length=256)
    model_version: str = Field(min_length=1, max_length=256)
    temperature: float = Field(default=0, ge=0, le=2)
    token_budget: int = Field(default=8_000, gt=0, le=1_000_000)


class RuntimeConfiguration(StrictModel):
    execution_mode: ExecutionMode
    request_timeout_seconds: float = Field(default=120, gt=0, le=600)
    maximum_steps: int = Field(default=12, ge=1, le=100)
    retry_policy: RetryPolicy = Field(default_factory=RetryPolicy)
    redact_observability_payloads: bool = True
    allow_external_channel_dispatch: bool = False

    @field_validator("allow_external_channel_dispatch")
    @classmethod
    def real_mode_is_required_for_external_dispatch(cls, value: bool, info: object) -> bool:
        execution_mode = getattr(info, "data", {}).get("execution_mode")
        if value and execution_mode is not ExecutionMode.REAL:
            raise ValueError("External channel dispatch is permitted only in real mode")
        return value


class BenchmarkConfiguration(StrictModel):
    suite_id: str = Field(min_length=1, max_length=128)
    suite_version: str = Field(pattern=r"^\d+\.\d+\.\d+$")
    dataset_version: str = Field(min_length=1, max_length=128)
    seed: int
    trials_per_task: int = Field(default=3, ge=1, le=100)
    runtime: RuntimeConfiguration
    model: ModelConfiguration
