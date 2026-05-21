"""
Health check route.
"""
from datetime import datetime

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from adapters.driving.api.dependencies import get_db
from adapters.driving.api.schemas import HealthResponse

router = APIRouter(tags=["System"])


@router.get("/health", response_model=HealthResponse)
async def health_check(session: AsyncSession = Depends(get_db)):
    """Check API and database health."""
    db_status = "connected"
    try:
        await session.execute(text("SELECT 1"))
    except Exception:
        db_status = "disconnected"

    return HealthResponse(
        status="healthy",
        version="1.0.0",
        database=db_status,
        timestamp=datetime.now(),
    )


@router.get("/")
async def root():
    """API root - basic info."""
    return {
        "app": "Mizan",
        "description": "AI-Powered Campaign Management Platform for MENA E-Commerce",
        "version": "1.0.0",
        "docs": "/docs",
    }
