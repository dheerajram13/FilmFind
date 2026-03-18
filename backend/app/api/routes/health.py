"""
Health check and system status endpoints.

Provides endpoints for monitoring application health and status.
"""

from datetime import UTC, datetime

from fastapi import APIRouter, Depends, status
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.api.dependencies import get_db, require_admin
from app.core.cache_manager import get_cache_manager
from app.core.config import settings
from app.core.scheduler import get_scheduler
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
            "message": "Database connection failed",
        }
        health_status["status"] = "unhealthy"

    # Check configuration — report generic warnings without leaking key names
    config_ok = bool(settings.DATABASE_URL)
    has_warnings = not (settings.TMDB_API_KEY and (settings.GEMINI_API_KEY or settings.GROQ_API_KEY))

    if not config_ok:
        health_status["checks"]["configuration"] = {
            "status": "unhealthy",
            "message": "Required configuration missing",
        }
        health_status["status"] = "unhealthy"
    elif has_warnings:
        health_status["checks"]["configuration"] = {
            "status": "warning",
            "message": "One or more optional API keys not configured",
        }
    else:
        health_status["checks"]["configuration"] = {
            "status": "healthy",
            "message": "Configuration valid",
        }

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


@router.get("/cache/stats", status_code=status.HTTP_200_OK, dependencies=[Depends(require_admin)])
async def get_cache_stats():
    """
    Get cache statistics (hits, misses, hit rate). Requires admin auth.

    Returns:
        Cache performance metrics
    """
    cache_manager = get_cache_manager()
    stats = cache_manager.get_stats()

    return {
        "cache_enabled": settings.CACHE_ENABLED,
        "stats": stats,
        "timestamp": datetime.now(UTC).isoformat(),
    }


@router.get("/jobs", status_code=status.HTTP_200_OK)
async def get_scheduled_jobs():
    """
    Get list of scheduled background jobs.

    Returns:
        List of jobs with their next run times
    """
    if not settings.ENABLE_BACKGROUND_JOBS:
        return {
            "enabled": False,
            "message": "Background jobs are disabled",
            "jobs": [],
        }

    scheduler = get_scheduler()
    jobs = scheduler.get_jobs()

    return {
        "enabled": True,
        "jobs": jobs,
        "timestamp": datetime.now(UTC).isoformat(),
    }


@router.post("/jobs/{job_id}/run", status_code=status.HTTP_200_OK, dependencies=[Depends(require_admin)])
async def trigger_job(job_id: str):
    """
    Manually trigger a background job to run immediately. Requires admin auth.

    Args:
        job_id: ID of the job to trigger

    Returns:
        Success message or error
    """
    if not settings.ENABLE_BACKGROUND_JOBS:
        return {
            "success": False,
            "message": "Background jobs are disabled",
        }

    scheduler = get_scheduler()
    success = scheduler.run_job_now(job_id)

    if success:
        return {
            "success": True,
            "message": f"Job '{job_id}' triggered successfully",
        }

    return {
        "success": False,
        "message": f"Job not found",
    }
