from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from sqlalchemy import text
from app.infrastructure.database import engine
from app.infrastructure.redis_client import redis_client
from app.api.worlds import router as worlds_router
from app.api.ws import router as ws_router
from app.core.telemetry import setup_telemetry, metrics
from app.core.config import settings

@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_telemetry()
    # Startup actions
    await redis_client.connect()
    yield
    # Shutdown actions
    await redis_client.close()
    await engine.dispose()

app = FastAPI(
    title="WORLDOS", 
    description="Autonomous persistent world simulation powered by agentic AI",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(worlds_router)
app.include_router(ws_router)

@app.get("/metrics")
async def get_metrics():
    return metrics.get_metrics()

@app.get("/health")
async def health_check():
    health_status = {
        "status": "ok",
        "service": "WORLDOS",
        "database": "unknown",
        "redis": "unknown"
    }

    # Check Database
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        health_status["database"] = "ok"
    except Exception as e:
        health_status["database"] = f"error: {str(e)}"
        health_status["status"] = "error"

    # Check Redis
    try:
        r = await redis_client.get_client()
        await r.ping()
        health_status["redis"] = "ok"
    except Exception as e:
        health_status["redis"] = f"error: {str(e)}"
        health_status["status"] = "error"

    if health_status["status"] == "error":
        raise HTTPException(status_code=503, detail=health_status)

    return health_status
