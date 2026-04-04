"""
60-Second Mode endpoints.

POST /sixty/pick   — score all films, pick one, return with why-reasons
POST /sixty/{session_id}/action — log watch/share/retry clicks

Caching strategy:
- Cache key: "sixty:{mood}:{context}:{craving}"
- TTL: 24 hours (86400 seconds)
- Cached payload: top-10 (film_id, score) pairs
- At request time, ORM objects are fetched and weighted_random_top3() is called
  on the cached candidates, so variety is preserved across cached requests.
"""
import time
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field, field_validator
from sqlalchemy.orm import Session

from app.api.dependencies import DatabaseSession, make_rate_limit_dependency
from app.core.cache_manager import get_cache_manager
from app.core.config import settings
from app.core.scoring import (
    CONTEXT_MAX_DARKNESS,
    VALID_CONTEXTS,
    VALID_CRAVINGS,
    VALID_MOODS,
    match_score_to_percent,
    weighted_random_top3,
)
from app.db.sessions import log_sixty_session, update_sixty_action
from app.models.media import Media
from app.schemas.movie import MovieResponse
from app.services.film_admin_service import sixty_cache_key
from app.services.sixty_scorer import score_films_sql
from app.services.sixty_why import generate_why_reasons
from app.utils.logger import get_logger
from app.utils.movie_mapper import movie_to_response

logger = get_logger(__name__)

router = APIRouter(prefix="/sixty", tags=["sixty"])

_sixty_rate_limit = make_rate_limit_dependency(settings.RATE_LIMIT_SIXTY_PER_MINUTE)
_SIXTY_CACHE_TTL = 86400  # 24 hours


# ---------------------------------------------------------------------------
# Request / Response schemas
# ---------------------------------------------------------------------------


class SixtyPickRequest(BaseModel):
    mood: str = Field(..., max_length=50)
    context: str = Field(..., max_length=50)
    craving: str = Field(..., max_length=50)
    session_token: str = ""
    region: Optional[str] = None
    seconds_taken: Optional[int] = None

    @field_validator("mood")
    @classmethod
    def mood_must_be_valid(cls, v: str) -> str:
        if v not in VALID_MOODS:
            raise ValueError(f"Invalid mood. Valid values: {sorted(VALID_MOODS)}")
        return v

    @field_validator("context")
    @classmethod
    def context_must_be_valid(cls, v: str) -> str:
        if v not in VALID_CONTEXTS:
            raise ValueError(f"Invalid context. Valid values: {sorted(VALID_CONTEXTS)}")
        return v

    @field_validator("craving")
    @classmethod
    def craving_must_be_valid(cls, v: str) -> str:
        if v not in VALID_CRAVINGS:
            raise ValueError(f"Invalid craving. Valid values: {sorted(VALID_CRAVINGS)}")
        return v


class SixtyPickResponse(BaseModel):
    film: MovieResponse
    match_score: int
    why_reasons: list[str]
    session_id: str


class SixtyActionRequest(BaseModel):
    watch_clicked: bool = False
    share_clicked: bool = False
    retry_clicked: bool = False


# ---------------------------------------------------------------------------
# Cache helpers
# ---------------------------------------------------------------------------


def _load_candidates_from_cache(
    db: Session, mood: str, context: str, craving: str
) -> list[tuple[Media, float]] | None:
    """
    Return cached (Media, score) pairs, or None on cache miss / disabled.
    Fetches ORM objects fresh from DB so they're attached to the current session.
    """
    cache = get_cache_manager()
    key = sixty_cache_key(mood, context, craving)
    cached = cache.get(key)
    if cached is None:
        return None

    id_score = {int(item["id"]): float(item["score"]) for item in cached}
    films = db.query(Media).filter(Media.id.in_(id_score.keys())).all()
    if not films:
        return None

    result = [(f, id_score[f.id]) for f in films if f.id in id_score]
    result.sort(key=lambda x: x[1], reverse=True)
    return result


