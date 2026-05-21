"""
Async SQLAlchemy database engine and session management.

Uses asyncpg driver for PostgreSQL.
"""
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from helper.config import Config


# ── Base class for all ORM models ──────────────────────────────────
class Base(DeclarativeBase):
    pass


# ── Engine & session factory (created once at import time) ─────────
engine = create_async_engine(
    Config.DATABASE_URL,
    echo=Config.DEBUG,
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=True,
)

async_session_factory = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


# ── Helpers ────────────────────────────────────────────────────────
async def get_session() -> AsyncSession:
    """Yield an async session (for FastAPI Depends)."""
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


async def init_db():
    """Create all tables (dev/startup convenience)."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def close_db():
    """Dispose engine (shutdown)."""
    await engine.dispose()
