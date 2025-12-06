"""
TMDB API Service
"""
from collections.abc import Callable
from typing import Any, Optional

from loguru import logger

from app.core.config import settings
from app.services.TMDB.tmdb_client import TMDBAPIClient
from app.services.TMDB.tmdb_validator import TMDBDataValidator


class TMDBService:
    """
    High-level TMDB service
    Facade pattern: Provides simple interface to complex subsystem
    """

    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize TMDB service

        Args:
            api_key: TMDB API key (defaults to settings)
        """

        self.api_key = api_key or settings.TMDB_API_KEY
        if not self.api_key:
            raise ValueError("TMDB API key is required")

        self.client = TMDBAPIClient(self.api_key)
        self.validator = TMDBDataValidator()

    def fetch_movie(self, movie_id: int) -> Optional[dict[str, Any]]:
        """
        Fetch and validate a single movie

        Args:
            movie_id: TMDB movie ID

        Returns:
            Cleaned movie data or None
        """

        logger.info(f"Fetching movie {movie_id}")

        raw_data = self.client.get_movie(movie_id)
        if not raw_data:
            logger.warning(f"Failed to fetch movie {movie_id}")
            return None

        if not self.validator.validate_movie(raw_data):
            logger.warning(f"Invalid movie data for {movie_id}")
            return None

        return self.validator.clean_movie_data(raw_data)

    def _fetch_paginated_movies(
        self,
        fetch_func: Callable[[int], Optional[dict[str, Any]]],
        max_pages: int,
        log_prefix: str,
        fetch_full_details: bool = True,
    ) -> list[dict[str, Any]]:
        """
        Fetch movies with pagination

        Args:
            fetch_func: Function to fetch a page of movies (takes page number)
            max_pages: Maximum number of pages to fetch
            log_prefix: Description for logging (e.g., "popular movies")
            fetch_full_details: If True, fetches full details for each movie (slower, more complete)
                               If False, uses basic data from list endpoint (faster, less data)

        Returns:
            List of cleaned movie data

        Note:
            Setting fetch_full_details=True causes N+1 API calls:
            - 1 call per page (e.g., 10 pages = 10 calls)
            - 1 call per movie for details (e.g., 200 movies = 200 calls)
            - Total: ~210 API calls for 10 pages
            With 40 req/10s rate limit, this takes ~50 seconds minimum.

            For initial data ingestion, consider fetch_full_details=False
            and fetch details in a separate batch process.
        """
        logger.info(
            f"Fetching {log_prefix} (max {max_pages} pages, full_details={fetch_full_details})"
        )
        movies = []

        for page in range(1, max_pages + 1):
            logger.info(f"Fetching page {page}/{max_pages}")
            response = fetch_func(page)

            if not response or "results" not in response:
                logger.warning(f"Failed to fetch page {page}")
                break

            for movie in response["results"]:
                if self.validator.validate_movie(movie):
                    if fetch_full_details:
                        # Fetch complete movie details (includes cast, keywords, etc.)
                        full_data = self.fetch_movie(movie["id"])
                        if full_data:
                            movies.append(full_data)
                    else:
                        # Use basic data from list endpoint (faster, no extra API calls)
                        cleaned_data = self.validator.clean_movie_data(movie)
                        movies.append(cleaned_data)

            if page >= response.get("total_pages", 0):
                break

        logger.info(f"Fetched {len(movies)} {log_prefix}")
        return movies

    def fetch_popular_movies(
        self,
        max_pages: int = 10,
        fetch_full_details: bool = True,
    ) -> list[dict[str, Any]]:
        """
        Fetch popular movies

        Args:
            max_pages: Maximum number of pages to fetch
            fetch_full_details: If True, fetches complete details (cast, keywords, etc.)
                               If False, uses basic data from list (faster, fewer API calls)

        Returns:
            List of cleaned movie data
        """
        return self._fetch_paginated_movies(
            fetch_func=self.client.get_popular_movies,
            max_pages=max_pages,
            log_prefix="popular movies",
            fetch_full_details=fetch_full_details,
        )

    def fetch_top_rated_movies(
        self,
        max_pages: int = 10,
        fetch_full_details: bool = True,
    ) -> list[dict[str, Any]]:
        """
        Fetch top rated movies

        Args:
            max_pages: Maximum number of pages to fetch
            fetch_full_details: If True, fetches complete details (cast, keywords, etc.)
                               If False, uses basic data from list (faster, fewer API calls)

        Returns:
            List of cleaned movie data
        """
        return self._fetch_paginated_movies(
            fetch_func=self.client.get_top_rated_movies,
            max_pages=max_pages,
            log_prefix="top rated movies",
            fetch_full_details=fetch_full_details,
        )

    def fetch_movies_by_genre(
        self,
        genre_id: int,
        max_pages: int = 5,
        fetch_full_details: bool = True,
    ) -> list[dict[str, Any]]:
        """
        Fetch movies by genre

        Args:
            genre_id: TMDB genre ID
            max_pages: Maximum number of pages to fetch
            fetch_full_details: If True, fetches complete details (cast, keywords, etc.)
                               If False, uses basic data from list (faster, fewer API calls)

        Returns:
            List of cleaned movie data
        """

        # Create a closure that captures the genre_id
        def fetch_genre_page(page: int) -> Optional[dict[str, Any]]:
            return self.client.discover_movies(page=page, with_genres=genre_id)

        return self._fetch_paginated_movies(
            fetch_func=fetch_genre_page,
            max_pages=max_pages,
            log_prefix=f"movies for genre {genre_id}",
            fetch_full_details=fetch_full_details,
        )

    def fetch_movie_details_batch(
        self,
        movie_ids: list[int],
        delay_between_batches: float = 0.25,
    ) -> list[dict[str, Any]]:
        """
        Fetch full details for a batch of movies with rate limiting

        This is useful for a two-phase approach:
        1. Fetch basic movie lists with fetch_full_details=False (fast)
        2. Fetch complete details separately with this method (controlled rate)

        Args:
            movie_ids: List of TMDB movie IDs to fetch
            delay_between_batches: Seconds to wait between requests (default 0.25s = 4 req/s)

        Returns:
            List of cleaned movie data with full details

        Example:
            >>> # Phase 1: Fast fetch of basic data
            >>> movies = service.fetch_popular_movies(max_pages=10, fetch_full_details=False)
            >>> movie_ids = [m['tmdb_id'] for m in movies]
            >>>
            >>> # Phase 2: Batch fetch details with controlled rate
            >>> detailed_movies = service.fetch_movie_details_batch(movie_ids)
        """
        import time

        logger.info(
            f"Fetching details for {len(movie_ids)} movies (delay={delay_between_batches}s)"
        )
        detailed_movies = []

        for i, movie_id in enumerate(movie_ids, 1):
            if i % 10 == 0:
                logger.info(f"Fetching details: {i}/{len(movie_ids)}")

            movie_data = self.fetch_movie(movie_id)
            if movie_data:
                detailed_movies.append(movie_data)

            # Rate limiting: sleep between requests
            if i < len(movie_ids):  # Don't sleep after last request
                time.sleep(delay_between_batches)

        logger.info(f"Fetched details for {len(detailed_movies)}/{len(movie_ids)} movies")
        return detailed_movies

    def get_all_genres(self) -> list[dict[str, Any]]:
        """
        Get all available movie genres

        Returns:
            List of genres with id and name
        """

        logger.info("Fetching all genres")
        response = self.client.get_genres()

        if not response or "genres" not in response:
            logger.warning("Failed to fetch genres")
            return []

        return response["genres"]

    def close(self):
        """Close service and cleanup resources"""
        self.client.close()

    def __enter__(self):
        """Context manager entry"""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.close()
