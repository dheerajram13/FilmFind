"""
Sixty-mode cache management: key format and cache refresh.
"""
from __future__ import annotations

from sqlalchemy.orm import Session

from app.core.cache_manager import get_cache_manager
from app.core.scoring import VALID_CONTEXTS, VALID_CRAVINGS, VALID_MOODS
from app.services.sixty_scorer import score_films_sql
from app.utils.logger import get_logger

logger = get_logger(__name__)

_SIXTY_CACHE_TTL = 86400  # 24 hours


def sixty_cache_key(mood: str, context: str, craving: str) -> str:
    """Single source of truth for the sixty-mode Redis cache key format."""
    return f"sixty:{mood}:{context}:{craving}"


class SixtyRefreshService:
    """Busts and rebuilds Redis cache for all mood×context×craving combinations."""

    def refresh(self, db: Session) -> dict:
        """
        Delete all sixty:* keys and rebuild from scored DB results.

        Returns a summary dict.
        """
        cache = get_cache_manager()

        deleted = cache.delete_pattern("sixty:*")
        logger.info(f"sixty/refresh: deleted {deleted} existing cache keys")

        cached = skipped = errors = 0

        for mood in VALID_MOODS:
            for context in VALID_CONTEXTS:
                for craving in VALID_CRAVINGS:
                    try:
                        scored = score_films_sql(db, mood, context, craving)
                        if scored:
                            key = sixty_cache_key(mood, context, craving)
                            payload = [{"id": f.id, "score": s} for f, s in scored]
                            cache.set(key, payload, ttl=_SIXTY_CACHE_TTL)
                            cached += 1
                        else:
                            skipped += 1
                    except Exception as exc:
                        logger.error(f"sixty/refresh error {mood}/{context}/{craving}: {exc}")
                        errors += 1

        logger.info(f"sixty/refresh complete: cached={cached} skipped={skipped} errors={errors}")
        return {
            "status": "ok",
            "deleted_old_keys": deleted,
            "combinations_cached": cached,
            "combinations_skipped_no_films": skipped,
            "errors": errors,
            "total_combinations": len(VALID_MOODS) * len(VALID_CONTEXTS) * len(VALID_CRAVINGS),
        }
