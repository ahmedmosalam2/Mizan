"""
CrewAI Adapter — Settings
=========================
Adapter-specific settings فقط.
بيانات الـ scenarios (products, channels, ROAS) موجودة في:
    benchmarks/scenarios/test_data.py
"""

from benchmarks.adapters.crewai.enums import LLMProvider


# ── LLM Defaults ─────────────────────────────────────────────────
DEFAULT_PROVIDER = LLMProvider.GROQ
DEFAULT_MODEL    = "llama-3.3-70b-versatile"
DEFAULT_MODE     = "full"

# ── Retry & Fallback ──────────────────────────────────────────────
MAX_RETRY_ATTEMPTS       = 3
FALLBACK_SMS_ON_REJECTED = True

# ── Budget & Approval ─────────────────────────────────────────────
BUDGET_REALLOCATION_THRESHOLD = 0.20   # 20% → يحتاج موافقة

# ── Content Guardrails ────────────────────────────────────────────
MIN_ARABIC_CHARS        = 15
RAMADAN_FORBIDDEN_WORDS = ["كحول", "خمر", "مسكر", "alcohol", "wine", "beer"]

# ── Memory ────────────────────────────────────────────────────────
MIN_RECALL_SCORE = 0.5

# ── Knowledge / RAG ──────────────────────────────────────────────
RAG_RESULTS_LIMIT   = 5
RAG_SCORE_THRESHOLD = 0.35
