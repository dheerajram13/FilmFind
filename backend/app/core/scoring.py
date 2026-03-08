"""
60-Second Mode scoring algorithm.

Pure functions — no I/O, fully testable.
Implements the V2 spec mood/context/craving matrix scoring.

Key design decisions:
- Weights sum exactly to 1.0: dim_fit=0.25, mood_fit=0.25, ctx_fit=0.20,
  crav_dim_fit=0.15, crav_fit=0.15
- Darkness is a hard constraint only (not a scored dimension)
- Per-component normalization maps each component to [0,1] independently,
  so the final weighted sum is always in [0,1] — no clamping needed
- MOOD_PROFILES keys match the mood_scores JSONB keys written by score_films.py
  (happy, sad, charged, chill, adventurous, romantic)
"""
import random
from typing import Any


# ---------------------------------------------------------------------------
# Mood → dimension weight profiles
#
# Keys for mood_* entries MUST match VALID_MOODS exactly — these are the
# same keys the LLM writes into mood_scores JSONB via score_films.py.
# "darkness" is intentionally absent — it is a hard constraint, not a signal.
# ---------------------------------------------------------------------------

MOOD_PROFILES: dict[str, dict[str, float]] = {
    "happy": {
        "energy": 0.60,
        "complexity": 0.10,
        "mood_happy": 0.70,
        "mood_sad": -0.50,
        "mood_charged": -0.20,
        "mood_chill": 0.20,
        "mood_adventurous": 0.20,
        "mood_romantic": 0.20,
    },
    "sad": {
        "energy": -0.20,
        "complexity": 0.30,
        "mood_happy": -0.10,
        "mood_sad": 0.70,
        "mood_charged": -0.10,
        "mood_chill": 0.10,
        "mood_adventurous": -0.10,
        "mood_romantic": 0.40,
    },
    "charged": {
        "energy": 0.70,
        "complexity": 0.30,
        "mood_happy": 0.10,
        "mood_sad": -0.30,
        "mood_charged": 0.70,
        "mood_chill": -0.40,
        "mood_adventurous": 0.30,
        "mood_romantic": -0.20,
    },
    "chill": {
        "energy": -0.50,
        "complexity": -0.10,
        "mood_happy": 0.30,
        "mood_sad": 0.10,
        "mood_charged": -0.50,
        "mood_chill": 0.70,
        "mood_adventurous": -0.10,
        "mood_romantic": 0.30,
    },
    "adventurous": {
        "energy": 0.60,
        "complexity": 0.30,
        "mood_happy": 0.20,
        "mood_sad": -0.10,
        "mood_charged": 0.30,
        "mood_chill": -0.20,
        "mood_adventurous": 0.70,
        "mood_romantic": 0.00,
    },
    "romantic": {
        "energy": 0.10,
        "complexity": 0.10,
        "mood_happy": 0.30,
        "mood_sad": 0.20,
        "mood_charged": -0.20,
        "mood_chill": 0.20,
        "mood_adventurous": 0.00,
        "mood_romantic": 0.80,
    },
}

# ---------------------------------------------------------------------------
# Context → maximum darkness_score allowed (hard block only)
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
#
# Keys must be either dimension names ("energy", "complexity") or
# mood_* names matching MOOD_PROFILES. "darkness" intentionally absent.
# ---------------------------------------------------------------------------

CRAVING_BOOSTERS: dict[str, dict[str, float]] = {
    "laugh":      {"mood_happy": 0.40, "mood_chill": 0.30, "energy": 0.20},
    "cry":        {"mood_sad": 0.60, "mood_romantic": 0.30},
    "mind-blown": {"complexity": 0.70, "mood_charged": 0.30},
    "thrilled":   {"mood_charged": 0.60, "energy": 0.40},
    "inspired":   {"mood_happy": 0.50, "complexity": 0.30, "energy": 0.20},
    "scared":     {"mood_charged": 0.60, "energy": 0.40},
    "comforted":  {"mood_happy": 0.50, "mood_sad": 0.30},
    "wowed":      {"energy": 0.40, "complexity": 0.40, "mood_happy": 0.20},
}

# Valid enum values (used in routes for validation)
VALID_MOODS = set(MOOD_PROFILES.keys())
VALID_CONTEXTS = set(CONTEXT_MAX_DARKNESS.keys())
VALID_CRAVINGS = set(CRAVING_BOOSTERS.keys())

# Mood score keys that appear in mood_scores JSONB (= VALID_MOODS, no prefix)
_MOOD_SCORE_KEYS: list[str] = list(VALID_MOODS)


