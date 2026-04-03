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

Each component is normalised to [0,1] using:
    (raw / abs_weight_sum + 1.0) / 2.0   (for signed dot-products)
    direct JSONB lookup clamped to [0,1]  (for ctx_fit, crav_fit)
"""
from __future__ import annotations

from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session, load_only

from app.core.scoring import (
    CONTEXT_MAX_DARKNESS,
    CRAVING_BOOSTERS,
    MOOD_PROFILES,
    _MOOD_SCORE_KEYS,
)
from app.models.media import Media
from app.utils.logger import get_logger

logger = get_logger(__name__)

# Number of scored candidates returned from the DB (weighted_random_top3 picks 1)
_TOP_K = 10
if not (isinstance(_TOP_K, int) and 1 <= _TOP_K <= 100):
    raise ValueError(f"Invalid _TOP_K value: {_TOP_K!r}")

# Whitelist of allowed mood score keys — guards the f-string SQL fragment
_ALLOWED_MOOD_KEYS: frozenset[str] = frozenset(_MOOD_SCORE_KEYS)


def score_films_sql(
    db: Session,
    mood: str,
    context: str,
    craving: str,
    excluded_film_ids: list[int] | None = None,
) -> list[tuple[Media, float]]:
    """
    Score all fully-enriched films in Postgres and return the top _TOP_K.

    Args:
        db: SQLAlchemy session.
        mood: Validated mood string (e.g. "happy").
        context: Validated context string (e.g. "solo-night").
        craving: Validated craving string (e.g. "laugh").
        excluded_film_ids: Film IDs to exclude (e.g. already seen this session).
    Returns:
        List of (Media, score) tuples ordered by score descending, length ≤ _TOP_K.
        Returns [] if no enriched films exist.
    """
    profile = MOOD_PROFILES[mood]
    booster = CRAVING_BOOSTERS[craving]
    max_dark = CONTEXT_MAX_DARKNESS[context]

    # ── Build coefficient dicts ───────────────────────────────────────────
    # Dimensional weights from mood profile
    dim_keys = ["energy", "complexity"]
    dim_w = {k: profile.get(k, 0.0) for k in dim_keys}
    dim_abs = sum(abs(w) for w in dim_w.values()) or 1.0  # fallback to 1.0 → neutral 0.5 score

    # Mood fingerprint weights from mood profile (mood_* keys → strip prefix)
    mood_w = {k: profile.get(f"mood_{k}", 0.0) for k in _MOOD_SCORE_KEYS}
    mood_abs = sum(abs(w) for w in mood_w.values()) or 1.0  # fallback to 1.0 → neutral 0.5 score

    # Craving dimensional weights from booster
    crav_dim_w = {k: booster.get(k, 0.0) for k in dim_keys}
    crav_dim_abs = sum(abs(w) for w in crav_dim_w.values()) or 1.0  # fallback to 1.0 → neutral 0.5 score

    # ── Validate mood keys before injecting into SQL f-string ─────────────
    for k in _MOOD_SCORE_KEYS:
        if k not in _ALLOWED_MOOD_KEYS or not k.isidentifier():
            raise ValueError(f"Invalid mood key: {k!r}")

    # ── Build SQL parameter dict ──────────────────────────────────────────
    params: dict[str, Any] = {
        "max_dark": max_dark,
        "context": context,
        "craving": craving,
        # Dimensional fit coefficients
        "w_energy": dim_w["energy"],
        "w_complexity": dim_w["complexity"],
        "dim_abs": dim_abs,
        # Mood fit coefficients (one per mood score key)
        "mood_abs": mood_abs,
        # Craving dimensional fit coefficients
        "cw_energy": crav_dim_w["energy"],
        "cw_complexity": crav_dim_w["complexity"],
        "crav_dim_abs": crav_dim_abs,
        # Exclusion lists
        "excluded_ids": excluded_film_ids or [],
        "no_exclusions": not bool(excluded_film_ids),
    }
    # Add one param per mood key
    for k in _MOOD_SCORE_KEYS:
        params[f"mw_{k}"] = mood_w[k]

    # ── Build mood_raw SQL fragment ───────────────────────────────────────
    # mood_scores JSONB is keyed by mood name (happy, sad, charged, ...)
    # Keys are validated above — safe to use in f-string.
    mood_raw_parts = " + ".join(
        f":mw_{k} * COALESCE((mood_scores ->> '{k}')::float, 0.5)"
        for k in _MOOD_SCORE_KEYS
    )

    sql = text(f"""
        SELECT
            id,
            (
                -- dim_fit * 0.25
                (
                    (
                        :w_energy * (COALESCE(energy_score, 5)::float / 10.0)
                        + :w_complexity * (COALESCE(complexity_score, 5)::float / 10.0)
                    ) / :dim_abs + 1.0
                ) / 2.0 * 0.25

                -- mood_fit * 0.25
                + (
                    (
                        ({mood_raw_parts})
                    ) / :mood_abs + 1.0
                ) / 2.0 * 0.25

                -- ctx_fit * 0.20  (direct JSONB lookup, default 0.5)
                + LEAST(1.0, GREATEST(0.0,
                    COALESCE((context_scores ->> :context)::float, 0.5)
                  )) * 0.20

                -- crav_dim_fit * 0.15
                + (
                    (
                        :cw_energy * (COALESCE(energy_score, 5)::float / 10.0)
                        + :cw_complexity * (COALESCE(complexity_score, 5)::float / 10.0)
                    ) / :crav_dim_abs + 1.0
                ) / 2.0 * 0.15

                -- crav_fit * 0.15  (direct JSONB lookup, default 0.5)
                + LEAST(1.0, GREATEST(0.0,
                    COALESCE((craving_scores ->> :craving)::float, 0.5)
                  )) * 0.15
            ) AS score
        FROM media
        WHERE
            adult = FALSE
            AND is_fully_scored = TRUE
            AND COALESCE(darkness_score, 5) <= :max_dark
            AND (:no_exclusions OR id != ALL(:excluded_ids))
        ORDER BY score DESC
        LIMIT {_TOP_K}
    """)

    rows = db.execute(sql, params).fetchall()

    if not rows:
        logger.info(f"score_films_sql: no enriched films for {mood}/{context}/{craving}")
        return []

    # Bulk-fetch the ORM objects for the returned IDs (preserves order).
    # load_only excludes large unused columns (embedding ~3KB/row, narrative_dna).
    ids = [row.id for row in rows]
    score_by_id = {row.id: float(row.score) for row in rows}

    films = (
        db.query(Media)
        .filter(Media.id.in_(ids))
        .options(load_only(
            Media.id,
            Media.tmdb_id,
            Media.media_type,
            Media.title,
            Media.release_date,
            Media.overview,
            Media.poster_path,
            Media.backdrop_path,
            Media.poster_supabase_url,
            Media.backdrop_supabase_url,
            Media.genres,
            Media.vote_average,
            Media.vote_count,
            Media.popularity,
            Media.original_language,
            Media.adult,
            Media.narrative_dna,
            Media.tone_tags,
            Media.mood_scores,
            Media.context_scores,
            Media.craving_scores,
            Media.energy_score,
            Media.complexity_score,
            Media.darkness_score,
            Media.is_fully_scored,
        ))
        .all()
    )
    film_by_id = {f.id: f for f in films}

    # Return in score-descending order
    result = []
    for fid in ids:
        if fid in film_by_id:
            result.append((film_by_id[fid], score_by_id[fid]))

    logger.info(f"score_films_sql: {len(result)} results for {mood}/{context}/{craving}")
    logger.debug(
        f"score_films_sql: best score={result[0][1]:.3f}" if result else "score_films_sql: empty"
    )
    return result
