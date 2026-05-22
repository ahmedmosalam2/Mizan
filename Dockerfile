# ══════════════════════════════════════════════════════════════
# Mizan — AI Agentic Framework Benchmark
# Multi-stage Docker build for reproducible environments
# ══════════════════════════════════════════════════════════════

FROM python:3.11-slim AS base

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# ── Dependencies stage ──────────────────────────────────────
FROM base AS deps

COPY requirements.txt pyproject.toml ./
RUN pip install --no-cache-dir -r requirements.txt

# ── Application stage ───────────────────────────────────────
FROM deps AS app

COPY src/ ./src/
COPY .env.example .env.example
COPY README.md LICENSE ./

# Create non-root user
RUN groupadd -r mizan && useradd -r -g mizan -d /app mizan \
    && mkdir -p /app/benchmark_results \
    && chown -R mizan:mizan /app

USER mizan

# Expose API port
EXPOSE 8001

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8001/ || exit 1

# Default: run the API server
CMD ["python", "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8001", "--app-dir", "src"]