def score_film(film: Any, mood: str, context: str, craving: str) -> float:
    """
    Score a single film against the given mood/context/craving combination.

    Args:
        film: SQLAlchemy Media instance. Must have score columns populated.
        mood: One of VALID_MOODS
        context: One of VALID_CONTEXTS
        craving: One of VALID_CRAVINGS

    Returns:
        Float score in [0.0, 1.0]. Returns 0.0 if darkness hard-blocked.

    Formula (weights sum to exactly 1.0):
        dim_fit      × 0.25  — energy + complexity fit for the mood
        mood_fit     × 0.25  — film's mood fingerprint vs user mood
        ctx_fit      × 0.20  — film's context score (direct JSONB lookup)
        crav_dim_fit × 0.15  — craving-driven dimension boost
        crav_fit     × 0.15  — film's explicit craving score (direct JSONB lookup)
    """
    darkness: int = film.darkness_score or 5
    complexity: int = film.complexity_score or 5
    energy: int = film.energy_score or 5
    mood_scores: dict = film.mood_scores or {}
    context_scores: dict = film.context_scores or {}
    craving_scores: dict = film.craving_scores or {}

    # ── 1. Hard block: darkness constraint only ───────────────────────────
    max_dark = CONTEXT_MAX_DARKNESS.get(context, 10)
    if darkness > max_dark:
        return 0.0

    profile = MOOD_PROFILES.get(mood, {})
    booster = CRAVING_BOOSTERS.get(craving, {})

    # Dimension values normalised to [0, 1]
    dim_vals = {
        "energy": energy / 10.0,
        "complexity": complexity / 10.0,
    }

    # ── 2. Dimensional fit [0, 1] ─────────────────────────────────────────
    dim_w = {k: profile.get(k, 0.0) for k in dim_vals}
    dim_abs = sum(abs(w) for w in dim_w.values()) or 1.0
    dim_raw = sum(dim_w[k] * dim_vals[k] for k in dim_vals)
    dim_fit = (dim_raw / dim_abs + 1.0) / 2.0

    # ── 3. Mood score fit [0, 1] ──────────────────────────────────────────
    # Profile keys: "mood_happy", "mood_sad", ... strip "mood_" to look up JSONB
    mood_w = {k: profile.get(f"mood_{k}", 0.0) for k in _MOOD_SCORE_KEYS}
    mood_abs = sum(abs(w) for w in mood_w.values()) or 1.0
    mood_raw = sum(mood_w[k] * float(mood_scores.get(k, 0.5)) for k in _MOOD_SCORE_KEYS)
    mood_fit = (mood_raw / mood_abs + 1.0) / 2.0

    # ── 4. Context fit [0, 1] — direct JSONB lookup ───────────────────────
    ctx_fit = float(context_scores.get(context, 0.5))

    # ── 5. Craving dimensional boost [0, 1] ───────────────────────────────
    crav_dim_w = {k: booster.get(k, 0.0) for k in dim_vals}
    crav_dim_abs = sum(abs(w) for w in crav_dim_w.values()) or 1.0
    crav_dim_raw = sum(crav_dim_w[k] * dim_vals[k] for k in dim_vals)
    crav_dim_fit = (crav_dim_raw / crav_dim_abs + 1.0) / 2.0

    # ── 6. Craving score [0, 1] — direct JSONB lookup ─────────────────────
    crav_fit = float(craving_scores.get(craving, 0.5))

    # ── Weighted sum — always in [0, 1], no clamp needed ──────────────────
    return (
        dim_fit      * 0.25
        + mood_fit   * 0.25
        + ctx_fit    * 0.20
        + crav_dim_fit * 0.15
        + crav_fit   * 0.15
    )


def weighted_random_top3(scored: list[tuple[Any, float]]) -> Any:
    """
    Select one film using weighted random sampling from the top-3 candidates.

    Adds Gaussian noise (σ=0.04) before ranking to provide session-level
    variety — rank-4/5 films can occasionally surface without ever swapping
    a strong match for a weak one.

    Args:
        scored: List of (film, score) tuples, any length >= 1.

    Returns:
        Selected film object.
    """
    if not scored:
        raise ValueError("scored list is empty")

    # Add small noise for variety, then take top 3
    noisy = [(f, max(0.0, s + random.gauss(0, 0.04))) for f, s in scored]
    top3 = sorted(noisy, key=lambda x: x[1], reverse=True)[:3]

    films = [f for f, _ in top3]
    weights = [max(s, 0.001) for _, s in top3]

    return random.choices(films, weights=weights, k=1)[0]


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
