from contextlib import asynccontextmanager
from fastapi import FastAPI
from app.api.v1.router import api_router
from app.db.session import engine
from app.core.config import settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events."""
    # Startup
    print("Using environment:", settings.ENVIRONMENT)
    print("Using database:", settings.DATABASE_URL)
    yield
    # Shutdown
    engine.dispose()


app = FastAPI(
    title="BruinPlace API",
    version="0.1.0",
    description="Housing platform API for UCLA students",
    lifespan=lifespan
)

app.include_router(api_router, prefix="/api/v1")
