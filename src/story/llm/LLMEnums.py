from enum import Enum


class LLMProvider(str, Enum):
    GROQ       = "groq"
    OPENROUTER = "openrouter"
    OPENAI     = "openai"
    GEMINI     = "gemini"
    ANTHROPIC  = "anthropic"
    OLLAMA     = "ollama"
    MOCK       = "mock"


class LLMModel(str, Enum):
    # Groq (free)
    LLAMA_70B     = "llama-3.3-70b-versatile"
    LLAMA_8B      = "llama-3.1-8b-instant"
    MIXTRAL_8X7B  = "mixtral-8x7b-32768"

    # OpenRouter (free tier)
    LLAMA_3_3_70B_FREE = "meta-llama/llama-3.3-70b-instruct:free"
    DEEPSEEK_R1     = "deepseek/deepseek-r1:free"
    GEMMA3_27B      = "google/gemma-3-27b-it:free"

    # Google
    GEMINI_FLASH  = "gemini-2.0-flash"
    GEMINI_PRO    = "gemini-1.5-pro"
