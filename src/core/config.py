"""
Configuration and environment setup for the multi-agent framework.

This module provides:
- Default configurations
- Environment variable loading
- Config validation
"""

from dataclasses import dataclass, field
from typing import Optional, Dict, Any
import os
from enum import Enum


class Environment(Enum):
    """Execution environments."""
    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"
    TEST = "test"


class LogLevel(Enum):
    """Logging levels."""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


@dataclass
class FrameworkConfig:
    """Configuration for framework adapters."""
    framework_type: str  # "crewai", "langgraph", "agno"
    max_retries: int = 3
    timeout_seconds: int = 300
    enable_cache: bool = True


@dataclass
class LLMConfig:
    """LLM configuration."""
    default_model: str = "gpt-4"
    temperature: float = 0.7
    max_tokens: int = 2048
    api_key: Optional[str] = None
    api_base: Optional[str] = None
    enable_cost_tracking: bool = True


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
    metrics_export_interval_seconds: int = 60
    enable_audit_logs: bool = True


@dataclass
class Config:
    """Main configuration object."""
    environment: Environment = Environment.DEVELOPMENT
    log_level: LogLevel = LogLevel.INFO
    
    # Framework
    framework: FrameworkConfig = field(default_factory=lambda: FrameworkConfig("langgraph"))
    
    # LLM
    llm: LLMConfig = field(default_factory=LLMConfig)
    
    # Compliance
    compliance: ComplianceConfig = field(default_factory=ComplianceConfig)
    
    # Observability
    observability: ObservabilityConfig = field(default_factory=ObservabilityConfig)
    
    # Features
    enable_approval_gates: bool = True
    enable_human_in_the_loop: bool = True
    
    @classmethod
    def from_env(cls) -> "Config":
        """Load configuration from environment variables."""
        config = cls()
        
        # Environment
        env = os.getenv("MIZAN_ENV", "development").lower()
        config.environment = Environment(env)
        
        # Log level
        log_level = os.getenv("MIZAN_LOG_LEVEL", "INFO").upper()
        config.log_level = LogLevel(log_level)
        
        # Framework
        fw_type = os.getenv("MIZAN_FRAMEWORK", "langgraph").lower()
        config.framework.framework_type = fw_type
        
        # LLM
        config.llm.api_key = os.getenv("OPENAI_API_KEY")
        config.llm.default_model = os.getenv("MIZAN_LLM_MODEL", "gpt-4")
        
        return config
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert config to dict for logging."""
        return {
            "environment": self.environment.value,
            "log_level": self.log_level.value,
            "framework": self.framework.framework_type,
            "llm_model": self.llm.default_model,
            "compliance_enabled": self.compliance.enable_pii_detection,
            "observability_enabled": self.observability.enable_tracing,
        }


# Global config instance
_config: Optional[Config] = None


def get_config() -> Config:
    """Get global configuration."""
    global _config
    if _config is None:
        _config = Config.from_env()
    return _config


def set_config(config: Config) -> None:
    """Set global configuration."""
    global _config
    _config = config


# Default configurations for common scenarios

def get_development_config() -> Config:
    """Get development configuration."""
    config = Config()
    config.environment = Environment.DEVELOPMENT
    config.log_level = LogLevel.DEBUG
    config.llm.enable_cost_tracking = False  # Don't stress about costs in dev
    return config


def get_production_config() -> Config:
    """Get production configuration."""
    config = Config()
    config.environment = Environment.PRODUCTION
    config.log_level = LogLevel.WARNING
    config.compliance.enable_pii_detection = True
    config.compliance.enable_audit_logging = True
    config.observability.enable_tracing = True
    return config


def get_benchmark_config() -> Config:
    """Get configuration for benchmarking."""
    config = Config()
    config.environment = Environment.TEST
    config.log_level = LogLevel.INFO
    config.observability.enable_tracing = True
    config.observability.enable_metrics = True
    config.llm.enable_cost_tracking = True
    return config
