"""
60-Second Mode scoring algorithm.

Pure functions — no I/O, fully testable.
Implements the V1 spec mood/context/craving matrix scoring.
"""
import math
import random
from typing import Any


# ---------------------------------------------------------------------------
# Mood → dimension weight profiles
# Each mood specifies how much weight to give each score dimension.
# ---------------------------------------------------------------------------

MOOD_PROFILES: dict[str, dict[str, float]] = {
    "happy": {
        "energy": 0.40,
        "darkness": -0.30,
        "complexity": 0.10,
        "mood_happy": 0.50,
        "mood_sad": -0.40,
        "mood_tense": -0.20,
        "mood_funny": 0.30,
        "mood_romantic": 0.20,
    },
    "sad": {
        "energy": -0.10,
        "darkness": 0.20,
        "complexity": 0.20,
        "mood_happy": -0.10,
        "mood_sad": 0.50,
        "mood_tense": 0.10,
        "mood_funny": -0.20,
        "mood_romantic": 0.30,
    },
    "charged": {
        "energy": 0.50,
        "darkness": 0.20,
        "complexity": 0.20,
        "mood_happy": 0.10,
        "mood_sad": -0.20,
        "mood_tense": 0.40,
        "mood_funny": -0.10,
        "mood_romantic": -0.10,
    },
    "chill": {
        "energy": -0.30,
        "darkness": -0.10,
        "complexity": -0.10,
        "mood_happy": 0.30,
        "mood_sad": 0.10,
        "mood_tense": -0.30,
        "mood_funny": 0.20,
        "mood_romantic": 0.20,
    },
    "adventurous": {
        "energy": 0.40,
        "darkness": 0.10,
        "complexity": 0.20,
        "mood_happy": 0.20,
        "mood_sad": -0.10,
        "mood_tense": 0.30,
        "mood_funny": 0.10,
        "mood_romantic": 0.00,
    },
    "romantic": {
        "energy": 0.10,
        "darkness": -0.20,
        "complexity": 0.10,
        "mood_happy": 0.30,
        "mood_sad": 0.20,
        "mood_tense": -0.10,
        "mood_funny": 0.10,
        "mood_romantic": 0.60,
    },
}

# ---------------------------------------------------------------------------
# Context → maximum darkness_score allowed (hard block)
# ---------------------------------------------------------------------------

CONTEXT_MAX_DARKNESS: dict[str, int] = {
    "family": 2,
    "date-night": 6,
    "solo-night": 10,
    "friends": 7,
    "movie-night": 8,
    "background": 4,
}

# ---------------------------------------------------------------------------
# Craving → score dimension boosters (additive on top of mood profile)
# ---------------------------------------------------------------------------

CRAVING_BOOSTERS: dict[str, dict[str, float]] = {
    "laugh": {"mood_funny": 0.40, "energy": 0.10},
    "cry": {"mood_sad": 0.40, "mood_romantic": 0.20},
    "mind-blown": {"complexity": 0.40, "mood_tense": 0.20},
    "thrilled": {"mood_tense": 0.40, "energy": 0.30, "darkness": 0.10},
    "inspired": {"mood_happy": 0.30, "complexity": 0.20, "energy": 0.10},
    "scared": {"darkness": 0.40, "mood_tense": 0.40, "energy": 0.20},
    "comforted": {"mood_happy": 0.30, "mood_sad": 0.20, "energy": -0.20},
    "wowed": {"energy": 0.30, "complexity": 0.20, "mood_happy": 0.10},
}

# Valid enum values (used in routes for validation)
VALID_MOODS = set(MOOD_PROFILES.keys())
VALID_CONTEXTS = set(CONTEXT_MAX_DARKNESS.keys())
VALID_CRAVINGS = set(CRAVING_BOOSTERS.keys())


def score_film(film: Any, mood: str, context: str, craving: str) -> float:
    """
    Score a single film against the given mood/context/craving combination.

    Args:
        film: SQLAlchemy Media instance. Must have score columns populated.
        mood: One of VALID_MOODS
        context: One of VALID_CONTEXTS
        craving: One of VALID_CRAVINGS

    Returns:
        Float score (higher is better). Returns 0.0 if scores not populated.
    """
    mood_scores: dict = film.mood_scores or {}
    context_scores: dict = film.context_scores or {}
    craving_scores: dict = film.craving_scores or {}
    darkness: int = film.darkness_score or 5
    complexity: int = film.complexity_score or 5
    energy: int = film.energy_score or 5

    # Hard block: context darkness constraint
    max_dark = CONTEXT_MAX_DARKNESS.get(context, 10)
    if darkness > max_dark:
        return 0.0

    profile = MOOD_PROFILES.get(mood, {})
    booster = CRAVING_BOOSTERS.get(craving, {})

    total = 0.0

    # Dimension scores from profile
    dim_map = {
        "energy": energy / 10.0,
        "darkness": darkness / 10.0,
        "complexity": complexity / 10.0,
    }
    for dim, weight in profile.items():
        if dim in dim_map:
            total += weight * dim_map[dim]

    # Mood scores (from JSONB column) — keys like "happy", "sad", etc.
    for dim, weight in profile.items():
        if dim.startswith("mood_"):
            mood_key = dim[5:]  # strip "mood_" prefix
            score_val = mood_scores.get(mood_key, 0.5)
            total += weight * float(score_val)

    # Context scores (direct lookup)
    ctx_val = context_scores.get(context, 0.5)
    total += 0.20 * float(ctx_val)

    # Craving boosters
    for dim, boost in booster.items():
        if dim in dim_map:
            total += boost * dim_map[dim]
        elif dim.startswith("mood_"):
            mood_key = dim[5:]
            score_val = mood_scores.get(mood_key, 0.5)
            total += boost * float(score_val)

    # Craving scores (direct lookup)
    crav_val = craving_scores.get(craving, 0.5)
    total += 0.20 * float(crav_val)

    # Normalize: shift into 0–1 range (theoretical range is roughly -2 to +2)
    normalized = (total + 2.0) / 4.0
    return max(0.0, min(1.0, normalized))


def weighted_random_top3(scored: list[tuple[Any, float]]) -> Any:
    """
    Select one film using weighted random sampling from the top-3 candidates.

    Args:
        scored: List of (film, score) tuples, can be any length >= 1.

    Returns:
        Selected film object.
    """
    if not scored:
        raise ValueError("scored list is empty")

    # Sort descending by score
    sorted_scored = sorted(scored, key=lambda x: x[1], reverse=True)

    # Take top 3
    top3 = sorted_scored[:3]

    films = [f for f, _ in top3]
    weights = [max(s, 0.001) for _, s in top3]  # avoid zero weights

    chosen = random.choices(films, weights=weights, k=1)[0]
    return chosen


def match_score_to_percent(final_score: float) -> int:
    """
    Convert a raw score (0–1) to a user-facing match percentage clamped 87–99.

    Args:
        final_score: Float in [0, 1]

    Returns:
        Integer in [87, 99]
    """
    scaled = int(round(87 + (final_score * 12)))
    return max(87, min(99, scaled))
