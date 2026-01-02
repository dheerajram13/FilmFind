"""
Base cache strategy class.

Provides common caching functionality following DRY and SOLID principles.
"""

from abc import ABC, abstractmethod
from typing import Any

from app.core.cache_config import CacheKeyPrefix, CacheTTL
from app.core.cache_manager import CacheManager
from app.utils.logger import get_logger


logger = get_logger(__name__)


class BaseCacheStrategy(ABC):
    """
    Abstract base class for cache strategies.

    Follows:
    - Single Responsibility: Handles caching logic for one type of data
    - Open/Closed: Open for extension (subclasses), closed for modification
    - DRY: Common get/set/invalidate logic in base class
    """

    def __init__(
        self,
        cache_manager: CacheManager,
        prefix: CacheKeyPrefix,
        ttl: CacheTTL,
    ) -> None:
        """
        Initialize base cache strategy.

        Args:
            cache_manager: Cache manager instance
            prefix: Cache key prefix
            ttl: Time to live for cached values
        """
        self.cache = cache_manager
        self.prefix = prefix
        self.ttl = ttl

    @abstractmethod
    def get_key(self, *args: Any, **kwargs: Any) -> str:
        """
        Generate cache key (must be implemented by subclasses).

        Args:
            *args: Positional arguments for key generation
            **kwargs: Keyword arguments for key generation

        Returns:
            Cache key string
        """

    def get(self, *args: Any, **kwargs: Any) -> Any | None:
        """
        Get value from cache.

        Args:
            *args: Arguments for key generation
            **kwargs: Keyword arguments for key generation

        Returns:
            Cached value or None if not found
        """
        key = self.get_key(*args, **kwargs)
        result = self.cache.get(key)

        # Log cache hit/miss
        self._log_cache_access(result is not None, key)

        return result

    def set(  # noqa: A003
        self,
        value: Any,
        *args: Any,
        **kwargs: Any,
    ) -> bool:
        """
        Set value in cache.

        Args:
            value: Value to cache
            *args: Arguments for key generation
            **kwargs: Keyword arguments for key generation

        Returns:
            True if successful, False otherwise
        """
        key = self.get_key(*args, **kwargs)
        return self.cache.set(key, value, self.ttl)

    def invalidate_all(self) -> int:
        """
        Invalidate all caches for this strategy.

        Returns:
            Number of keys deleted
        """
        pattern = f"{self.prefix.value}:*"
        count = self.cache.delete_pattern(pattern)
        if count > 0:
            logger.info(f"Invalidated {count} {self.prefix.value} cache entries")
        return count

    def _log_cache_access(self, is_hit: bool, key: str) -> None:
        """
        Log cache access (hit or miss).

        Args:
            is_hit: True if cache hit, False if miss
            key: Cache key
        """
        if is_hit:
            logger.debug(f"Cache HIT: {self.prefix.value} - {key}")
        else:
            logger.debug(f"Cache MISS: {self.prefix.value} - {key}")
