"""
Cache strategies for different endpoint types.

Provides specialized caching logic for search, movies, and other endpoints.
All strategies inherit from BaseCacheStrategy following DRY and SOLID principles.
"""

from typing import Any

from app.core.base_cache_strategy import BaseCacheStrategy
from app.core.cache_config import CacheKeyPrefix, CacheTTL
from app.core.cache_manager import CacheManager
from app.utils.logger import get_logger


logger = get_logger(__name__)


class SearchCacheStrategy(BaseCacheStrategy):
    """Cache strategy for search endpoints."""

    def __init__(self, cache_manager: CacheManager) -> None:
        """Initialize search cache strategy."""
        super().__init__(cache_manager, CacheKeyPrefix.SEARCH, CacheTTL.SEARCH_RESULTS)

    def get_key(self, query: str, filters: dict | None = None, limit: int = 10) -> str:
        """Generate cache key for search query."""
        query_hash = self.cache.hash_value(query)
        filters_hash = self.cache.hash_value(filters or {})
        return self.cache.generate_key(self.prefix, query_hash, filters_hash, limit)

    def get(self, query: str, filters: dict | None = None, limit: int = 10) -> Any | None:
        """Get cached search results."""
        return super().get(query=query, filters=filters, limit=limit)

    def set(  # noqa: A003
        self, query: str, results: Any, filters: dict | None = None, limit: int = 10
    ) -> bool:
        """Set search results in cache."""
        return super().set(results, query=query, filters=filters, limit=limit)


class MovieCacheStrategy(BaseCacheStrategy):
    """Cache strategy for movie details."""

    def __init__(self, cache_manager: CacheManager) -> None:
        """Initialize movie cache strategy."""
        super().__init__(cache_manager, CacheKeyPrefix.MOVIE, CacheTTL.MOVIE_DETAILS)

    def get_key(self, movie_id: int) -> str:
        """Generate cache key for movie ID."""
        return self.cache.generate_key(self.prefix, movie_id)

    def get(self, movie_id: int) -> Any | None:
        """Get cached movie details."""
        return super().get(movie_id=movie_id)

    def set(self, movie_id: int, movie_data: Any) -> bool:  # noqa: A003
        """Set movie details in cache."""
        return super().set(movie_data, movie_id=movie_id)

    def invalidate(self, movie_id: int) -> bool:
        """Invalidate specific movie cache."""
        key = self.get_key(movie_id)
        success = self.cache.delete(key)
        if success:
            logger.info(f"Invalidated cache for movie: {movie_id}")
        return success


class SimilarMoviesCacheStrategy(BaseCacheStrategy):
    """Cache strategy for similar movies endpoint."""

    def __init__(self, cache_manager: CacheManager) -> None:
        """Initialize similar movies cache strategy."""
        super().__init__(cache_manager, CacheKeyPrefix.SIMILAR, CacheTTL.SIMILAR_MOVIES)

    def get_key(self, movie_id: int, skip: int = 0, limit: int = 20) -> str:
        """Generate cache key for similar movies."""
        return self.cache.generate_key(self.prefix, movie_id, skip, limit)

    def get(self, movie_id: int, skip: int = 0, limit: int = 20) -> Any | None:
        """Get cached similar movies."""
        return super().get(movie_id=movie_id, skip=skip, limit=limit)

    def set(  # noqa: A003
        self, movie_id: int, results: Any, skip: int = 0, limit: int = 20
    ) -> bool:
        """Set similar movies in cache."""
        return super().set(results, movie_id=movie_id, skip=skip, limit=limit)

    def invalidate(self, movie_id: int) -> int:
        """Invalidate all similar movie caches for a movie."""
        pattern = f"{self.prefix.value}:{movie_id}:*"
        count = self.cache.delete_pattern(pattern)
        if count > 0:
            logger.info(f"Invalidated {count} similar movie cache entries for movie {movie_id}")
        return count


class TrendingCacheStrategy(BaseCacheStrategy):
    """Cache strategy for trending movies endpoint."""

    def __init__(self, cache_manager: CacheManager) -> None:
        """Initialize trending cache strategy."""
        super().__init__(cache_manager, CacheKeyPrefix.TRENDING, CacheTTL.TRENDING)

    def get_key(self, skip: int = 0, limit: int = 20) -> str:
        """Generate cache key for trending movies."""
        return self.cache.generate_key(self.prefix, skip, limit)

    def get(self, skip: int = 0, limit: int = 20) -> Any | None:
        """Get cached trending movies."""
        return super().get(skip=skip, limit=limit)

    def set(self, results: Any, skip: int = 0, limit: int = 20) -> bool:  # noqa: A003
        """Set trending movies in cache."""
        return super().set(results, skip=skip, limit=limit)


class FilterCacheStrategy(BaseCacheStrategy):
    """Cache strategy for filter endpoint."""

    def __init__(self, cache_manager: CacheManager) -> None:
        """Initialize filter cache strategy."""
        super().__init__(cache_manager, CacheKeyPrefix.FILTER, CacheTTL.FILTER_RESULTS)

    def get_key(self, filters: dict, skip: int = 0, limit: int = 20) -> str:
        """Generate cache key for filter query."""
        filters_hash = self.cache.hash_value(filters)
        return self.cache.generate_key(self.prefix, filters_hash, skip, limit)

    def get(self, filters: dict, skip: int = 0, limit: int = 20) -> Any | None:
        """Get cached filter results."""
        return super().get(filters=filters, skip=skip, limit=limit)

    def set(  # noqa: A003
        self, filters: dict, results: Any, skip: int = 0, limit: int = 20
    ) -> bool:
        """Set filter results in cache."""
        return super().set(results, filters=filters, skip=skip, limit=limit)


class CacheInvalidator:
    """
    Handles cache invalidation for data updates.

    Follows Single Responsibility Principle for cache invalidation logic.
    """

    def __init__(
        self,
        search_cache: SearchCacheStrategy,
        movie_cache: MovieCacheStrategy,
        similar_cache: SimilarMoviesCacheStrategy,
        trending_cache: TrendingCacheStrategy,
        filter_cache: FilterCacheStrategy,
    ) -> None:
        """Initialize cache invalidator."""
        self.search = search_cache
        self.movie = movie_cache
        self.similar = similar_cache
        self.trending = trending_cache
        self.filter = filter_cache

    def invalidate_movie_update(self, movie_id: int) -> None:
        """
        Invalidate caches when a movie is updated.

        Args:
            movie_id: ID of updated movie
        """
        logger.info(f"Invalidating caches for movie update: {movie_id}")
        self.movie.invalidate(movie_id)
        self.similar.invalidate(movie_id)
        # Also invalidate search and filter caches as results may change
        self.search.invalidate_all()
        self.filter.invalidate_all()

    def invalidate_new_movies(self) -> None:
        """Invalidate caches when new movies are added."""
        logger.info("Invalidating caches for new movies")
        self.search.invalidate_all()
        self.filter.invalidate_all()
        self.trending.invalidate_all()

    def invalidate_all(self) -> None:
        """Invalidate all caches (nuclear option)."""
        logger.warning("Invalidating ALL caches")
        self.search.invalidate_all()
        self.movie.invalidate_all()
        self.similar.invalidate_all()
        self.trending.invalidate_all()
        self.filter.invalidate_all()
