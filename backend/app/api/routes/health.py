"""
Health check and system status endpoints.

Provides endpoints for monitoring application health and status.
"""

from datetime import UTC, datetime

from fastapi import APIRouter, Depends, status
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.api.dependencies import get_db
from app.core.config import settings
from app.utils.logger import get_logger


logger = get_logger(__name__)

router = APIRouter(tags=["health"])


@router.get("/health", status_code=status.HTTP_200_OK)
async def health_check():
    """
    Basic health check endpoint.

    Returns:
        Simple health status
    """
    return {
        "status": "healthy",
        "timestamp": datetime.now(UTC).isoformat(),
        "service": settings.APP_NAME,
        "version": settings.APP_VERSION,
    }


@router.get("/health/detailed", status_code=status.HTTP_200_OK)
async def detailed_health_check(db: Session = Depends(get_db)):
    """
    Detailed health check with dependency status.

    Checks:
    - Database connectivity
    - Application status
    - Configuration status

    Returns:
        Detailed health information
    """
    health_status = {
        "status": "healthy",
        "timestamp": datetime.now(UTC).isoformat(),
        "service": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "checks": {},
    }

    # Check database
    try:
        # Execute simple query
        db.execute(text("SELECT 1"))
        db.commit()
        health_status["checks"]["database"] = {
            "status": "healthy",
            "message": "Database connection successful",
        }
    except Exception as exc:
        logger.error(f"Database health check failed: {exc}")
        health_status["checks"]["database"] = {
            "status": "unhealthy",
            "message": f"Database error: {exc!s}",
        }
        health_status["status"] = "unhealthy"

    # Check configuration
    config_status = "healthy"
    config_issues = []

    if not settings.DATABASE_URL:
        config_issues.append("DATABASE_URL not configured")
        config_status = "unhealthy"

    if not settings.TMDB_API_KEY:
        config_issues.append("TMDB_API_KEY not configured")

    if not settings.GROQ_API_KEY and settings.LLM_PROVIDER == "groq":
        config_issues.append("GROQ_API_KEY not configured")

    health_status["checks"]["configuration"] = {
        "status": config_status,
        "message": "Configuration valid" if not config_issues else ", ".join(config_issues),
    }

    if config_status == "unhealthy":
        health_status["status"] = "unhealthy"

    # Overall health assessment
    if health_status["status"] == "unhealthy":
        return health_status  # FastAPI will still return 200, but with unhealthy status

    return health_status


@router.get("/", status_code=status.HTTP_200_OK)
async def root():
    """
    Root endpoint with API information.

    Returns:
        API welcome message and basic info
    """
    return {
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "status": "running",
        "description": "AI-Powered Semantic Movie Discovery Engine",
        "docs": f"{settings.API_PREFIX}/docs",
        "health": "/health",
    }


@router.get("/ping", status_code=status.HTTP_200_OK)
async def ping():
    """
    Simple ping endpoint for uptime monitoring.

    Returns:
        Pong message with timestamp
    """
    return {
        "message": "pong",
        "timestamp": datetime.now(UTC).isoformat(),
    }
