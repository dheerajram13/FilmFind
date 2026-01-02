"""
Redis cache manager.

Provides a clean interface for caching with automatic serialization,
TTL management, and error handling.
"""

import hashlib
import json
from typing import Any

from redis import Redis
from redis.exceptions import ConnectionError, RedisError

from app.core.cache_config import CacheKeyPrefix, CacheTTL
from app.core.config import settings
from app.utils.logger import get_logger


logger = get_logger(__name__)


class CacheManager:
    """
    Redis cache manager with automatic serialization and error handling.

    Follows Single Responsibility Principle:
    - Handles Redis connection
    - Manages cache operations (get, set, delete)
    - Provides key generation utilities
    - Tracks cache statistics
    """

    def __init__(self) -> None:
        """Initialize Redis connection."""
        self._redis: Redis | None = None
        self._enabled = settings.CACHE_ENABLED
        self._stats = {"hits": 0, "misses": 0, "errors": 0}

        if self._enabled:
            self._connect()

    def _connect(self) -> None:
        """Establish Redis connection."""
        try:
            self._redis = Redis(
                host=settings.REDIS_HOST,
                port=settings.REDIS_PORT,
                db=settings.REDIS_DB,
                password=settings.REDIS_PASSWORD if settings.REDIS_PASSWORD else None,
                decode_responses=False,  # We handle serialization ourselves
                socket_connect_timeout=5,
                socket_timeout=5,
            )
            # Test connection
            self._redis.ping()
            logger.info(f"Connected to Redis at {settings.REDIS_HOST}:{settings.REDIS_PORT}")
        except (ConnectionError, RedisError) as exc:
            logger.error(f"Failed to connect to Redis: {exc}")
            logger.warning("Cache disabled - running without Redis")
            self._enabled = False
            self._redis = None

    def get(self, key: str) -> Any | None:
        """
        Get value from cache.

        Args:
            key: Cache key

        Returns:
            Cached value or None if not found/error
        """
        if not self._enabled or not self._redis:
            return None

        try:
            value = self._redis.get(key)
            if value is None:
                self._stats["misses"] += 1
                return None

            self._stats["hits"] += 1
            # Deserialize JSON
            return json.loads(value)
        except (RedisError, json.JSONDecodeError) as exc:
            logger.error(f"Cache get error for key {key}: {exc}")
            self._stats["errors"] += 1
            return None

    def set(  # noqa: A003
        self, key: str, value: Any, ttl: int | CacheTTL | None = None
    ) -> bool:
        """
        Set value in cache with optional TTL.

        Args:
            key: Cache key
            value: Value to cache (must be JSON serializable)
            ttl: Time to live in seconds (None = no expiration)

        Returns:
            True if successful, False otherwise
        """
        if not self._enabled or not self._redis:
            return False

        try:
            # Serialize to JSON
            serialized = json.dumps(value)

            # Convert CacheTTL enum to int
            ttl_seconds = ttl.value if isinstance(ttl, CacheTTL) else ttl

            # Set with TTL
            if ttl_seconds and ttl_seconds > 0:
                self._redis.setex(key, ttl_seconds, serialized)
            else:
                self._redis.set(key, serialized)

            return True
        except (RedisError, TypeError, ValueError) as exc:
            logger.error(f"Cache set error for key {key}: {exc}")
            self._stats["errors"] += 1
            return False

    def delete(self, key: str) -> bool:
        """
        Delete key from cache.

        Args:
            key: Cache key to delete

        Returns:
            True if deleted, False otherwise
        """
        if not self._enabled or not self._redis:
            return False

        try:
            self._redis.delete(key)
            return True
        except RedisError as exc:
            logger.error(f"Cache delete error for key {key}: {exc}")
            self._stats["errors"] += 1
            return False

    def delete_pattern(self, pattern: str) -> int:
        """
        Delete all keys matching a pattern.

        Args:
            pattern: Key pattern (e.g., "search:*")

        Returns:
            Number of keys deleted
        """
        if not self._enabled or not self._redis:
            return 0

        try:
            keys = self._redis.keys(pattern)
            if keys:
                return self._redis.delete(*keys)
            return 0
        except RedisError as exc:
            logger.error(f"Cache delete pattern error for {pattern}: {exc}")
            self._stats["errors"] += 1
            return 0

    def exists(self, key: str) -> bool:
        """
        Check if key exists in cache.

        Args:
            key: Cache key

        Returns:
            True if exists, False otherwise
        """
        if not self._enabled or not self._redis:
            return False

        try:
            return bool(self._redis.exists(key))
        except RedisError as exc:
            logger.error(f"Cache exists error for key {key}: {exc}")
            self._stats["errors"] += 1
            return False

    def clear_all(self) -> bool:
        """
        Clear all keys from cache.

        WARNING: This clears the entire Redis database.

        Returns:
            True if successful, False otherwise
        """
        if not self._enabled or not self._redis:
            return False

        try:
            self._redis.flushdb()
            logger.warning("Cleared all cache keys")
            return True
        except RedisError as exc:
            logger.error(f"Cache clear error: {exc}")
            self._stats["errors"] += 1
            return False

    def get_stats(self) -> dict[str, int]:
        """
        Get cache statistics.

        Returns:
            Dictionary with hits, misses, errors counts
        """
        total = self._stats["hits"] + self._stats["misses"]
        hit_rate = self._stats["hits"] / total * 100 if total > 0 else 0

        return {
            "hits": self._stats["hits"],
            "misses": self._stats["misses"],
            "errors": self._stats["errors"],
            "hit_rate": round(hit_rate, 2),
        }

    def reset_stats(self) -> None:
        """Reset cache statistics."""
        self._stats = {"hits": 0, "misses": 0, "errors": 0}

    @staticmethod
    def generate_key(prefix: CacheKeyPrefix | str, *parts: Any) -> str:
        """
        Generate cache key from prefix and parts.

        Args:
            prefix: Key prefix (CacheKeyPrefix enum or string)
            *parts: Key parts to join

        Returns:
            Cache key string
        """
        prefix_str = prefix.value if isinstance(prefix, CacheKeyPrefix) else prefix
        parts_str = [str(p) for p in parts]
        return f"{prefix_str}:{':'.join(parts_str)}"

    @staticmethod
    def hash_value(value: Any) -> str:
        """
        Generate hash for cache key from any value.

        Args:
            value: Value to hash (must be JSON serializable)

        Returns:
            SHA256 hash string (first 16 characters)
        """
        try:
            # Convert to JSON for consistent hashing
            json_str = json.dumps(value, sort_keys=True)
            # Generate hash
            hash_obj = hashlib.sha256(json_str.encode())
            return hash_obj.hexdigest()[:16]
        except (TypeError, ValueError):
            # Fallback to string representation
            return hashlib.sha256(str(value).encode()).hexdigest()[:16]


# Global cache manager instance
_cache_manager: CacheManager | None = None


def get_cache_manager() -> CacheManager:
    """
    Get global cache manager instance (singleton pattern).

    Returns:
        CacheManager instance
    """
    global _cache_manager  # noqa: PLW0603
    if _cache_manager is None:
        _cache_manager = CacheManager()
    return _cache_manager
