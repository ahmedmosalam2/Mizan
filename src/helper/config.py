import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    """Application configuration."""
    
    # Database - supports both PostgreSQL (production) and SQLite (dev fallback)
    DATABASE_URL = os.getenv(
        "DATABASE_URL",
        "postgresql+asyncpg://mizan_user:mizan_secure_pass_2026@localhost:5432/mizan_campaigns"
    )
    
    # Ensure the URL uses the async driver
    if DATABASE_URL.startswith("postgresql://"):
        DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://", 1)
    
    # SQLite fallback for development (when PostgreSQL isn't available)
    SQLITE_FALLBACK = os.getenv("SQLITE_FALLBACK", "false").lower() == "true"
    if SQLITE_FALLBACK:
        DATABASE_URL = "sqlite+aiosqlite:///./mizan_dev.db"
    
    # API
    API_HOST = os.getenv("API_HOST", "0.0.0.0")
    API_PORT = int(os.getenv("API_PORT", "8000"))
    DEBUG = os.getenv("DEBUG", "false").lower() == "true"
    
    # LLM
    GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
    OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
    
    @staticmethod
    def get_db_url():
        return Config.DATABASE_URL