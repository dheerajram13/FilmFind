"""
TMDB API Client
"""
from typing import Any, Optional

from app.core.config import settings
from app.core.constants import (
    HTTP_TIMEOUT_DEFAULT,
    TMDB_BASE_URL,
    TMDB_DEFAULT_RATE_LIMIT,
    TMDB_RATE_WINDOW,
)
from app.utils import HTTPClient, RateLimiter


class TMDBAPIClient:
    """
    TMDB API HTTP client (SRP)
    """

    def __init__(
        self, api_key: str, base_url: str = TMDB_BASE_URL, timeout: int = HTTP_TIMEOUT_DEFAULT
    ):
        """
        Initialize TMDB API client

        Args:
            api_key: TMDB API key
            base_url: TMDB API base URL (default from constants)
            timeout: Request timeout in seconds (default from constants)
        """

        self.api_key = api_key
        rate_limit = getattr(settings, "TMDB_RATE_LIMIT", TMDB_DEFAULT_RATE_LIMIT)
        self.rate_limiter = RateLimiter(max_requests=rate_limit, time_window=TMDB_RATE_WINDOW)
        self.http_client = HTTPClient(base_url=base_url, timeout=timeout)

    def _make_request(
        self, endpoint: str, params: Optional[dict[str, Any]] = None
    ) -> Optional[dict[str, Any]]:
        """
        Make HTTP request to TMDB API

        Args:
            endpoint: API endpoint (e.g., '/movie/popular')
            params: Query parameters

        Returns:
            Response JSON or None if error
        """

        # Apply Rate limiting if needed
        self.rate_limiter.check_and_wait()

        # Add API key to params
        if params is None:
            params = {}
        params["api_key"] = self.api_key

        # Use HTTPClient's get_json method
        return self.http_client.get_json(endpoint, params=params)

    def get_movie(self, movie_id: int) -> Optional[dict[str, Any]]:
        """Get movie details by ID"""

        return self._make_request(
            f"/movie/{movie_id}", params={"append_to_response": "keywords,credits"}
        )

    def get_popular_movies(self, page: int = 1) -> Optional[dict[str, Any]]:
        """Get popular movies"""

        return self._make_request("/movie/popular", params={"page": page})

    def get_top_rated_movies(self, page: int = 1) -> Optional[dict[str, Any]]:
        """Get top rated movies"""

        return self._make_request("/movie/top_rated", params={"page": page})

    def get_now_playing_movies(self, page: int = 1) -> Optional[dict[str, Any]]:
        """Get now playing movies"""

        return self._make_request("/movie/now_playing", params={"page": page})

    def discover_movies(
        self, page: int = 1, sort_by: str = "popularity.desc", **kwargs
    ) -> Optional[dict[str, Any]]:
        """
        Discover movies with filters

        Args:
            page: Page number
            sort_by: Sort order
            **kwargs: Additional filter parameters (year, genre_id, etc.)
        """

        params = {"page": page, "sort_by": sort_by, **kwargs}

        return self._make_request("/discover/movie", params=params)

    def get_movie_keywords(self, movie_id: int) -> Optional[dict[str, Any]]:
        """Get keywords for a movie"""

        return self._make_request(f"/movie/{movie_id}/keywords")

    def get_movie_credits(self, movie_id: int) -> Optional[dict[str, Any]]:
        """Get credits (cast/crew) for a movie"""

        return self._make_request(f"/movie/{movie_id}/credits")

    def get_genres(self) -> Optional[dict[str, Any]]:
        """Get list of all movie genres"""

        return self._make_request("/genre/movie/list")

    def close(self):
        """Close HTTP client"""
        self.http_client.close()
