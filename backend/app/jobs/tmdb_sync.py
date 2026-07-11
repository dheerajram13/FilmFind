"""
TMDB daily delta sync job.

Uses the TMDB /movie/changes and /tv/changes endpoints to get IDs of films that
changed in the last 24 hours, then fetches full details and upserts mutable
fields. Marks media_embedding.needs_rebuild = TRUE so stale embeddings are
regenerated on the next embedding run.

New films detected here are NOT fully ingested (no image upload, no relational
linking). The weekly full ingest via ingest_media.py handles that.
"""

import json
from datetime import UTC, datetime, timedelta
from typing import Optional

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.services.tmdb.tmdb_service import TMDBService
from app.utils.job_utils import JobStats, execute_with_db
from app.utils.logger import get_logger

logger = get_logger(__name__)


def sync_tmdb_data() -> dict:
    """
    Daily delta sync — runs via APScheduler.

    Fetches changed movie and TV show IDs from TMDB's changes endpoints,
    updates mutable fields, and marks embeddings for rebuild.
    """
    return execute_with_db(
        _sync_logic,
        "TMDB delta sync",
        {"movies_updated": 0, "tv_updated": 0, "new_detected": 0, "failed": 0},
    )


def _sync_logic(db: Session, stats: JobStats) -> None:
    tmdb = TMDBService()
    start_date = (datetime.now(UTC) - timedelta(days=1)).date().isoformat()

    logger.info(f"TMDB delta sync — changes since {start_date}")

    # Movies
    movie_ids = tmdb.client.get_movie_changes(start_date)
    logger.info(f"  {len(movie_ids)} changed movie IDs")
    for tmdb_id in movie_ids:
        result = _sync_one(db, tmdb, tmdb_id, is_tv=False)
        if result == "updated":
            stats.increment("movies_updated")
        elif result == "new":
            stats.increment("new_detected")
        elif result == "failed":
            stats.increment("failed")

    # TV shows
    tv_ids = tmdb.client.get_tv_changes(start_date)
    logger.info(f"  {len(tv_ids)} changed TV IDs")
    for tmdb_id in tv_ids:
        result = _sync_one(db, tmdb, tmdb_id, is_tv=True)
        if result == "updated":
            stats.increment("tv_updated")
        elif result == "new":
            stats.increment("new_detected")
        elif result == "failed":
            stats.increment("failed")

    logger.info(
        f"Sync complete — movies_updated={stats.get('movies_updated')} "
        f"tv_updated={stats.get('tv_updated')} "
        f"new_detected={stats.get('new_detected')} "
        f"failed={stats.get('failed')}"
    )


def _sync_one(db: Session, tmdb: TMDBService, tmdb_id: int, is_tv: bool) -> str:
    """
    Fetch full details for one changed film and upsert mutable fields.

    Returns: "updated" | "new" | "skipped" | "failed"
    """
    try:
        full = tmdb.client.get_tv_show(tmdb_id) if is_tv else tmdb.client.get_movie(tmdb_id)
        if not full:
            return "skipped"

        if is_tv:
            if not tmdb.validator.validate_tv_show(full):
                return "skipped"
            cleaned = tmdb.validator.clean_tv_show_data(full)
            table = "tv_shows"
        else:
            if not tmdb.validator.validate_movie(full):
                return "skipped"
            cleaned = tmdb.validator.clean_movie_data(full)
            table = "movies"

        row = db.execute(
            text(f"SELECT media_id FROM {table} WHERE tmdb_id = :tid"),
            {"tid": tmdb_id},
        ).fetchone()

        if not row:
            # Not in our catalogue yet — weekly full ingest will add it if it
            # meets the quality floor. Log and skip.
            logger.debug(f"tmdb_id={tmdb_id} not in catalogue, skipping delta sync")
            return "new"

        media_id = row.media_id

        # Update mutable fields — all scalar columns that change over time
        if is_tv:
            db.execute(text("""
                UPDATE tv_shows SET
                    title               = :title,
                    overview            = :overview,
                    status              = :status,
                    popularity          = :popularity,
                    vote_average        = :vote_average,
                    vote_count          = :vote_count,
                    streaming_providers = :streaming_providers,
                    number_of_seasons   = :seasons,
                    number_of_episodes  = :episodes,
                    in_production       = :in_production,
                    last_air_date       = :last_air,
                    updated_at          = NOW()
                WHERE tmdb_id = :tmdb_id
            """), {
                "title": cleaned["title"],
                "overview": cleaned.get("overview"),
                "status": cleaned.get("status"),
                "popularity": cleaned.get("popularity"),
                "vote_average": cleaned.get("vote_average"),
                "vote_count": cleaned.get("vote_count"),
                "streaming_providers": _j(cleaned.get("streaming_providers")),
                "seasons": cleaned.get("number_of_seasons"),
                "episodes": cleaned.get("number_of_episodes"),
                "in_production": cleaned.get("in_production", False),
                "last_air": cleaned.get("last_air_date"),
                "tmdb_id": tmdb_id,
            })
        else:
            db.execute(text("""
                UPDATE movies SET
                    title               = :title,
                    overview            = :overview,
                    status              = :status,
                    popularity          = :popularity,
                    vote_average        = :vote_average,
                    vote_count          = :vote_count,
                    streaming_providers = :streaming_providers,
                    updated_at          = NOW()
                WHERE tmdb_id = :tmdb_id
            """), {
                "title": cleaned["title"],
                "overview": cleaned.get("overview"),
                "status": cleaned.get("status"),
                "popularity": cleaned.get("popularity"),
                "vote_average": cleaned.get("vote_average"),
                "vote_count": cleaned.get("vote_count"),
                "streaming_providers": _j(cleaned.get("streaming_providers")),
                "tmdb_id": tmdb_id,
            })

        # Mark embedding stale — overview or other text fields may have changed
        db.execute(
            text("UPDATE media_embedding SET needs_rebuild = TRUE WHERE media_id = :mid"),
            {"mid": media_id},
        )

        db.commit()
        return "updated"

    except Exception as exc:
        logger.error(f"Failed to sync tmdb_id={tmdb_id}: {exc}")
        db.rollback()
        return "failed"


def _j(val) -> Optional[str]:
    if val is None:
        return None
    if isinstance(val, (dict, list)):
        return json.dumps(val)
    return val
