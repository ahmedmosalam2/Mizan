import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    """Application configuration."""
    
    # Database
    DATABASE_URL = os.getenv(
        "DATABASE_URL",
        "postgresql://mizan_user:mizan_secure_pass_2026@localhost:5432/mizan_campaigns"
    )
    
    # API
    API_HOST = os.getenv("API_HOST", "0.0.0.0")
    API_PORT = int(os.getenv("API_PORT", "8000"))
    DEBUG = os.getenv("DEBUG", "false").lower() == "true"
    
    # LLM
    GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
    
    @staticmethod
    def get_db_url():
        return Config.DATABASE_URL