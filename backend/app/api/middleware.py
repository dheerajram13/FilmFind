"""
API middleware for request/response processing.

Provides middleware for:
- Request logging
- Error handling
- Request timing
- Custom headers

Design Patterns:
- Single Responsibility: Each middleware has one job
- Open/Closed: Easy to add new middleware without modifying existing ones
"""

from collections.abc import Callable
import time

from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from app.api.exceptions import APIException
from app.utils.logger import get_logger


logger = get_logger(__name__)


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """
    Middleware for logging all incoming requests and responses.

    Logs:
    - Request method, path, client IP
    - Response status code
    - Request duration
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request and log details."""
        # Start timing
        start_time = time.time()

        # Get client info
        client_host = request.client.host if request.client else "unknown"

        # Log incoming request
        logger.info(f"Request: {request.method} {request.url.path} " f"from {client_host}")

        # Process request
        try:
            response = await call_next(request)
        except Exception as exc:
            # Log error and re-raise
            logger.error(f"Request failed: {exc}", exc_info=True)
            raise

        # Calculate duration
        duration = time.time() - start_time

        # Log response
        logger.info(
            f"Response: {request.method} {request.url.path} "
            f"status={response.status_code} duration={duration:.3f}s"
        )

        # Add custom headers
        response.headers["X-Process-Time"] = str(duration)

        return response


class ErrorHandlingMiddleware(BaseHTTPMiddleware):
    """
    Middleware for centralized error handling.

    Catches custom APIExceptions and converts them to appropriate JSON responses.
    Follows DRY by using a single method for all error responses.
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request with error handling."""
        try:
            return await call_next(request)
        except APIException as exc:
            # Handle our custom API exceptions
            logger.warning(f"{exc.error_type}: {exc.message}", extra={"details": exc.details})
            return self._create_error_response(exc)
        except ValueError as exc:
            # Validation errors from Pydantic or other libraries
            logger.warning(f"Validation error: {exc}")
            api_exc = APIException(
                message=str(exc),
                status_code=400,
                error_type="validation_error",
            )
            return self._create_error_response(api_exc)
        except Exception as exc:
            # Catch-all for unexpected errors
            logger.error(f"Unhandled error: {exc}", exc_info=True)
            api_exc = APIException(
                message="An unexpected error occurred",
                status_code=500,
                error_type="internal_error",
            )
            return self._create_error_response(api_exc)

    @staticmethod
    def _create_error_response(exc: APIException) -> JSONResponse:
        """
        Create standardized JSON error response.

        Args:
            exc: APIException instance

        Returns:
            JSONResponse with error details
        """
        content = {
            "error": exc.message,
            "type": exc.error_type,
        }

        # Add details if present
        if exc.details:
            content["details"] = exc.details

        return JSONResponse(
            status_code=exc.status_code,
            content=content,
        )


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    Middleware for adding security headers to responses.

    Adds headers for:
    - XSS protection
    - Content type options
    - Frame options
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Add security headers to response."""
        response = await call_next(request)

        # Security headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"

        return response
