from enum import Enum


class LLMProvider(str, Enum):
    GROQ     = "groq"
    OPENAI   = "openai"
    GEMINI   = "google"
    ANTHROPIC = "anthropic"
    OLLAMA   = "ollama"
    OPENROUTER = "openrouter"


class AdapterMode(str, Enum):
    FULL  = "full"
    CLEAN = "clean"


class DeployChannel(str, Enum):
    META_ADS  = "Meta Ads"
    SNAPCHAT  = "Snapchat"
    GOOGLE    = "Google Ads"
    WHATSAPP  = "WhatsApp"
    EMAIL     = "Email"
    SMS       = "SMS"


class ChannelError(str, Enum):
    RATE_LIMIT        = "API_RATE_LIMIT"
    TEMPLATE_REJECTED = "TEMPLATE_REJECTED"
    AUTH_FAILED       = "AUTH_FAILED"
    UNKNOWN           = "UNKNOWN"


class RiskLevel(str, Enum):
    CRITICAL = "critical"
    HIGH     = "high"
    MEDIUM   = "medium"
    LOW      = "low"


class Market(str, Enum):
    KSA  = "KSA"
    EG   = "EG"
    BOTH = "both"


class OrchestrationMode(str, Enum):
    SEQUENTIAL   = "sequential"
    PARALLEL     = "parallel"
    HIERARCHICAL = "hierarchical"
