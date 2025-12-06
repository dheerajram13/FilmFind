"""
Rate Limiter Utility
Reusable rate limiting for any API or service
"""
import time
from typing import Optional
from loguru import logger


class RateLimiter:
    """
    Generic rate limiter using sliding window algorithm

    Can be used for any API that has rate limits.
    Thread-safe for single-threaded applications.

    Example:
        limiter = RateLimiter(max_requests=30, time_window=60)
        limiter.check_and_wait()  # Will wait if limit exceeded
    """

    def __init__(self, max_requests: int = 40, time_window: int = 10):
        """
        Initialize rate limiter

        Args:
            max_requests: Maximum requests allowed in time window
            time_window: Time window in seconds
        """

        self.max_requests = max_requests
        self.time_window = time_window
        self.requests = []

    def check_and_wait(self) -> None:
        """
        Wait if rate limit is exceeded

        Uses sliding window algorithm:
        - Removes old requests outside the time window
        - If at limit, waits until oldest request expires
        - Records new request timestamp
        """

        now = time.time()

        # Remove requests outside the time window
        self.requests = [
            req_time for req_time in self.requests
            if now - req_time < self.time_window
        ]

        # If at limit, wait
        if len(self.requests) >= self.max_requests:
            sleep_time = self.time_window - (now - self.requests[0])
            if sleep_time > 0:
                logger.debug(
                    f"Rate limit reached ({self.max_requests}/{self.time_window}s). "
                    f"Waiting {sleep_time:.2f} seconds..."
                )
                time.sleep(sleep_time)
                self.requests = []

        self.requests.append(time.time())

    def reset(self) -> None:
        """Clear all recorded requests"""

        self.requests = []

    def get_remaining(self) -> int:
        """
        Get number of remaining requests available

        Returns:
            Number of requests available before hitting limit
        """

        now = time.time()
        self.requests = [
            req_time for req_time in self.requests
            if now - req_time < self.time_window
        ]

        return max(0, self.max_requests - len(self.requests))

    def get_wait_time(self) -> float:
        """
        Get time to wait before next request is available

        Returns:
            Seconds to wait (0 if requests available)
        """
        
        now = time.time()
        self.requests = [
            req_time for req_time in self.requests
            if now - req_time < self.time_window
        ]

        if len(self.requests) < self.max_requests:
            return 0.0

        return self.time_window - (now - self.requests[0])

    def __repr__(self) -> str:
        """String representation"""

        return (
            f"RateLimiter(max_requests={self.max_requests}, "
            f"time_window={self.time_window}s, "
            f"remaining={self.get_remaining()})"
        )
