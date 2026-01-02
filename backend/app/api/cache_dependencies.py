"""
Cache dependencies for FastAPI endpoints.

Provides dependency injection for cache strategies.
"""

from app.core.cache_manager import get_cache_manager
from app.core.cache_strategies import (
    CacheInvalidator,
    FilterCacheStrategy,
    MovieCacheStrategy,
    SearchCacheStrategy,
    SimilarMoviesCacheStrategy,
    TrendingCacheStrategy,
)


def get_search_cache() -> SearchCacheStrategy:
    """Dependency for search cache strategy."""
    return SearchCacheStrategy(get_cache_manager())


def get_movie_cache() -> MovieCacheStrategy:
    """Dependency for movie cache strategy."""
    return MovieCacheStrategy(get_cache_manager())


def get_similar_cache() -> SimilarMoviesCacheStrategy:
    """Dependency for similar movies cache strategy."""
    return SimilarMoviesCacheStrategy(get_cache_manager())


def get_trending_cache() -> TrendingCacheStrategy:
    """Dependency for trending cache strategy."""
    return TrendingCacheStrategy(get_cache_manager())


def get_filter_cache() -> FilterCacheStrategy:
    """Dependency for filter cache strategy."""
    return FilterCacheStrategy(get_cache_manager())


def get_cache_invalidator() -> CacheInvalidator:
    """Dependency for cache invalidator."""
    search = get_search_cache()
    movie = get_movie_cache()
    similar = get_similar_cache()
    trending = get_trending_cache()
    filter_cache = get_filter_cache()

    return CacheInvalidator(search, movie, similar, trending, filter_cache)
