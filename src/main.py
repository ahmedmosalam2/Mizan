"""
Mizan — AI Agentic Framework Benchmark for MENA E-Commerce.

Entry point for the benchmark API.
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from adapters.driving.api.routes.benchmark import router as benchmark_router


app = FastAPI(
    title="Mizan Benchmark",
    description="Benchmark platform comparing 20 AI agentic frameworks on a real-world MENA e-commerce scenario.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(benchmark_router)


@app.get("/")
async def root():
    return {
        "app": "Mizan Benchmark",
        "description": "AI Agentic Framework Benchmark for MENA E-Commerce",
        "version": "1.0.0",
        "docs": "/docs",
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8001, reload=True)
