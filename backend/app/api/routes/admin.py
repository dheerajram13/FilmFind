"""
Admin endpoints — requires Bearer token (ADMIN_SECRET).

Provides:
- POST /admin/enrich/{film_id}         — run Stage 2 enrichment on a single film
- POST /admin/embed/{film_id}          — regenerate embedding for a single film
- POST /admin/cache/sixty/refresh      — bust and rebuild all 216 sixty-mode cache entries
- GET  /admin/analytics/searches       — top queries + CTR from search_sessions
- GET  /admin/analytics/sixty          — mood/context/craving breakdown from sixty_sessions
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func

from app.api.dependencies import DatabaseSession, require_admin
from app.models.media import Media
from app.models.session import SearchSession, SixtySession
from app.services.film_admin_service import (
    EmbeddingRegenerationService,
    FilmEnrichmentService,
    SixtyRefreshService,
)
from app.utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/admin", tags=["admin"])


# ---------------------------------------------------------------------------
# Enrichment endpoints
# ---------------------------------------------------------------------------


@router.post(
    "/enrich/{film_id}",
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(require_admin)],
)
async def enrich_film(film_id: int, db: DatabaseSession) -> dict:
    """Run Stage 2 Gemini enrichment on a single film."""
    film = db.query(Media).filter(Media.id == film_id).first()
    if not film:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Film {film_id} not found")

    try:
        result = FilmEnrichmentService().enrich(db, film)
        return {"film_id": film_id, "title": film.title, "status": "enriched", **result}
    except ValueError as exc:
        logger.warning(f"Admin enrich validation error for film {film_id}: {exc}")
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Enrichment validation failed")
    except Exception as exc:
        logger.error(f"Admin enrich failed for film {film_id}: {exc}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Enrichment failed")


@router.post(
    "/embed/{film_id}",
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(require_admin)],
)
async def regenerate_embedding(film_id: int, db: DatabaseSession) -> dict:
    """Regenerate the FAISS embedding for a single film."""
    film = db.query(Media).filter(Media.id == film_id).first()
    if not film:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Film {film_id} not found")

    try:
        dim = EmbeddingRegenerationService().regenerate(db, film)
        return {"film_id": film_id, "title": film.title, "dim": dim, "status": "embedded"}
    except Exception as exc:
        logger.error(f"Admin embed failed for film {film_id}: {exc}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Embedding regeneration failed")


# ---------------------------------------------------------------------------
# Cache endpoints
# ---------------------------------------------------------------------------


@router.post(
    "/cache/sixty/refresh",
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(require_admin)],
)
async def refresh_sixty_cache(db: DatabaseSession) -> dict:
    """
    Bust and rebuild the Redis cache for all 216 mood×context×craving combinations.
    """
    return SixtyRefreshService().refresh(db)


# ---------------------------------------------------------------------------
# Analytics endpoints
# ---------------------------------------------------------------------------


@router.get(
    "/analytics/searches",
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(require_admin)],
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

    rows = (
        db.query(SearchSession.query_text, func.count(SearchSession.id).label("count"))
        .filter(SearchSession.query_text.isnot(None))
        .group_by(SearchSession.query_text)
        .order_by(func.count(SearchSession.id).desc())
        .limit(limit)
        .all()
    )

    return {
        "total_sessions": total_sessions,
        "sessions_with_click": sessions_with_click,
        "ctr": ctr,
        "top_queries": [{"query": r.query_text, "count": r.count} for r in rows],
    }


@router.get(
    "/analytics/sixty",
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(require_admin)],
)
async def analytics_sixty(db: DatabaseSession) -> dict:
    """Mood/context/craving breakdown from sixty_sessions."""
    total = db.query(func.count(SixtySession.id)).scalar() or 0

    def _breakdown(field):
        return (
            db.query(field, func.count(SixtySession.id).label("count"))
            .filter(field.isnot(None))
            .group_by(field)
            .order_by(func.count(SixtySession.id).desc())
            .all()
        )

    watch_count = db.query(func.count(SixtySession.id)).filter(SixtySession.watch_clicked.is_(True)).scalar() or 0
    share_count = db.query(func.count(SixtySession.id)).filter(SixtySession.share_clicked.is_(True)).scalar() or 0
    retry_count = db.query(func.count(SixtySession.id)).filter(SixtySession.retry_clicked.is_(True)).scalar() or 0

    return {
        "total_sessions": total,
        "watch_rate": round(watch_count / total, 4) if total > 0 else 0.0,
        "share_rate": round(share_count / total, 4) if total > 0 else 0.0,
        "retry_rate": round(retry_count / total, 4) if total > 0 else 0.0,
        "mood_breakdown": [{"mood": r.mood, "count": r.count} for r in _breakdown(SixtySession.mood)],
        "context_breakdown": [{"context": r.context, "count": r.count} for r in _breakdown(SixtySession.context)],
        "craving_breakdown": [{"craving": r.craving, "count": r.count} for r in _breakdown(SixtySession.craving)],
    }
