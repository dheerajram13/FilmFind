"""
Dependency injection for FastAPI endpoints.

Provides injectable dependencies for:
- Database sessions
- Service instances
- Authentication
- Rate limiting
"""

import asyncio
import time
from collections.abc import Generator
from typing import Annotated, Optional

from fastapi import Depends, Header, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.api.exceptions import ValidationException
from app.core.cache_manager import get_cache_manager
from app.core.config import settings
from app.core.database import SessionLocal
from app.services.constraint_validator import ConstraintValidator
from app.services.filter_engine import FilterEngine
from app.utils.logger import get_logger


logger = get_logger(__name__)

_bearer = HTTPBearer(auto_error=False)


# =============================================================================
# Database Dependencies
# =============================================================================


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# Type alias for dependency injection
DatabaseSession = Annotated[Session, Depends(get_db)]


# =============================================================================
# Service Dependencies
# =============================================================================


def get_filter_engine() -> FilterEngine:
    return FilterEngine()


def get_constraint_validator() -> ConstraintValidator:
    return ConstraintValidator()


# Type aliases for dependency injection
FilterEngineService = Annotated[FilterEngine, Depends(get_filter_engine)]
ConstraintValidatorService = Annotated[ConstraintValidator, Depends(get_constraint_validator)]


# =============================================================================
# Authentication Dependencies
# =============================================================================


def get_api_key(
    x_api_key: str | None = Header(None, description="API key for authentication")
) -> str:
    if x_api_key is None:
        return "anonymous"
    logger.debug(f"API key provided: {x_api_key[:8]}...")
    return x_api_key


# Type alias for dependency injection
APIKey = Annotated[str, Depends(get_api_key)]


def require_admin(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(_bearer),
) -> None:
    """Verify the Bearer token matches ADMIN_SECRET."""
    secret = settings.ADMIN_SECRET
    if not secret:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Admin endpoints are not enabled (ADMIN_SECRET not configured)",
        )
    if credentials is None or credentials.credentials != secret:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing admin token",
            headers={"WWW-Authenticate": "Bearer"},
        )


# =============================================================================
# Rate Limiting Dependencies
# =============================================================================


def make_rate_limit_dependency(limit: int):
    """
    Return a FastAPI dependency that enforces `limit` requests/minute per IP
    using a Redis sorted-set sliding window.

    Fails open when Redis is unavailable (logs warning, allows request).
    """

    async def _check(request: Request) -> None:
        cache = get_cache_manager()
        redis = cache._redis
        if redis is None:
            logger.warning("Rate limiter: Redis unavailable, skipping check")
            return

        # Prefer X-Forwarded-For (reverse proxy), fall back to direct client IP
        forwarded = request.headers.get("X-Forwarded-For") or ""
        ip = forwarded.split(",")[0].strip() or (
            request.client.host if request.client else "unknown"
        )
        key = f"rl:{request.url.path}:{ip}"
        now_ms = int(time.time() * 1000)
        window_ms = 60_000

        def _pipeline():
            pipe = redis.pipeline()
            pipe.zremrangebyscore(key, 0, now_ms - window_ms)
            pipe.zadd(key, {str(now_ms): now_ms})
            pipe.zcard(key)
            pipe.expire(key, 61)
            return pipe.execute()

        try:
            results = await asyncio.get_event_loop().run_in_executor(None, _pipeline)
        except Exception as exc:
            logger.warning(f"Rate limiter: Redis error ({exc}), skipping check")
            return

        count = results[2]  # zcard result
        if count > limit:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Rate limit exceeded. Max {limit} requests/minute.",
                headers={"Retry-After": "60"},
            )

    return _check


# =============================================================================
# Prompt Injection Guard
# =============================================================================


_INJECTION_PATTERNS = [
    "ignore previous",
    "ignore above",
    "disregard",
    "you are now",
    "act as",
    "jailbreak",
    "system prompt",
    "forget instructions",
    "ignore all",
]


def sanitise_query(query: str) -> str:
    """
    Guard against prompt injection attempts in user search queries.

    Raises HTTP 400 if any known injection pattern is detected.
    Returns the stripped query on success.
    """
    lower = query.lower()
    for pattern in _INJECTION_PATTERNS:
        if pattern in lower:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid query",
            )
    return query.strip()


# Keep the old no-op name as an alias so existing imports don't break
async def check_rate_limit(
    request_id: str | None = Header(None, alias="X-Request-ID"),
    client_ip: str | None = Header(None, alias="X-Forwarded-For"),
) -> None:
    if request_id:
        logger.debug(f"Request ID: {request_id}")
    if client_ip:
        logger.debug(f"Client IP: {client_ip}")


# =============================================================================
# Pagination Dependencies
# =============================================================================


def get_pagination_params(
    skip: int = 0,
    limit: int = 20,
) -> dict[str, int]:
    if skip < 0:
        raise ValidationException("Skip must be >= 0", details={"skip": skip})
    if limit <= 0:
        raise ValidationException("Limit must be > 0", details={"limit": limit})
    if limit > 100:
        raise ValidationException("Limit must be <= 100", details={"limit": limit})
    return {"skip": skip, "limit": limit}


# Type alias for dependency injection
PaginationParams = Annotated[dict[str, int], Depends(get_pagination_params)]
