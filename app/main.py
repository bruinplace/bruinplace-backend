from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.v1.router import api_router
from app.db.session import engine
from app.db.base import Base
from app.core.config import settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events."""
    # Startup
    print("Using environment:", settings.ENVIRONMENT)
    print("Using database:", settings.DATABASE_URL)
    # Auto-create tables in development for quick setup
    if settings.ENVIRONMENT == "development":
        Base.metadata.create_all(bind=engine)
    yield
    # Shutdown
    engine.dispose()


app = FastAPI(
    title="BruinPlace API",
    version="0.1.0",
    description="Housing platform API for UCLA students",
    lifespan=lifespan
)

# CORS for frontend (e.g. localhost:3000, localhost:5173)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:5173",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5173"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix="/api/v1")
