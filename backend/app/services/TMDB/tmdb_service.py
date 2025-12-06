"""
TMDB API Service
"""
from typing import Optional, List, Dict, Any
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

    def fetch_movie(self, movie_id: int) -> Optional[Dict[str, Any]]:
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

    def fetch_popular_movies(
        self,
        max_pages: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Fetch popular movies

        Args:
            max_pages: Maximum number of pages to fetch

        Returns:
            List of cleaned movie data
        """

        logger.info(f"Fetching popular movies (max {max_pages} pages)")
        movies = []

        for page in range(1, max_pages + 1):
            logger.info(f"Fetching page {page}/{max_pages}")
            response = self.client.get_popular_movies(page=page)

            if not response or 'results' not in response:
                logger.warning(f"Failed to fetch page {page}")
                break

            for movie in response['results']:
                if self.validator.validate_movie(movie):
                    # Fetch full details for each movie
                    full_data = self.fetch_movie(movie['id'])
                    if full_data:
                        movies.append(full_data)

            # Check if we've reached the last page
            if page >= response.get('total_pages', 0):
                break

        logger.info(f"Fetched {len(movies)} popular movies")

        return movies

    def fetch_top_rated_movies(
        self,
        max_pages: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Fetch top rated movies

        Args:
            max_pages: Maximum number of pages to fetch

        Returns:
            List of cleaned movie data
        """

        logger.info(f"Fetching top rated movies (max {max_pages} pages)")
        movies = []

        for page in range(1, max_pages + 1):
            logger.info(f"Fetching page {page}/{max_pages}")
            response = self.client.get_top_rated_movies(page=page)

            if not response or 'results' not in response:
                logger.warning(f"Failed to fetch page {page}")
                break

            for movie in response['results']:
                if self.validator.validate_movie(movie):
                    full_data = self.fetch_movie(movie['id'])
                    if full_data:
                        movies.append(full_data)

            if page >= response.get('total_pages', 0):
                break

        logger.info(f"Fetched {len(movies)} top rated movies")
        return movies

    def fetch_movies_by_genre(
        self,
        genre_id: int,
        max_pages: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Fetch movies by genre

        Args:
            genre_id: TMDB genre ID
            max_pages: Maximum number of pages to fetch

        Returns:
            List of cleaned movie data
        """
        logger.info(f"Fetching movies for genre {genre_id} (max {max_pages} pages)")
        movies = []

        for page in range(1, max_pages + 1):
            response = self.client.discover_movies(
                page=page,
                with_genres=genre_id
            )

            if not response or 'results' not in response:
                break

            for movie in response['results']:
                if self.validator.validate_movie(movie):
                    full_data = self.fetch_movie(movie['id'])
                    if full_data:
                        movies.append(full_data)

            if page >= response.get('total_pages', 0):
                break

        logger.info(f"Fetched {len(movies)} movies for genre {genre_id}")
        
        return movies

    def get_all_genres(self) -> List[Dict[str, Any]]:
        """
        Get all available movie genres

        Returns:
            List of genres with id and name
        """

        logger.info("Fetching all genres")
        response = self.client.get_genres()

        if not response or 'genres' not in response:
            logger.warning("Failed to fetch genres")
            return []

        return response['genres']

    def close(self):
        """Close service and cleanup resources"""
        self.client.close()

    def __enter__(self):
        """Context manager entry"""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.close()
