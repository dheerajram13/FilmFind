"""
60-Second Mode scoring algorithm.

Pure functions — no I/O, fully testable.
Implements the V2 spec mood/context/craving matrix scoring.

Key design decisions:
- Weights sum exactly to 1.0 — see _COMPONENT_WEIGHTS below
- Direct LLM signals (mood_fit, ctx_fit, crav_fit) total 0.70;
  derived dimension proxies (dim_fit, crav_dim_fit) total 0.30
- Darkness is a hard constraint only (not a scored dimension)
- Per-component normalization maps each component to [0,1] independently,
  so the final weighted sum is always in [0,1] — no clamping needed
- MOOD_PROFILES keys match the mood_scores JSONB keys written by score_films.py
  (happy, sad, charged, chill, adventurous, romantic)

References:
- Russell, J.A. (1980). A circumplex model of affect.
  Journal of Personality and Social Psychology, 39(6), 1161–1178.
  → Source for energy weights (= arousal coordinates) in MOOD_PROFILES.
- Mohammad, S. (2018). NRC Valence, Arousal, and Dominance Lexicon.
  National Research Council Canada. https://saifmohammad.com/WebPages/nrc-vad.html
  → Source for CRAVING_BOOSTERS valence/arousal values.
- MPAA Rating System (G / PG / PG-13 / R / NC-17)
  → Source for CONTEXT_MAX_DARKNESS thresholds.
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
    # Energy weights = Russell (1980) Circumplex arousal coordinates.
    # Complexity weights are approximations (no direct Circumplex analog).
    # Mood cross-weights derived from V×A dot-product similarity between moods.
    "happy": {
        "energy": 0.51,        # Circumplex arousal +0.51
        "complexity": 0.10,    # approx — simple emotional state
        "mood_happy": 0.70,
        "mood_sad": -0.50,
        "mood_charged": 0.10,  # adjacent on Circumplex (was -0.20, wrong sign)
        "mood_chill": 0.20,
        "mood_adventurous": 0.20,
        "mood_romantic": 0.20,
    },
    "sad": {
        "energy": -0.27,       # Circumplex arousal -0.27
        "complexity": 0.30,    # approx — emotional processing
        "mood_happy": -0.10,
        "mood_sad": 0.70,
        "mood_charged": -0.10,
        "mood_chill": 0.10,
        "mood_adventurous": -0.10,
        "mood_romantic": 0.40,
    },
    "charged": {
        "energy": 0.75,        # Circumplex arousal +0.75
        "complexity": 0.30,    # approx — cognitive engagement
        "mood_happy": 0.20,    # moderately similar to charged on Circumplex (was 0.10)
        "mood_sad": -0.30,
        "mood_charged": 0.70,
        "mood_chill": -0.40,
        "mood_adventurous": 0.30,
        "mood_romantic": -0.20,
    },
    "chill": {
        "energy": -0.57,       # Circumplex arousal -0.57
        "complexity": -0.10,   # approx — low cognitive demand
        "mood_happy": 0.30,
        "mood_sad": 0.10,
        "mood_charged": -0.50,
        "mood_chill": 0.70,
        "mood_adventurous": -0.10,
        "mood_romantic": 0.30,
    },
    "adventurous": {
        "energy": 0.62,        # Circumplex arousal +0.62
        "complexity": 0.30,    # approx — cognitive engagement
        "mood_happy": 0.20,
        "mood_sad": -0.10,
        "mood_charged": 0.30,
        "mood_chill": -0.20,
        "mood_adventurous": 0.70,
        "mood_romantic": 0.00,
    },
    "romantic": {
        "energy": 0.16,        # Circumplex arousal +0.16
        "complexity": 0.10,    # approx — emotionally focused
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
    "family":      2,   # G/PG equivalent (MPAA)
    "background":  4,   # PG — darkness proxy; ideally complexity-capped (future work)
    "date-night":  6,   # PG-13 lower bound (MPAA)
    "friends":     7,   # R lower bound (MPAA)
    "movie-night": 8,   # R upper bound (MPAA)
    "solo-night":  10,  # no cap
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
    # NRC-VAD: thrilled V=+0.72, A=+0.82 — high arousal, positive valence
    "thrilled":   {"mood_charged": 0.40, "mood_adventurous": 0.40, "mood_happy": 0.20, "energy": 0.75},
    "inspired":   {"mood_happy": 0.50, "complexity": 0.30, "energy": 0.20},
    # NRC-VAD: scared V=-0.55, A=+0.74 — high arousal, negative valence (distinct from thrilled)
    "scared":     {"mood_charged": 0.70, "energy": 0.60, "complexity": 0.20},
    # NRC-VAD: comforted V=+0.77, A=-0.12 — positive valence, low arousal
    "comforted":  {"mood_happy": 0.40, "mood_chill": 0.35, "mood_sad": 0.15, "energy": -0.10},
    "wowed":      {"energy": 0.40, "complexity": 0.40, "mood_happy": 0.20},
}

# Valid enum values (used in routes for validation)
VALID_MOODS = set(MOOD_PROFILES.keys())
VALID_CONTEXTS = set(CONTEXT_MAX_DARKNESS.keys())
VALID_CRAVINGS = set(CRAVING_BOOSTERS.keys())

# Mood score keys that appear in mood_scores JSONB (= VALID_MOODS, no prefix)
_MOOD_SCORE_KEYS: list[str] = list(VALID_MOODS)


# ---------------------------------------------------------------------------
# Component weights for score_film() — must sum to 1.0
#
# Direct LLM signals (Stage 3 scores): mood_fit + ctx_fit + crav_fit = 0.70
# Derived dimension proxies (Stage 2 integers): dim_fit + crav_dim_fit = 0.30
# ---------------------------------------------------------------------------

_COMPONENT_WEIGHTS: dict[str, float] = {
    "mood_fit":     0.30,  # direct LLM judgment — highest semantic precision
    "dim_fit":      0.20,  # indirect proxy (energy/complexity integers from Stage 2)
    "ctx_fit":      0.20,  # direct LLM judgment
    "crav_fit":     0.20,  # direct LLM judgment
    "crav_dim_fit": 0.10,  # double-derived (booster × dimension proxy)
}


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

    Formula (weights sum to exactly 1.0 — see _COMPONENT_WEIGHTS):
        mood_fit     × 0.30  — film's mood fingerprint vs user mood (direct LLM)
        dim_fit      × 0.20  — energy + complexity fit for the mood (derived proxy)
        ctx_fit      × 0.20  — film's context score (direct JSONB lookup)
        crav_fit     × 0.20  — film's explicit craving score (direct JSONB lookup)
        crav_dim_fit × 0.10  — craving-driven dimension boost (double-derived)
    """
    darkness: int = film.darkness_score if film.darkness_score is not None else 5
    complexity: int = film.complexity_score if film.complexity_score is not None else 5
    energy: int = film.energy_score if film.energy_score is not None else 5
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
        dim_fit        * _COMPONENT_WEIGHTS["dim_fit"]
        + mood_fit     * _COMPONENT_WEIGHTS["mood_fit"]
        + ctx_fit      * _COMPONENT_WEIGHTS["ctx_fit"]
        + crav_dim_fit * _COMPONENT_WEIGHTS["crav_dim_fit"]
        + crav_fit     * _COMPONENT_WEIGHTS["crav_fit"]
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
