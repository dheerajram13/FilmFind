"""
Async fire-and-forget session logging for search and 60-second mode.

All writes use asyncio.create_task so they never block the HTTP response.
"""
import asyncio
import uuid
from datetime import datetime
from typing import Any

from loguru import logger
from sqlalchemy.orm import Session

from app.models.session import SearchSession, SixtySession


# ---------------------------------------------------------------------------
# Search session helpers
# ---------------------------------------------------------------------------


async def _write_search_session(
    db: Session,
    query_text: str,
    query_parsed: dict,
    results: list,
    session_token: str,
    response_ms: int,
) -> str:
    session_id = str(uuid.uuid4())
    try:
        record = SearchSession(
            id=session_id,
            session_token=session_token,
            query_text=query_text,
            query_parsed=query_parsed,
            results=results,
            response_ms=response_ms,
            created_at=datetime.utcnow(),
        )
        db.add(record)
        db.commit()
    except Exception as exc:
        logger.warning(f"Failed to log search session: {exc}")
        try:
            db.rollback()
        except Exception:
            pass
    return session_id


def log_search_session(
    db: Session,
    query_text: str,
    query_parsed: dict,
    results: list,
    session_token: str,
    response_ms: int,
) -> str:
    """
    Fire-and-forget: log a search session.

    Returns the session_id immediately (before write completes).
    """
    session_id = str(uuid.uuid4())
    asyncio.create_task(
        _write_search_session(db, query_text, query_parsed, results, session_token, response_ms)
    )
    return session_id


async def update_search_click(db: Session, session_id: str, film_id: int) -> None:
    """Mark which result was clicked."""
    try:
        record = db.query(SearchSession).filter(SearchSession.id == session_id).first()
        if record:
            record.result_clicked_id = film_id
            db.commit()
    except Exception as exc:
        logger.warning(f"Failed to update search click: {exc}")
        try:
            db.rollback()
        except Exception:
            pass


# ---------------------------------------------------------------------------
# Sixty session helpers
# ---------------------------------------------------------------------------


async def _write_sixty_session(
    db: Session,
    mood: str,
    context: str,
    craving: str,
    film_id: int,
    match_score: int,
    seconds_taken: int,
    session_token: str,
) -> str:
    session_id = str(uuid.uuid4())
    try:
        record = SixtySession(
            id=session_id,
            session_token=session_token,
            mood=mood,
            context=context,
            craving=craving,
            film_picked_id=film_id,
            match_score=match_score,
            seconds_taken=seconds_taken,
            created_at=datetime.utcnow(),
        )
        db.add(record)
        db.commit()
    except Exception as exc:
        logger.warning(f"Failed to log sixty session: {exc}")
        try:
            db.rollback()
        except Exception:
            pass
    return session_id


def log_sixty_session(
    db: Session,
    mood: str,
    context: str,
    craving: str,
    film_id: int,
    match_score: int,
    seconds_taken: int,
    session_token: str,
) -> str:
    """
    Fire-and-forget: log a 60-second mode session.

    Returns a session_id immediately.
    """
    session_id = str(uuid.uuid4())
    asyncio.create_task(
        _write_sixty_session(
            db, mood, context, craving, film_id, match_score, seconds_taken, session_token
        )
    )
    return session_id


async def update_sixty_action(
    db: Session,
    session_id: str,
    watch: bool = False,
    share: bool = False,
    retry: bool = False,
) -> None:
    """Update watch/share/retry click flags on an existing sixty session."""
    try:
        record = db.query(SixtySession).filter(SixtySession.id == session_id).first()
        if record:
            if watch:
                record.watch_clicked = True
            if share:
                record.share_clicked = True
            if retry:
                record.retry_clicked = True
            db.commit()
    except Exception as exc:
        logger.warning(f"Failed to update sixty action: {exc}")
        try:
            db.rollback()
        except Exception:
            pass
