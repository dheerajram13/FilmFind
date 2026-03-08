"""
Admin endpoints — requires Bearer token (ADMIN_SECRET).

Provides:
- POST /admin/enrich/{film_id}         — run Stage 2 enrichment on a single film
- POST /admin/embed/{film_id}          — regenerate embedding for a single film
- POST /admin/cache/sixty/refresh      — bust and rebuild all 216 sixty-mode cache entries
- GET  /admin/analytics/searches       — top queries + CTR from search_sessions
- GET  /admin/analytics/sixty          — mood/context/craving breakdown from sixty_sessions
"""
from collections import Counter
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.api.dependencies import DatabaseSession
from app.core.cache_manager import get_cache_manager
from app.core.config import settings
from app.core.scoring import VALID_CONTEXTS, VALID_CRAVINGS, VALID_MOODS
from app.models.media import Media
from app.models.session import SearchSession, SixtySession
from app.services.sixty_scorer import score_films_sql
from app.utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/admin", tags=["admin"])

_bearer = HTTPBearer(auto_error=False)


def _require_admin(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(_bearer),
) -> None:
    """Verify the Bearer token matches ADMIN_SECRET."""
    secret = settings.ADMIN_SECRET
    if not secret:
        # Admin secret not configured — block all admin requests
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Admin endpoints are not enabled (ADMIN_SECRET not configured)",
        )
    if credentials is None or credentials.credentials != secret:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing admin token",
            headers={"WWW-Authenticate": "Bearer"},
        )


# ---------------------------------------------------------------------------
# Enrichment endpoints
# ---------------------------------------------------------------------------


@router.post(
    "/enrich/{film_id}",
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(_require_admin)],
)
async def enrich_film(film_id: int, db: DatabaseSession) -> dict:
    """Run Stage 2 Gemini enrichment on a single film."""
    film = db.query(Media).filter(Media.id == film_id).first()
    if not film:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Film {film_id} not found")

    try:
        import json
        from app.services.llm_client import LLMClient

        client = LLMClient()
        genre_names = ", ".join(g.name for g in (film.genres or []))
        overview = film.overview or "No overview available."

        prompt = (
            f'Title: "{film.title}"\n'
            f"Genres: {genre_names or 'unknown'}\n"
            f"Overview: {overview[:500]}\n\n"
            "Analyse this film and return the JSON enrichment data."
        )
        _SYSTEM = (
            "You are a film analysis expert. Respond ONLY with valid JSON:\n"
            '{"narrative_dna":"...","themes":[...],"tone_tags":[...],'
            '"darkness_score":0,"complexity_score":0,"energy_score":0}'
        )
        raw = client.generate_completion(prompt=prompt, system_prompt=_SYSTEM, temperature=0.3, max_tokens=512, response_format={"type": "json_object"})

        try:
            data = json.loads(raw)
        except Exception:
            raise HTTPException(status_code=500, detail="LLM returned invalid JSON")

        film.narrative_dna = data.get("narrative_dna")
        film.themes = data.get("themes") or []
        film.tone_tags = data.get("tone_tags") or []
        film.darkness_score = _clamp(data.get("darkness_score"), 0, 10)
        film.complexity_score = _clamp(data.get("complexity_score"), 0, 10)
        film.energy_score = _clamp(data.get("energy_score"), 0, 10)
        db.commit()

        logger.info(f"Admin enriched film {film_id}: {film.title!r}")
        return {"film_id": film_id, "title": film.title, "status": "enriched"}

    except HTTPException:
        raise
    except Exception as exc:
        logger.error(f"Admin enrich failed for film {film_id}: {exc}")
        raise HTTPException(status_code=500, detail=str(exc))


@router.post(
    "/embed/{film_id}",
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(_require_admin)],
)
async def regenerate_embedding(film_id: int, db: DatabaseSession) -> dict:
    """Regenerate the FAISS embedding for a single film."""
    film = db.query(Media).filter(Media.id == film_id).first()
    if not film:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Film {film_id} not found")

    try:
        from app.services.embedding_service import EmbeddingService

        svc = EmbeddingService()
        genre_names = " ".join(g.name for g in (film.genres or []))
        text = f"{film.title} {film.overview or ''} {genre_names}".strip()
        vector = svc.encode(text)
        film.embedding = vector.tolist() if hasattr(vector, "tolist") else list(vector)
        film.embedding_needs_rebuild = False
        db.commit()

        logger.info(f"Admin regenerated embedding for film {film_id}: {film.title!r}")
        return {"film_id": film_id, "title": film.title, "dim": len(film.embedding), "status": "embedded"}

    except Exception as exc:
        logger.error(f"Admin embed failed for film {film_id}: {exc}")
        raise HTTPException(status_code=500, detail=str(exc))


# ---------------------------------------------------------------------------
# Cache endpoints
# ---------------------------------------------------------------------------