def _store_candidates_in_cache(
    mood: str, context: str, craving: str, scored: list[tuple[Media, float]]
) -> None:
    """Persist top-10 (film_id, score) pairs to Redis."""
    cache = get_cache_manager()
    key = sixty_cache_key(mood, context, craving)
    payload = [{"id": f.id, "score": s} for f, s in scored]
    cache.set(key, payload, ttl=_SIXTY_CACHE_TTL)


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.post("/pick", status_code=status.HTTP_200_OK, response_model=SixtyPickResponse, dependencies=[Depends(_sixty_rate_limit)])
async def sixty_pick(
    request: SixtyPickRequest,
    db: DatabaseSession,
) -> SixtyPickResponse:
    """
    Pick one film for 60-second mode.

    Pipeline:
    1. Validate mood/context/craving enum values
    2. Check Redis cache ("sixty:{mood}:{context}:{craving}", 24h TTL)
       - Cache hit  → use cached top-10 candidates (no DB scoring needed)
       - Cache miss → run score_films_sql() in Postgres, cache result
    3. weighted_random_top3() with Gaussian noise for variety
    4. generate_why_reasons() for 3 bullets
    5. log_sixty_session() fire-and-forget
    6. Return film + match_score + why_reasons
    """
    # Try cache first
    scored = _load_candidates_from_cache(db, request.mood, request.context, request.craving)
    cache_hit = scored is not None

    if not scored:
        # Run SQL scoring — returns top-10 fully-enriched, darkness-filtered films
        scored = score_films_sql(db, request.mood, request.context, request.craving)

        if scored:
            _store_candidates_in_cache(request.mood, request.context, request.craving, scored)

    if not scored:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=(
                "No fully-scored films available for this combination. "
                "Run score_films.py to enrich the database."
            ),
        )

    logger.info(
        f"sixty_pick: {len(scored)} candidates "
        f"({'cache hit' if cache_hit else 'cache miss'}) "
        f"mood={request.mood} context={request.context} craving={request.craving}"
    )

    # Weighted random pick from top 3 (with noise for variety)
    selected_film: Media = weighted_random_top3(scored)
    best_score = next((s for f, s in scored if f.id == selected_film.id), 0.0)
    match_score = match_score_to_percent(best_score)

    # Generate personalised why-reasons
    try:
        why_reasons = await generate_why_reasons(
            film=selected_film,
            mood_label=request.mood,
            context_label=request.context,
            craving_label=request.craving,
        )
    except Exception as exc:
        logger.warning(f"why_reasons generation failed: {exc}")
        why_reasons = [
            f"A perfect match for your {request.mood} mood",
            f"Delivers the {request.craving} experience you want",
            "A highly rated pick you'll love",
        ]

    # Ensure exactly 3 reasons
    while len(why_reasons) < 3:
        why_reasons.append("A great pick for tonight")
    why_reasons = why_reasons[:3]

    # Fire-and-forget session log
    session_id = log_sixty_session(
        db=db,
        mood=request.mood,
        context=request.context,
        craving=request.craving,
        film_id=selected_film.id,
        match_score=match_score,
        seconds_taken=request.seconds_taken or 0,
        session_token=request.session_token,
    )

    film_response = movie_to_response(selected_film)

    logger.info(
        f"sixty_pick result: {selected_film.title!r} match_score={match_score} "
        f"mood={request.mood} context={request.context} craving={request.craving}"
    )

    return SixtyPickResponse(
        film=film_response,
        match_score=match_score,
        why_reasons=why_reasons,
        session_id=session_id,
    )


@router.post("/{session_id}/action", status_code=status.HTTP_204_NO_CONTENT)
async def sixty_action(
    session_id: str,
    request: SixtyActionRequest,
    db: DatabaseSession,
) -> None:
    """Log watch/share/retry click actions on a sixty session."""
    await update_sixty_action(
        db=db,
        session_id=session_id,
        watch=request.watch_clicked,
        share=request.share_clicked,
        retry=request.retry_clicked,
    )
