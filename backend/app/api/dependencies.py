"""
Dependency injection for FastAPI endpoints.

Provides injectable dependencies for:
- Database sessions
- Service instances
- Authentication
- Rate limiting
"""

from collections.abc import Generator
from typing import Annotated

from fastapi import Depends, Header
from sqlalchemy.orm import Session

from app.api.exceptions import ValidationException
from app.core.database import SessionLocal
from app.services.constraint_validator import ConstraintValidator
from app.services.filter_engine import FilterEngine
from app.utils.logger import get_logger


logger = get_logger(__name__)


# =============================================================================
# Database Dependencies
# =============================================================================


def get_db() -> Generator[Session, None, None]:
    """
    Dependency for database session.

    Yields:
        Database session

    Example:
        >>> @app.get("/movies")
        >>> async def get_movies(db: Session = Depends(get_db)):
        >>>     return db.query(Movie).all()
    """
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
    """
    Dependency for filter engine service.

    Returns:
        FilterEngine instance

    Example:
        >>> @app.post("/filter")
        >>> async def filter_movies(
        >>>     engine: FilterEngine = Depends(get_filter_engine)
        >>> ):
        >>>     return engine.apply_filters(movies, constraints)
    """
    return FilterEngine()


def get_constraint_validator() -> ConstraintValidator:
    """
    Dependency for constraint validator service.

    Returns:
        ConstraintValidator instance

    Example:
        >>> @app.post("/validate")
        >>> async def validate(
        >>>     validator: ConstraintValidator = Depends(get_constraint_validator)
        >>> ):
        >>>     return validator.validate(constraints)
    """
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
    """
    Dependency for API key authentication (optional).

    Args:
        x_api_key: API key from request header

    Returns:
        Validated API key

    Raises:
        HTTPException: If API key is invalid

    Example:
        >>> @app.get("/protected")
        >>> async def protected_route(api_key: str = Depends(get_api_key)):
        >>>     return {"message": "Access granted"}
    """
    # For now, API key is optional
    # In production, implement proper validation
    if x_api_key is None:
        # Allow requests without API key for now
        return "anonymous"

    # Validate API key (implement your logic here)
    # For now, accept any key
    logger.info(f"API key provided: {x_api_key[:8]}...")
    return x_api_key


# Type alias for dependency injection
APIKey = Annotated[str, Depends(get_api_key)]


# =============================================================================
# Rate Limiting Dependencies
# =============================================================================


async def check_rate_limit(
    request_id: str | None = Header(None, alias="X-Request-ID"),
    client_ip: str | None = Header(None, alias="X-Forwarded-For"),
) -> None:
    """
    Dependency for rate limiting (placeholder).

    Args:
        request_id: Unique request ID
        client_ip: Client IP address

    Raises:
        HTTPException: If rate limit exceeded

    Example:
        >>> @app.get("/search", dependencies=[Depends(check_rate_limit)])
        >>> async def search():
        >>>     return {"results": []}
    """
    # Placeholder for rate limiting logic
    # In production, implement with Redis or similar
    # For now, just log the request
    if request_id:
        logger.debug(f"Request ID: {request_id}")
    if client_ip:
        logger.debug(f"Client IP: {client_ip}")

    # TODO: Implement actual rate limiting
    # Example:
    # - Check Redis for request count
    # - Increment counter
    # - If count > limit, raise HTTPException(status_code=429)


# =============================================================================
# Pagination Dependencies
# =============================================================================


def get_pagination_params(
    skip: int = 0,
    limit: int = 20,
) -> dict[str, int]:
    """
    Dependency for pagination parameters.

    Args:
        skip: Number of records to skip (offset)
        limit: Maximum number of records to return

    Returns:
        Dictionary with skip and limit values

    Raises:
        ValidationException: If pagination params are invalid

    Example:
        >>> @app.get("/movies")
        >>> async def get_movies(pagination: dict = Depends(get_pagination_params)):
        >>>     skip = pagination["skip"]
        >>>     limit = pagination["limit"]
        >>>     return db.query(Movie).offset(skip).limit(limit).all()
    """
    # Validate parameters
    if skip < 0:
        raise ValidationException("Skip must be >= 0", details={"skip": skip})

    if limit <= 0:
        raise ValidationException("Limit must be > 0", details={"limit": limit})

    if limit > 100:
        raise ValidationException("Limit must be <= 100", details={"limit": limit})

    return {"skip": skip, "limit": limit}


# Type alias for dependency injection
PaginationParams = Annotated[dict[str, int], Depends(get_pagination_params)]
