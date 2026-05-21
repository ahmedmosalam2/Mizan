
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from db.database import init_db, close_db


from adapters.driving.api.routes.health import router as health_router
from adapters.driving.api.routes.campaigns import router as campaigns_router
from adapters.driving.api.routes.agents import router as agents_router
from adapters.driving.api.routes.benchmark import router as benchmark_router


# ── Lifecycle ──────────────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup / shutdown hooks."""
 
    print("[*] Mizan API starting up ...")
    await init_db()
    print("[+] Database tables created / verified")
    yield

    print("[*] Mizan API shutting down ...")
    await close_db()
app = FastAPI(
    title="Mizan",
    description=(
        "AI-Powered Campaign Management Platform for MENA E-Commerce.\n\n"
        "ميزان - منصة إدارة الحملات الإعلانية بالذكاء الاصطناعي"
    ),
    version="1.0.0",
    lifespan=lifespan,
)

# ── CORS ───────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # tighten in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Register routers ──────────────────────────────────────────────
app.include_router(health_router)
app.include_router(campaigns_router)
app.include_router(agents_router)
app.include_router(benchmark_router)


# ── Run directly ───────────────────────────────────────────────────
if __name__ == "__main__":
    import uvicorn
    from helper.config import Config

    uvicorn.run(
        "main:app",
        host=Config.API_HOST,
        port=Config.API_PORT,
        reload=Config.DEBUG,
    )
