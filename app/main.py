from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.v1.router import api_router
from app.db.session import engine
from app.db.base import DeclarativeBase
from app.core.config import settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events."""
    # Startup
    # Auto-create tables in development for quick setup
    if settings.ENVIRONMENT == "development":
        DeclarativeBase.metadata.create_all(bind=engine)
    yield
    # Shutdown
    engine.dispose()


app = FastAPI(
    title="BruinPlace API",
    version="0.1.0",
    description="Housing platform API for UCLA students",
    lifespan=lifespan,
)

# CORS origins come from settings; defaults differ for development vs production.
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_allow_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix="/api/v1")
