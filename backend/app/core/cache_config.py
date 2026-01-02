"""
Cache configuration.

Defines TTL values and cache key patterns for different data types.
"""

from enum import Enum


class CacheTTL(int, Enum):
    """Cache TTL values in seconds."""

    # Search results cache (1 hour)
    SEARCH_RESULTS = 3600

    # Movie details cache (24 hours)
    MOVIE_DETAILS = 86400

    # Similar movies cache (12 hours)
    SIMILAR_MOVIES = 43200

    # Filter results cache (6 hours)
    FILTER_RESULTS = 21600

    # Trending movies cache (30 minutes - changes frequently)
    TRENDING = 1800

    # LLM re-ranking results cache (4 hours - expensive operation)
    RERANK_RESULTS = 14400

    # Embeddings cache (permanent - only invalidate on data update)
    EMBEDDINGS = -1  # -1 means no expiration

    # Query parsing cache (12 hours)
    QUERY_PARSING = 43200


class CacheKeyPrefix(str, Enum):
    """Cache key prefixes for different data types."""

    SEARCH = "search"
    MOVIE = "movie"
    SIMILAR = "similar"
    FILTER = "filter"
    TRENDING = "trending"
    RERANK = "rerank"
    EMBEDDING = "embedding"
    QUERY_PARSE = "query_parse"


# Cache key patterns
CACHE_KEY_PATTERNS = {
    "search": "{prefix}:{query_hash}:{filters_hash}:{limit}",
    "movie": "{prefix}:{movie_id}",
    "similar": "{prefix}:{movie_id}:{skip}:{limit}",
    "filter": "{prefix}:{filters_hash}:{skip}:{limit}",
    "trending": "{prefix}:{skip}:{limit}",
    "rerank": "{prefix}:{query_hash}:{candidates_hash}",
    "embedding": "{prefix}:{text_hash}",
    "query_parse": "{prefix}:{query_hash}",
}

# Maximum cache size per key (in bytes)
MAX_CACHE_SIZE = 1_000_000  # 1MB per key

# Cache statistics update interval (in seconds)
STATS_UPDATE_INTERVAL = 60  # Update stats every minute