@router.post(
    "/cache/sixty/refresh",
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(_require_admin)],
)
async def refresh_sixty_cache(db: DatabaseSession) -> dict:
    """
    Bust and rebuild the Redis cache for all 216 mood×context×craving combinations.

    Deletes all existing "sixty:*" keys, then scores each combination via
    score_films_sql() and stores the top-10 results.  Returns a summary of how
    many combinations were cached vs skipped (no enriched films).

    This endpoint lets you rebuild stale cache after a score_films.py run
    without restarting the server.
    """
    cache = get_cache_manager()

    # Delete all existing sixty cache entries
    deleted = cache.delete_pattern("sixty:*")
    logger.info(f"cache/sixty/refresh: deleted {deleted} existing cache keys")

    cached = 0
    skipped = 0
    errors = 0

    for mood in VALID_MOODS:
        for context in VALID_CONTEXTS:
            for craving in VALID_CRAVINGS:
                try:
                    scored = score_films_sql(db, mood, context, craving)
                    if scored:
                        key = f"sixty:{mood}:{context}:{craving}"
                        payload = [{"id": f.id, "score": s} for f, s in scored]
                        cache.set(key, payload, ttl=86400)
                        cached += 1
                    else:
                        skipped += 1
                except Exception as exc:
                    logger.error(f"cache refresh error {mood}/{context}/{craving}: {exc}")
                    errors += 1

    logger.info(
        f"cache/sixty/refresh complete: cached={cached} skipped={skipped} errors={errors}"
    )
    return {
        "status": "ok",
        "deleted_old_keys": deleted,
        "combinations_cached": cached,
        "combinations_skipped_no_films": skipped,
        "errors": errors,
        "total_combinations": len(VALID_MOODS) * len(VALID_CONTEXTS) * len(VALID_CRAVINGS),
    }


# ---------------------------------------------------------------------------
# Analytics endpoints
# ---------------------------------------------------------------------------


@router.get(
    "/analytics/searches",
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(_require_admin)],
)
async def analytics_searches(db: DatabaseSession, limit: int = 20) -> dict:
    """Top search queries and click-through rates from search_sessions."""
    total_sessions = db.query(func.count(SearchSession.id)).scalar() or 0
    sessions_with_click = (
        db.query(func.count(SearchSession.id))
        .filter(SearchSession.result_clicked_id.isnot(None))
        .scalar()
        or 0
    )
    ctr = round(sessions_with_click / total_sessions, 4) if total_sessions > 0 else 0.0

    # Top queries by frequency
    rows = (
        db.query(SearchSession.query_text, func.count(SearchSession.id).label("count"))
        .filter(SearchSession.query_text.isnot(None))
        .group_by(SearchSession.query_text)
        .order_by(func.count(SearchSession.id).desc())
        .limit(limit)
        .all()
    )
    top_queries = [{"query": r.query_text, "count": r.count} for r in rows]

    return {
        "total_sessions": total_sessions,
        "sessions_with_click": sessions_with_click,
        "ctr": ctr,
        "top_queries": top_queries,
    }


@router.get(
    "/analytics/sixty",
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(_require_admin)],
)
async def analytics_sixty(db: DatabaseSession) -> dict:
    """Mood/context/craving breakdown from sixty_sessions."""
    total = db.query(func.count(SixtySession.id)).scalar() or 0

    mood_rows = (
        db.query(SixtySession.mood, func.count(SixtySession.id).label("count"))
        .filter(SixtySession.mood.isnot(None))
        .group_by(SixtySession.mood)
        .order_by(func.count(SixtySession.id).desc())
        .all()
    )
    context_rows = (
        db.query(SixtySession.context, func.count(SixtySession.id).label("count"))
        .filter(SixtySession.context.isnot(None))
        .group_by(SixtySession.context)
        .order_by(func.count(SixtySession.id).desc())
        .all()
    )
    craving_rows = (
        db.query(SixtySession.craving, func.count(SixtySession.id).label("count"))
        .filter(SixtySession.craving.isnot(None))
        .group_by(SixtySession.craving)
        .order_by(func.count(SixtySession.id).desc())
        .all()
    )

    watch_count = db.query(func.count(SixtySession.id)).filter(SixtySession.watch_clicked == True).scalar() or 0  # noqa: E712
    share_count = db.query(func.count(SixtySession.id)).filter(SixtySession.share_clicked == True).scalar() or 0  # noqa: E712
    retry_count = db.query(func.count(SixtySession.id)).filter(SixtySession.retry_clicked == True).scalar() or 0  # noqa: E712

    return {
        "total_sessions": total,
        "watch_rate": round(watch_count / total, 4) if total > 0 else 0.0,
        "share_rate": round(share_count / total, 4) if total > 0 else 0.0,
        "retry_rate": round(retry_count / total, 4) if total > 0 else 0.0,
        "mood_breakdown": [{"mood": r.mood, "count": r.count} for r in mood_rows],
        "context_breakdown": [{"context": r.context, "count": r.count} for r in context_rows],
        "craving_breakdown": [{"craving": r.craving, "count": r.count} for r in craving_rows],
    }


def _clamp(value, lo: int, hi: int) -> Optional[int]:
    if value is None:
        return None
    try:
        return max(lo, min(hi, int(value)))
    except (TypeError, ValueError):
        return None
