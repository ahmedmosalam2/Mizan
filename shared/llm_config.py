"""
LLM Configuration — Unified model config with seed control for fair benchmarking.

Ensures all framework adapters use the same model, temperature, and seeds
so comparisons are fair. Loads from environment variables with sensible defaults.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, Optional
import os
from dotenv import load_dotenv


class Environment(Enum):
    """Execution environments."""

    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"
    TEST = "test"
    BENCHMARK = "benchmark"


@dataclass
class LLMConfig:
    """LLM configuration for consistent benchmarking."""

    # Model selection
    provider: str = "openrouter"
    model: str = "meta-llama/llama-3.3-70b-instruct"
    temperature: float = 0.7
    max_tokens: int = 4096

    # API credentials
    api_key: str = ""
    api_base: Optional[str] = None

    # Reproducibility
    seed: int = 42
    top_p: float = 1.0

    # Cost tracking
    enable_cost_tracking: bool = True

    # Rate limiting
    max_retries: int = 5
    retry_backoff_base: float = 2.0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dict for passing to adapters."""
        return {
            "provider": self.provider,
            "model": self.model,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
            "api_key": self.api_key,
            "api_base": self.api_base,
            "seed": self.seed,
            "top_p": self.top_p,
        }


@dataclass
class ComplianceConfig:
    """Compliance and safety configuration."""

    enable_pii_detection: bool = True
    pii_redaction_mode: str = "hash"  # "hash", "mask", "redact"
    enable_audit_logging: bool = True
    audit_log_retention_days: int = 1095  # 3 years
    enable_consent_validation: bool = True
    supported_jurisdictions: list = field(default_factory=lambda: ["SA", "EG"])


@dataclass
class ObservabilityConfig:
    """Observability configuration."""

    enable_tracing: bool = True
    trace_level: str = "full"  # "full", "summary", "errors_only"
    enable_metrics: bool = True
    enable_audit_logs: bool = True
    langfuse_public_key: str = ""
    langfuse_secret_key: str = ""
    langfuse_host: str = "http://localhost:3000"


@dataclass
class MizanConfig:
    """Top-level configuration for the Mizan benchmark."""

    environment: Environment = Environment.BENCHMARK
    llm: LLMConfig = field(default_factory=LLMConfig)
    compliance: ComplianceConfig = field(default_factory=ComplianceConfig)
    observability: ObservabilityConfig = field(default_factory=ObservabilityConfig)

    # Benchmark settings
    mock_server_url: str = "http://localhost:8100"
    default_timeout_seconds: float = 120.0
    default_repeat_count: int = 3

    @classmethod
    def from_env(cls) -> "MizanConfig":
        """Load configuration from environment variables."""
        load_dotenv()
        config = cls()

        # Environment
        env = os.getenv("MIZAN_ENV", "benchmark").lower()
        config.environment = Environment(env)

        # LLM
        config.llm.provider = os.getenv("MIZAN_LLM_PROVIDER", config.llm.provider)
        config.llm.model = os.getenv("MIZAN_LLM_MODEL", config.llm.model)
        config.llm.api_key = os.getenv("OPENROUTER_API_KEY", "")
        if not config.llm.api_key:
            config.llm.api_key = os.getenv("GROQ_API_KEY", "")
            if config.llm.api_key:
                config.llm.provider = "groq"
        config.llm.seed = int(os.getenv("MIZAN_SEED", "42"))

        # Mock server
        config.mock_server_url = os.getenv(
            "MIZAN_MOCK_URL", config.mock_server_url
        )

        # Observability
        config.observability.langfuse_public_key = os.getenv(
            "LANGFUSE_PUBLIC_KEY", ""
        )
        config.observability.langfuse_secret_key = os.getenv(
            "LANGFUSE_SECRET_KEY", ""
        )

        return config

    def to_dict(self) -> Dict[str, Any]:
        """Convert config to dict for logging."""
        return {
            "environment": self.environment.value,
            "llm_provider": self.llm.provider,
            "llm_model": self.llm.model,
            "seed": self.llm.seed,
            "mock_server_url": self.mock_server_url,
            "compliance_enabled": self.compliance.enable_pii_detection,
            "tracing_enabled": self.observability.enable_tracing,
        }


# ── Global config ────────────────────────────────────────────────

_config: Optional[MizanConfig] = None


def get_config() -> MizanConfig:
    """Get global configuration (lazy-loaded from env)."""
    global _config
    if _config is None:
        _config = MizanConfig.from_env()
    return _config


def set_config(config: MizanConfig) -> None:
    """Set global configuration (for testing)."""
    global _config
    _config = config
