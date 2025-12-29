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
from app.api.routes import health
from app.core.config import settings
from app.utils.logger import get_logger


logger = get_logger(__name__)


# =============================================================================
# Lifespan Events
# =============================================================================


@asynccontextmanager
async def lifespan(app: FastAPI):  # noqa: ARG001
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

    # TODO: Initialize resources here
    # - Load ML models
    # - Connect to external services
    # - Warm up caches

    logger.info("Application startup complete")

    yield

    # Shutdown
    logger.info("Shutting down application...")

    # TODO: Cleanup resources here
    # - Close database connections
    # - Unload ML models
    # - Flush caches

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
    allow_methods=["*"],
    allow_headers=["*"],
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

# API routes (will be added in Module 3.2)
# from app.api.routes import search, movies, filters
# app.include_router(search.router, prefix=f"{settings.API_PREFIX}/search", tags=["search"])
# app.include_router(movies.router, prefix=f"{settings.API_PREFIX}/movies", tags=["movies"])
# app.include_router(filters.router, prefix=f"{settings.API_PREFIX}/filters", tags=["filters"])

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
