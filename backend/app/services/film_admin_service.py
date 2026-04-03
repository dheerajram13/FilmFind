"""
Services for admin film operations: enrichment, embedding regeneration,
and sixty-mode cache refresh.

Extracted from admin route handlers to keep routes thin (SRP).
"""
from __future__ import annotations

import json
from typing import Optional

from sqlalchemy.orm import Session

from app.core.cache_manager import get_cache_manager
from app.core.scoring import VALID_CONTEXTS, VALID_CRAVINGS, VALID_MOODS
from app.models.media import Media
from app.services.embedding_service import EmbeddingService
from app.services.llm_client import LLMClient
from app.services.sixty_scorer import score_films_sql
from app.utils.logger import get_logger

logger = get_logger(__name__)

_ENRICH_SYSTEM = (
    "You are a film analysis expert. Respond ONLY with valid JSON:\n"
    '{"narrative_dna":"...","themes":[...],"tone_tags":[...],'
    '"darkness_score":0,"complexity_score":0,"energy_score":0}'
)


def _clamp(value: object, lo: int, hi: int) -> Optional[int]:
    if value is None:
        return None
    try:
        return max(lo, min(hi, int(value)))  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return None


class FilmEnrichmentService:
    """Runs Stage 2 LLM enrichment on a single Media record."""

    def __init__(self, llm_client: Optional[LLMClient] = None) -> None:
        self._llm = llm_client or LLMClient()

    def enrich(self, db: Session, film: Media) -> dict:
        """
        Run LLM enrichment and persist results.

        Returns a dict with the updated field values.
        Raises ValueError if the LLM returns unparseable JSON.
        """
        genre_names = ", ".join(g.name for g in (film.genres or []))
        overview = film.overview or "No overview available."

        prompt = (
            f'Title: "{film.title}"\n'
            f"Genres: {genre_names or 'unknown'}\n"
            f"Overview: {overview[:500]}\n\n"
            "Analyse this film and return the JSON enrichment data."
        )

        raw = self._llm.generate_completion(
            prompt=prompt,
            system_prompt=_ENRICH_SYSTEM,
            temperature=0.3,
            max_tokens=512,
            response_format={"type": "json_object"},
        )

        try:
            data = json.loads(raw)
        except Exception as exc:
            raise ValueError(f"LLM returned invalid JSON: {exc}") from exc

        film.narrative_dna = data.get("narrative_dna")
        film.themes = data.get("themes") or []
        film.tone_tags = data.get("tone_tags") or []
        film.darkness_score = _clamp(data.get("darkness_score"), 0, 10)
        film.complexity_score = _clamp(data.get("complexity_score"), 0, 10)
        film.energy_score = _clamp(data.get("energy_score"), 0, 10)
        db.commit()

        logger.info(f"Enriched film {film.id}: {film.title!r}")
        return {
            "narrative_dna": film.narrative_dna,
            "themes": film.themes,
            "tone_tags": film.tone_tags,
            "darkness_score": film.darkness_score,
            "complexity_score": film.complexity_score,
            "energy_score": film.energy_score,
        }


class EmbeddingRegenerationService:
    """Regenerates the vector embedding for a single Media record."""

    def regenerate(self, db: Session, film: Media) -> int:
        """
        Encode film text and persist new embedding.

        Returns the embedding dimension.
        """
        svc = EmbeddingService()
        genre_names = " ".join(g.name for g in (film.genres or []))
        text = f"{film.title} {film.overview or ''} {genre_names}".strip()
        vector = svc.encode(text)
        film.embedding = vector.tolist() if hasattr(vector, "tolist") else list(vector)
        film.embedding_needs_rebuild = False
        db.commit()

        logger.info(f"Regenerated embedding for film {film.id}: {film.title!r}")
        return len(film.embedding)


# Cache key format — single source of truth shared with sixty route
def sixty_cache_key(mood: str, context: str, craving: str) -> str:
    return f"sixty:{mood}:{context}:{craving}"


_SIXTY_CACHE_TTL = 86400  # 24 hours — single source of truth for sixty-mode cache lifetime


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
