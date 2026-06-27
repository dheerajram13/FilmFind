"""
SQL-based scoring service for 60-Second Mode.

Pushes the full V2 scoring formula into a single Postgres query so Python
receives at most 10 rows instead of the entire media table.

Architecture:
- score_films_sql() builds parameterised SQL and returns top-10 (film, score) rows
- The caller (sixty.py) then calls weighted_random_top3() on those 10 rows
- No Python-side loop over the full film catalogue

Formula (same as scoring.py, implemented in SQL):
    score = dim_fit*0.25 + mood_fit*0.25 + ctx_fit*0.20 + crav_dim_fit*0.15 + crav_fit*0.15

Scoring columns now live in media_enrichment (joined via media_id).
The query unions movies and tv_shows so both types are scored together.
"""
from __future__ import annotations

from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.scoring import (
    CONTEXT_MAX_DARKNESS,
    CRAVING_BOOSTERS,
    MOOD_PROFILES,
    _MOOD_SCORE_KEYS,
)
from app.models.media import Media, Movie, TVShow
from app.utils.logger import get_logger

logger = get_logger(__name__)

_TOP_K = 10
if not (isinstance(_TOP_K, int) and 1 <= _TOP_K <= 100):
    raise ValueError(f"Invalid _TOP_K value: {_TOP_K!r}")

_ALLOWED_MOOD_KEYS: frozenset[str] = frozenset(_MOOD_SCORE_KEYS)


def score_films_sql(
    db: Session,
    mood: str,
    context: str,
    craving: str,
    excluded_film_ids: list[int] | None = None,
) -> list[tuple[Media, float]]:
    """
    Score all fully-enriched films via a single Postgres query and return top _TOP_K.

    Scores movies and tv_shows together by joining each to media_enrichment.
    Returns (Media-anchor, score) tuples; callers use media.movie / media.tv_show
    to access the concrete record.

    Args:
        db: SQLAlchemy session.
        mood: Validated mood string (e.g. "happy").
        context: Validated context string (e.g. "solo-night").
        craving: Validated craving string (e.g. "laugh").
        excluded_film_ids: media_id values to exclude (already seen this session).
    Returns:
        List of (Media, score) tuples ordered score descending, length ≤ _TOP_K.
    """
    profile = MOOD_PROFILES[mood]
    booster = CRAVING_BOOSTERS[craving]
    max_dark = CONTEXT_MAX_DARKNESS[context]

    dim_keys = ["energy", "complexity"]
    dim_w = {k: profile.get(k, 0.0) for k in dim_keys}
    dim_abs = sum(abs(w) for w in dim_w.values()) or 1.0

    mood_w = {k: profile.get(f"mood_{k}", 0.0) for k in _MOOD_SCORE_KEYS}
    mood_abs = sum(abs(w) for w in mood_w.values()) or 1.0

    crav_dim_w = {k: booster.get(k, 0.0) for k in dim_keys}
    crav_dim_abs = sum(abs(w) for w in crav_dim_w.values()) or 1.0

    for k in _MOOD_SCORE_KEYS:
        if k not in _ALLOWED_MOOD_KEYS or not k.isidentifier():
            raise ValueError(f"Invalid mood key: {k!r}")

    params: dict[str, Any] = {
        "max_dark": max_dark,
        "context": context,
        "craving": craving,
        "w_energy": dim_w["energy"],
        "w_complexity": dim_w["complexity"],
        "dim_abs": dim_abs,
        "mood_abs": mood_abs,
        "cw_energy": crav_dim_w["energy"],
        "cw_complexity": crav_dim_w["complexity"],
        "crav_dim_abs": crav_dim_abs,
        "excluded_ids": excluded_film_ids or [],
        "no_exclusions": not bool(excluded_film_ids),
    }
    for k in _MOOD_SCORE_KEYS:
        params[f"mw_{k}"] = mood_w[k]

    mood_raw_parts = " + ".join(
        f":mw_{k} * COALESCE((e.mood_scores ->> '{k}')::float, 0.5)"
        for k in _MOOD_SCORE_KEYS
    )

    # Score formula runs over media_enrichment (e), filtering adult=FALSE from
    # movies/tv_shows. UNION ALL combines both types under their shared media_id.
    sql = text(f"""
        WITH candidates AS (
            SELECT m.media_id AS media_id, m.adult
            FROM movies m
            UNION ALL
            SELECT t.media_id AS media_id, t.adult
            FROM tv_shows t
        )
        SELECT
            c.media_id,
            (
                -- dim_fit * 0.25
                (
                    (
                        :w_energy    * (COALESCE(e.energy_score, 5)::float / 10.0)
                        + :w_complexity * (COALESCE(e.complexity_score, 5)::float / 10.0)
                    ) / :dim_abs + 1.0
                ) / 2.0 * 0.25

                -- mood_fit * 0.25
                + (
                    (
                        ({mood_raw_parts})
                    ) / :mood_abs + 1.0
                ) / 2.0 * 0.25

                -- ctx_fit * 0.20
                + LEAST(1.0, GREATEST(0.0,
                    COALESCE((e.context_scores ->> :context)::float, 0.5)
                  )) * 0.20

                -- crav_dim_fit * 0.15
                + (
                    (
                        :cw_energy    * (COALESCE(e.energy_score, 5)::float / 10.0)
                        + :cw_complexity * (COALESCE(e.complexity_score, 5)::float / 10.0)
                    ) / :crav_dim_abs + 1.0
                ) / 2.0 * 0.15

                -- crav_fit * 0.15
                + LEAST(1.0, GREATEST(0.0,
                    COALESCE((e.craving_scores ->> :craving)::float, 0.5)
                  )) * 0.15
            ) AS score
        FROM candidates c
        JOIN media_enrichment e ON e.media_id = c.media_id
        WHERE
            c.adult = FALSE
            AND e.is_fully_scored = TRUE
            AND COALESCE(e.darkness_score, 5) <= :max_dark
            AND (:no_exclusions OR c.media_id != ALL(:excluded_ids))
        ORDER BY score DESC
        LIMIT {_TOP_K}
    """)

    rows = db.execute(sql, params).fetchall()

    if not rows:
        logger.info(f"score_films_sql: no enriched films for {mood}/{context}/{craving}")
        return []

    media_ids = [row.media_id for row in rows]
    score_by_id = {row.media_id: float(row.score) for row in rows}

    # Fetch Media anchors with enrichment + assets eagerly loaded
    from sqlalchemy.orm import selectinload
    anchors = (
        db.query(Media)
        .filter(Media.id.in_(media_ids))
        .options(
            selectinload(Media.movie),
            selectinload(Media.tv_show),
            selectinload(Media.enrichment),
            selectinload(Media.assets),
        )
        .all()
    )
    anchor_by_id = {a.id: a for a in anchors}

    result = []
    for mid in media_ids:
        if mid in anchor_by_id:
            result.append((anchor_by_id[mid], score_by_id[mid]))

    logger.info(f"score_films_sql: {len(result)} results for {mood}/{context}/{craving}")
    if result:
        logger.debug(f"score_films_sql: best score={result[0][1]:.3f}")
    return result
