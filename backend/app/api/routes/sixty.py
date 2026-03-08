"""
60-Second Mode endpoints.

POST /sixty/pick   — score all films, pick one, return with why-reasons
POST /sixty/{session_id}/action — log watch/share/retry clicks
"""
import time
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.dependencies import DatabaseSession
from app.core.scoring import (
    CONTEXT_MAX_DARKNESS,
    VALID_CONTEXTS,
    VALID_CRAVINGS,
    VALID_MOODS,
    match_score_to_percent,
    score_film,
    weighted_random_top3,
)
from app.db.sessions import log_sixty_session, update_sixty_action
from app.models.media import Media
from app.schemas.movie import MovieResponse
from app.services.sixty_why import generate_why_reasons
from app.utils.logger import get_logger
from app.utils.movie_mapper import movie_to_response

logger = get_logger(__name__)

router = APIRouter(prefix="/sixty", tags=["sixty"])


# ---------------------------------------------------------------------------
# Request / Response schemas
# ---------------------------------------------------------------------------


class SixtyPickRequest(BaseModel):
    mood: str
    context: str
    craving: str
    session_token: str = ""
    region: Optional[str] = None
    seconds_taken: Optional[int] = None


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
# Endpoints
# ---------------------------------------------------------------------------


@router.post("/pick", status_code=status.HTTP_200_OK, response_model=SixtyPickResponse)
async def sixty_pick(
    request: SixtyPickRequest,
    db: DatabaseSession,
) -> SixtyPickResponse:
    """
    Pick one film for 60-second mode.

    Scoring pipeline:
    1. Validate mood/context/craving enum values
    2. Fetch all films that have mood_scores populated
    3. Apply CONTEXT_MAX_DARKNESS hard block
    4. score_film() on each remaining film
    5. weighted_random_top3() to select
    6. generate_why_reasons() for 3 bullets
    7. log_sixty_session() fire-and-forget
    8. Return film + match_score + why_reasons
    """
    # Validate enum values
    if request.mood not in VALID_MOODS:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid mood '{request.mood}'. Valid values: {sorted(VALID_MOODS)}",
        )
    if request.context not in VALID_CONTEXTS:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid context '{request.context}'. Valid values: {sorted(VALID_CONTEXTS)}",
        )
    if request.craving not in VALID_CRAVINGS:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid craving '{request.craving}'. Valid values: {sorted(VALID_CRAVINGS)}",
        )

    # Fetch films with mood_scores populated
    max_darkness = CONTEXT_MAX_DARKNESS.get(request.context, 10)

    films = (
        db.query(Media)
        .filter(
            Media.mood_scores.isnot(None),
            Media.adult == False,  # noqa: E712
        )
        .all()
    )

    if not films:
        # Fall back to all films if none are enriched yet
        films = (
            db.query(Media)
            .filter(Media.adult == False)  # noqa: E712
            .all()
        )

    if not films:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="No films available. Database may be empty.",
        )

    logger.info(f"sixty_pick: {len(films)} candidate films, context={request.context}")

    # Score each film (darkness filter is applied inside score_film)
    scored: list[tuple[Media, float]] = []
    for film in films:
        raw_score = score_film(film, request.mood, request.context, request.craving)
        if raw_score > 0.0:
            scored.append((film, raw_score))

    if not scored:
        # If enrichment scores block everything (e.g. strict family filter),
        # fall back to darkness-only filter on all films
        for film in films:
            film_darkness = getattr(film, "darkness_score", None) or 5
            if film_darkness <= max_darkness:
                scored.append((film, 0.5))

    if not scored:
        # Last resort — return any film
        scored = [(films[0], 0.5)]

    # Weighted random pick from top 3
    selected_film: Media = weighted_random_top3(scored)
    best_score = next(s for f, s in scored if f.id == selected_film.id)

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
