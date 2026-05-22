"""
Mizan — AI Agentic Framework Benchmark for MENA E-Commerce.

Entry point for the benchmark API.
"""
import os
import logging

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from adapters.driving.api.routes.benchmark import router as benchmark_router
from adapters.driving.api.routes.llm_gateway import router as llm_gateway_router

logger = logging.getLogger("mizan.api")

app = FastAPI(
    title="Mizan Benchmark",
    description="Benchmark platform comparing 20 AI agentic frameworks on a real-world MENA e-commerce scenario.",
    version="1.0.0",
)

# ═══════════════════════════════════════════════════════════════
# Security: CORS from environment variable
# ═══════════════════════════════════════════════════════════════
_cors_origins = os.getenv("CORS_ORIGINS", "*").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in _cors_origins],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ═══════════════════════════════════════════════════════════════
# Global Error Handler — never leak raw stack traces to clients
# ═══════════════════════════════════════════════════════════════
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error("Unhandled error on %s %s: %s", request.method, request.url.path, exc, exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error. Check server logs for details."},
    )


app.include_router(benchmark_router)
app.include_router(llm_gateway_router)


@app.get("/")
async def root():
    return {
        "app": "Mizan Benchmark",
        "description": "AI Agentic Framework Benchmark for MENA E-Commerce",
        "version": "1.0.0",
        "docs": "/docs",
    }


@app.get("/health")
async def health():
    """Health check endpoint for Docker and load balancers."""
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8001, reload=True)
