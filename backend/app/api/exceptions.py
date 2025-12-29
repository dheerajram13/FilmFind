"""
Custom exceptions for API error handling.

Provides domain-specific exceptions that map to HTTP status codes.
Follows SOLID principles with Single Responsibility for each exception type.
"""

from fastapi import status


class APIException(Exception):
    """
    Base exception for all API errors.

    Attributes:
        message: Human-readable error message
        status_code: HTTP status code
        error_type: Error type identifier
        details: Additional error details
    """

    def __init__(
        self,
        message: str,
        status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR,
        error_type: str = "api_error",
        details: dict | None = None,
    ):
        self.message = message
        self.status_code = status_code
        self.error_type = error_type
        self.details = details or {}
        super().__init__(self.message)


class ValidationException(APIException):
    """Raised when request validation fails."""

    def __init__(self, message: str, details: dict | None = None):
        super().__init__(
            message=message,
            status_code=status.HTTP_400_BAD_REQUEST,
            error_type="validation_error",
            details=details,
        )


class NotFoundException(APIException):
    """Raised when a requested resource is not found."""

    def __init__(self, message: str, resource_type: str | None = None):
        details = {"resource_type": resource_type} if resource_type else {}
        super().__init__(
            message=message,
            status_code=status.HTTP_404_NOT_FOUND,
            error_type="not_found",
            details=details,
        )


class UnauthorizedException(APIException):
    """Raised when authentication is required but not provided."""

    def __init__(self, message: str = "Authentication required"):
        super().__init__(
            message=message,
            status_code=status.HTTP_401_UNAUTHORIZED,
            error_type="unauthorized",
        )


class ForbiddenException(APIException):
    """Raised when access to a resource is forbidden."""

    def __init__(self, message: str = "Access forbidden"):
        super().__init__(
            message=message,
            status_code=status.HTTP_403_FORBIDDEN,
            error_type="forbidden",
        )


class ConflictException(APIException):
    """Raised when there is a conflict with existing data."""

    def __init__(self, message: str, details: dict | None = None):
        super().__init__(
            message=message,
            status_code=status.HTTP_409_CONFLICT,
            error_type="conflict",
            details=details,
        )


class RateLimitException(APIException):
    """Raised when rate limit is exceeded."""

    def __init__(self, message: str = "Rate limit exceeded", retry_after: int | None = None):
        details = {"retry_after": retry_after} if retry_after else {}
        super().__init__(
            message=message,
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            error_type="rate_limit",
            details=details,
        )


class ServiceUnavailableException(APIException):
    """Raised when a dependent service is unavailable."""

    def __init__(
        self, message: str = "Service temporarily unavailable", service: str | None = None
    ):
        details = {"service": service} if service else {}
        super().__init__(
            message=message,
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            error_type="service_unavailable",
            details=details,
        )


class InternalServerException(APIException):
    """Raised for unexpected internal errors."""

    def __init__(self, message: str = "An unexpected error occurred"):
        super().__init__(
            message=message,
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            error_type="internal_error",
        )
