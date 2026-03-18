"""
FastAPI main application entry point.

Initializes the FilmFind API with all middleware, routes, and configurations.
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware

from app.api.middleware import (
    ErrorHandlingMiddleware,
    RequestLoggingMiddleware,
    SecurityHeadersMiddleware,
)
from app.api.routes import admin, health, search, sixty
from app.core.config import settings
from app.core.scheduler import start_scheduler, stop_scheduler
from app.utils.logger import get_logger


logger = get_logger(__name__)


# =============================================================================
# Lifespan Events
# =============================================================================


@asynccontextmanager
async def lifespan(app: FastAPI):  # noqa: ARG001, ANN201
    """
    Lifespan context manager for startup and shutdown events.

    Handles:
    - Application startup (initialize resources)
    - Application shutdown (cleanup resources)
    """
    # Startup
    logger.info(f"Starting {settings.APP_NAME} v{settings.APP_VERSION}")
    logger.info(f"Environment: {'Development' if settings.DEBUG else 'Production'}")
    logger.info(f"API Prefix: {settings.API_PREFIX}")
    logger.info(f"Docs URL: {settings.API_PREFIX}/docs")

    # pgvector is used for vector search — no pre-loading needed (index lives in Postgres)
    logger.info("Vector search: pgvector (HNSW cosine index in Postgres)")

    # Warn loudly if SECRET_KEY is the insecure default
    _INSECURE_KEY = "your-secret-key-change-in-production"
    if settings.SECRET_KEY == _INSECURE_KEY:
        logger.critical("SECRET_KEY is the insecure default — set a strong key in .env before production use")

    # Start background job scheduler
    start_scheduler()

    logger.info("Application startup complete")

    yield

    # Shutdown
    logger.info("Shutting down application...")

    # Stop background job scheduler
    stop_scheduler()

    logger.info("Application shutdown complete")


# =============================================================================
# FastAPI Application
# =============================================================================


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="AI-Powered Semantic Movie Discovery Engine",
    docs_url=f"{settings.API_PREFIX}/docs",
    redoc_url=f"{settings.API_PREFIX}/redoc",
    openapi_url=f"{settings.API_PREFIX}/openapi.json",
    lifespan=lifespan,
    # Additional metadata
    contact={
        "name": "FilmFind Team",
        "url": "https://github.com/filmfind/filmfind",
    },
    license_info={
        "name": "MIT License",
        "url": "https://opensource.org/licenses/MIT",
    },
)

# =============================================================================
# Middleware Setup
# =============================================================================

# CORS middleware (should be first)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization", "X-Request-ID", "X-API-Key"],
)

# GZip compression middleware
app.add_middleware(GZipMiddleware, minimum_size=1000)

# Security headers middleware
app.add_middleware(SecurityHeadersMiddleware)

# Error handling middleware
app.add_middleware(ErrorHandlingMiddleware)

# Request logging middleware (should be last for accurate timing)
app.add_middleware(RequestLoggingMiddleware)

# =============================================================================
# Router Registration
# =============================================================================

# Health check routes (no prefix)
app.include_router(health.router)

# Search and recommendation routes
app.include_router(search.router)

# 60-Second Mode routes
app.include_router(sixty.router, prefix="/api")

# Admin routes
app.include_router(admin.router, prefix="/api")

# =============================================================================
# Application Entry Point
# =============================================================================

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
        log_level=settings.LOG_LEVEL.lower(),
    )
