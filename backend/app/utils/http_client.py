"""
HTTP Client Utility
Reusable HTTP client with retry logic, logging, and error handling
"""
from typing import Any, Optional, Union

import httpx
from loguru import logger

from app.utils.retry import retry_with_backoff


class HTTPClient:
    """
    Generic HTTP client wrapper around httpx

    Provides:
    - Automatic retry with exponential backoff
    - Structured logging
    - Consistent error handling
    - Timeout management
    - Request/response logging

    Example:
        client = HTTPClient(base_url="", timeout=30)
        response = client.get("/users", params={"page": 1})
        data = client.get_json("/users/123")
    """

    def __init__(
        self,
        base_url: Optional[str] = None,
        timeout: int = 30,
        headers: Optional[dict[str, str]] = None,
        follow_redirects: bool = True,
        verify_ssl: bool = True,
    ):
        """
        Initialize HTTP client

        Args:
            base_url: Base URL for all requests (optional)
            timeout: Request timeout in seconds
            headers: Default headers for all requests
            follow_redirects: Whether to follow redirects
            verify_ssl: Whether to verify SSL certificates
        """

        self.base_url = base_url or ""
        self.timeout = timeout
        self.default_headers = headers or {}
        self.client = httpx.Client(
            timeout=timeout, follow_redirects=follow_redirects, verify=verify_ssl
        )

    def _build_url(self, endpoint: str) -> str:
        """
        Build full URL from base URL and endpoint

        Args:
            endpoint: API endpoint

        Returns:
            Full URL
        """

        if endpoint.startswith("http://") or endpoint.startswith("https://"):
            return endpoint

        base = self.base_url.rstrip("/")
        endpoint = endpoint.lstrip("/")

        return f"{base}/{endpoint}" if base else endpoint

    def _merge_headers(self, headers: Optional[dict[str, str]]) -> dict[str, str]:
        """
        Merge default headers with request-specific headers

        Args:
            headers: Request-specific headers

        Returns:
            Merged headers
        """

        merged = self.default_headers.copy()
        if headers:
            merged.update(headers)
        return merged

    @retry_with_backoff(
        max_retries=3, initial_delay=1.0, exceptions=(httpx.RequestError, httpx.TimeoutException)
    )
    def get(
        self,
        endpoint: str,
        params: Optional[dict[str, Any]] = None,
        headers: Optional[dict[str, str]] = None,
        **kwargs,
    ) -> httpx.Response:
        """
        Make GET request

        Args:
            endpoint: API endpoint
            params: Query parameters
            headers: Request headers
            **kwargs: Additional arguments for httpx

        Returns:
            HTTP response

        Raises:
            httpx.HTTPStatusError: For 4xx/5xx responses
            httpx.RequestError: For connection errors
        """

        url = self._build_url(endpoint)
        merged_headers = self._merge_headers(headers)

        logger.debug(f"GET {url} params={params}")

        try:
            response = self.client.get(url, params=params, headers=merged_headers, **kwargs)
            response.raise_for_status()
            logger.debug(f"GET {url} -> {response.status_code}")
            return response
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error {e.response.status_code} for GET {url}: {e}")
            raise
        except httpx.RequestError as e:
            logger.error(f"Request error for GET {url}: {e}")
            raise

    @retry_with_backoff(
        max_retries=3, initial_delay=1.0, exceptions=(httpx.RequestError, httpx.TimeoutException)
    )
    def post(
        self,
        endpoint: str,
        data: Optional[dict[str, Any]] = None,
        json: Optional[dict[str, Any]] = None,
        headers: Optional[dict[str, str]] = None,
        **kwargs,
    ) -> httpx.Response:
        """
        Make POST request

        Args:
            endpoint: API endpoint
            data: Form data
            json: JSON data
            headers: Request headers
            **kwargs: Additional arguments for httpx

        Returns:
            HTTP response

        Raises:
            httpx.HTTPStatusError: For 4xx/5xx responses
            httpx.RequestError: For connection errors
        """

        url = self._build_url(endpoint)
        merged_headers = self._merge_headers(headers)

        logger.debug(f"POST {url}")

        try:
            response = self.client.post(url, data=data, json=json, headers=merged_headers, **kwargs)
            response.raise_for_status()
            logger.debug(f"POST {url} -> {response.status_code}")
            return response
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error {e.response.status_code} for POST {url}: {e}")
            raise
        except httpx.RequestError as e:
            logger.error(f"Request error for POST {url}: {e}")
            raise

    @retry_with_backoff(
        max_retries=3, initial_delay=1.0, exceptions=(httpx.RequestError, httpx.TimeoutException)
    )
    def put(
        self,
        endpoint: str,
        data: Optional[dict[str, Any]] = None,
        json: Optional[dict[str, Any]] = None,
        headers: Optional[dict[str, str]] = None,
        **kwargs,
    ) -> httpx.Response:
        """
        Make PUT request

        Args:
            endpoint: API endpoint
            data: Form data
            json: JSON data
            headers: Request headers
            **kwargs: Additional arguments for httpx

        Returns:
            HTTP response
        """

        url = self._build_url(endpoint)
        merged_headers = self._merge_headers(headers)

        logger.debug(f"PUT {url}")

        try:
            response = self.client.put(url, data=data, json=json, headers=merged_headers, **kwargs)
            response.raise_for_status()
            logger.debug(f"PUT {url} -> {response.status_code}")
            return response
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error {e.response.status_code} for PUT {url}: {e}")
            raise
        except httpx.RequestError as e:
            logger.error(f"Request error for PUT {url}: {e}")
            raise

    @retry_with_backoff(
        max_retries=3, initial_delay=1.0, exceptions=(httpx.RequestError, httpx.TimeoutException)
    )
    def delete(
        self, endpoint: str, headers: Optional[dict[str, str]] = None, **kwargs
    ) -> httpx.Response:
        """
        Make DELETE request

        Args:
            endpoint: API endpoint
            headers: Request headers
            **kwargs: Additional arguments for httpx

        Returns:
            HTTP response
        """

        url = self._build_url(endpoint)
        merged_headers = self._merge_headers(headers)

        logger.debug(f"DELETE {url}")

        try:
            response = self.client.delete(url, headers=merged_headers, **kwargs)
            response.raise_for_status()
            logger.debug(f"DELETE {url} -> {response.status_code}")
            return response
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error {e.response.status_code} for DELETE {url}: {e}")
            raise
        except httpx.RequestError as e:
            logger.error(f"Request error for DELETE {url}: {e}")
            raise

    def get_json(
        self,
        endpoint: str,
        params: Optional[dict[str, Any]] = None,
        headers: Optional[dict[str, str]] = None,
        **kwargs,
    ) -> Optional[Union[dict[str, Any], list]]:
        """
        Make GET request and return JSON response

        Args:
            endpoint: API endpoint
            params: Query parameters
            headers: Request headers
            **kwargs: Additional arguments for httpx

        Returns:
            Parsed JSON response or None on error
        """

        try:
            response = self.get(endpoint, params=params, headers=headers, **kwargs)
            return response.json()
        except Exception as e:
            logger.error(f"Failed to get JSON from {endpoint}: {e}")
            return None

    def post_json(
        self,
        endpoint: str,
        json: Optional[dict[str, Any]] = None,
        headers: Optional[dict[str, str]] = None,
        **kwargs,
    ) -> Optional[Union[dict[str, Any], list]]:
        """
        Make POST request and return JSON response

        Args:
            endpoint: API endpoint
            json: JSON data
            headers: Request headers
            **kwargs: Additional arguments for httpx

        Returns:
            Parsed JSON response or None on error
        """

        try:
            response = self.post(endpoint, json=json, headers=headers, **kwargs)
            return response.json()
        except Exception as e:
            logger.error(f"Failed to post JSON to {endpoint}: {e}")
            return None

    def close(self):
        """Close the HTTP client"""
        self.client.close()

    def __enter__(self):
        """Context manager entry"""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.close()

    def __repr__(self) -> str:
        """String representation"""

        return f"HTTPClient(base_url='{self.base_url}', timeout={self.timeout}s)"
