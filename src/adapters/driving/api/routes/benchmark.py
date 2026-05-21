"""
Benchmark API routes — trigger and view benchmark results via API.
"""
import os
from typing import List, Optional

from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel, Field

from benchmarks.runner import BenchmarkRunner
from benchmarks.scenarios.test_data import FRAMEWORKS_REGISTRY


router = APIRouter(prefix="/api/v1/benchmark", tags=["Benchmark"])


# ── Schemas ────────────────────────────────────────────────────────
class BenchmarkRequest(BaseModel):
    frameworks: List[str] = Field(
        default=["crewai"],
        description="Framework IDs to benchmark",
    )
    scenarios: Optional[List[str]] = Field(
        default=None,
        description="Scenario IDs to run (null = all 7)",
    )
    llm_provider: str = Field(default="groq")
    llm_model: str = Field(default="llama-3.3-70b-versatile")


class BenchmarkStatus(BaseModel):
    status: str
    message: str
    frameworks: List[str] = []


# ── State ──────────────────────────────────────────────────────────
_benchmark_status = {"running": False, "last_result": None}


# ── Endpoints ──────────────────────────────────────────────────────
@router.get("/frameworks")
async def list_frameworks():
    """List all 20 registered frameworks."""
    return {
        "frameworks": FRAMEWORKS_REGISTRY,
        "total": len(FRAMEWORKS_REGISTRY),
    }


@router.post("/run", response_model=BenchmarkStatus)
async def run_benchmark(request: BenchmarkRequest, background_tasks: BackgroundTasks):
    """Start a benchmark run in the background."""
    if _benchmark_status["running"]:
        raise HTTPException(status_code=409, detail="A benchmark is already running")

    # Validate framework IDs
    valid_ids = {fw["id"] for fw in FRAMEWORKS_REGISTRY}
    invalid = [f for f in request.frameworks if f not in valid_ids]
    if invalid:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown frameworks: {invalid}. Valid: {sorted(valid_ids)}",
        )

    async def _run():
        _benchmark_status["running"] = True
        try:
            runner = BenchmarkRunner(llm_config={
                "provider": request.llm_provider,
                "model": request.llm_model,
                "api_key": os.getenv("GROQ_API_KEY", ""),
            })
            result = await runner.run_all_frameworks(
                framework_ids=request.frameworks,
                scenarios=request.scenarios,
            )
            _benchmark_status["last_result"] = result
        finally:
            _benchmark_status["running"] = False

    background_tasks.add_task(_run)

    return BenchmarkStatus(
        status="started",
        message=f"Benchmark started for {len(request.frameworks)} framework(s)",
        frameworks=request.frameworks,
    )


@router.get("/status")
async def benchmark_status():
    """Check if a benchmark is running."""
    return {
        "running": _benchmark_status["running"],
        "has_results": _benchmark_status["last_result"] is not None,
    }


@router.get("/results")
async def benchmark_results():
    """Get the latest benchmark results."""
    if _benchmark_status["last_result"] is None:
        raise HTTPException(status_code=404, detail="No benchmark results available. Run a benchmark first.")
    return _benchmark_status["last_result"]
