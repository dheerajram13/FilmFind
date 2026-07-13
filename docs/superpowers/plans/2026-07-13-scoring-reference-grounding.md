# Scoring Reference Grounding Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace hand-picked numbers in `scoring.py` with values grounded in Russell (1980) Circumplex and NRC-VAD lexicon, add testable component weights, and add MPAA citations to darkness thresholds.

**Architecture:** Single-file change to `backend/app/core/scoring.py`. A new test file `backend/tests/test_scoring_constants.py` tests the data properties directly (no mocks, no network). All three tasks extend the same test file.

**Tech Stack:** Python, pytest. No new dependencies.

## Global Constraints

- Run all commands inside Docker: `docker compose exec backend <cmd>`
- Test runner: `docker compose exec backend python -m pytest tests/test_scoring_constants.py --no-cov -v`
- Full suite check: `docker compose exec backend python -m pytest tests/test_sixty.py --no-cov`
- Do not change `weighted_random_top3`, `match_score_to_percent`, or the normalization formula `(raw / abs_sum + 1.0) / 2.0`
- Do not touch `score_films.py` or any prompt files

---

## File Map

| Action | Path | Responsibility |
|---|---|---|
| Modify | `backend/app/core/scoring.py` | Update profiles, boosters, weights, add citations |
| Create | `backend/tests/test_scoring_constants.py` | Property tests for all changed constants |

---

### Task 1: MOOD_PROFILES — energy weights and cross-weight fixes

**Files:**
- Create: `backend/tests/test_scoring_constants.py`
- Modify: `backend/app/core/scoring.py` (lines 28–89, `MOOD_PROFILES` dict)

**Interfaces:**
- Produces: `MOOD_PROFILES` with updated `energy` values and fixed `mood_charged`/`mood_happy` cross-weights

- [ ] **Step 1: Write the failing tests**

Create `backend/tests/test_scoring_constants.py`:

```python
"""
Property tests for scoring.py constants.
Tests assert on data values directly — no mocks, no network calls.
"""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.scoring import CRAVING_BOOSTERS, MOOD_PROFILES


class TestMoodProfilesEnergyWeights:
    """Energy weights must match Russell (1980) Circumplex arousal coordinates."""

    def test_happy_energy(self):
        assert MOOD_PROFILES["happy"]["energy"] == pytest.approx(0.51)

    def test_sad_energy(self):
        assert MOOD_PROFILES["sad"]["energy"] == pytest.approx(-0.27)

    def test_charged_energy(self):
        assert MOOD_PROFILES["charged"]["energy"] == pytest.approx(0.75)

    def test_chill_energy(self):
        assert MOOD_PROFILES["chill"]["energy"] == pytest.approx(-0.57)

    def test_adventurous_energy(self):
        assert MOOD_PROFILES["adventurous"]["energy"] == pytest.approx(0.62)

    def test_romantic_energy(self):
        assert MOOD_PROFILES["romantic"]["energy"] == pytest.approx(0.16)


class TestMoodProfilesCrossWeights:
    def test_happy_mood_charged_is_positive(self):
        # charged is adjacent to happy in V×A space — dot product is positive
        assert MOOD_PROFILES["happy"]["mood_charged"] > 0

    def test_charged_mood_happy_is_positive(self):
        # happy is moderately similar to charged on Circumplex
        assert MOOD_PROFILES["charged"]["mood_happy"] > 0
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
docker compose exec backend python -m pytest tests/test_scoring_constants.py --no-cov -v
```

Expected: 8 FAILED (current `energy` values and `mood_charged`/`mood_happy` cross-weights don't match)

- [ ] **Step 3: Update MOOD_PROFILES in scoring.py**

Replace the entire `MOOD_PROFILES` dict (lines 28–89) with:

```python
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
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
docker compose exec backend python -m pytest tests/test_scoring_constants.py --no-cov -v
```

Expected: 8 PASSED

- [ ] **Step 5: Run integration suite to verify no regressions**

```bash
docker compose exec backend python -m pytest tests/test_sixty.py --no-cov
```

Expected: all PASSED (tests assert on response shape, not score magnitudes)

- [ ] **Step 6: Commit**

```bash
git add backend/tests/test_scoring_constants.py backend/app/core/scoring.py
git commit -m "fix: ground MOOD_PROFILES energy weights in Russell (1980) Circumplex arousal coordinates"
```

---

### Task 2: CRAVING_BOOSTERS — fix scared, thrilled, comforted

**Files:**
- Modify: `backend/tests/test_scoring_constants.py` (extend with new test class)
- Modify: `backend/app/core/scoring.py` (lines 111–120, `CRAVING_BOOSTERS` dict)

**Interfaces:**
- Consumes: `CRAVING_BOOSTERS` from Task 1's `scoring.py`
- Produces: `CRAVING_BOOSTERS` with differentiated `scared`/`thrilled` and low-arousal `comforted`

- [ ] **Step 1: Add failing tests to test_scoring_constants.py**

Append to `backend/tests/test_scoring_constants.py` (after the existing classes):

```python
class TestCravingBoosters:
    def test_scared_and_thrilled_are_not_identical(self):
        # NRC-VAD: thrilled V=+0.72, scared V=-0.55 — opposite valence
        assert CRAVING_BOOSTERS["scared"] != CRAVING_BOOSTERS["thrilled"]

    def test_scared_does_not_boost_happy(self):
        # NRC-VAD: scared has negative valence (-0.55), should not boost happy
        assert "mood_happy" not in CRAVING_BOOSTERS["scared"]

    def test_thrilled_boosts_adventurous(self):
        # NRC-VAD: thrilled has positive valence (+0.72) and high arousal (+0.82)
        assert CRAVING_BOOSTERS["thrilled"].get("mood_adventurous", 0) > 0

    def test_thrilled_boosts_happy(self):
        assert CRAVING_BOOSTERS["thrilled"].get("mood_happy", 0) > 0

    def test_comforted_has_chill_boost(self):
        # NRC-VAD: comforted has low arousal (-0.12) — maps to chill
        assert CRAVING_BOOSTERS["comforted"].get("mood_chill", 0) > 0

    def test_comforted_has_low_or_negative_energy(self):
        # NRC-VAD: comforted arousal -0.12 — energy weight must be negative
        assert CRAVING_BOOSTERS["comforted"].get("energy", 0) < 0
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
docker compose exec backend python -m pytest tests/test_scoring_constants.py::TestCravingBoosters --no-cov -v
```

Expected: 6 FAILED (scared == thrilled currently; comforted has no chill or negative energy)

- [ ] **Step 3: Update CRAVING_BOOSTERS in scoring.py**

Replace only the `thrilled`, `scared`, and `comforted` entries in `CRAVING_BOOSTERS` (leave all others unchanged):

```python
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
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
docker compose exec backend python -m pytest tests/test_scoring_constants.py --no-cov -v
```

Expected: all 14 PASSED

- [ ] **Step 5: Run integration suite**

```bash
docker compose exec backend python -m pytest tests/test_sixty.py --no-cov
```

Expected: all PASSED

- [ ] **Step 6: Commit**

```bash
git add backend/tests/test_scoring_constants.py backend/app/core/scoring.py
git commit -m "fix: differentiate scared/thrilled boosters and add chill to comforted using NRC-VAD scores"
```

---

### Task 3: Component weights + CONTEXT_MAX_DARKNESS citations + module references

**Files:**
- Modify: `backend/tests/test_scoring_constants.py` (extend with weight tests)
- Modify: `backend/app/core/scoring.py` (module docstring, `CONTEXT_MAX_DARKNESS`, extract `_COMPONENT_WEIGHTS`, update `score_film()` return)

**Interfaces:**
- Consumes: `scoring.py` from Task 2
- Produces: `_COMPONENT_WEIGHTS` (exported), updated `score_film()` return, MPAA citations on `CONTEXT_MAX_DARKNESS`

- [ ] **Step 1: Add failing tests to test_scoring_constants.py**

Replace the existing `from app.core.scoring import` line at the top of `backend/tests/test_scoring_constants.py` with:

```python
from app.core.scoring import CRAVING_BOOSTERS, MOOD_PROFILES, _COMPONENT_WEIGHTS
```

Then append to `backend/tests/test_scoring_constants.py`:

```python
class TestComponentWeights:
    def test_weights_sum_to_one(self):
        assert sum(_COMPONENT_WEIGHTS.values()) == pytest.approx(1.0)

    def test_mood_fit_exceeds_dim_fit(self):
        # Direct LLM signal should outweigh dimension proxy
        assert _COMPONENT_WEIGHTS["mood_fit"] > _COMPONENT_WEIGHTS["dim_fit"]

    def test_direct_signals_exceed_derived_signals(self):
        # mood_fit + ctx_fit + crav_fit (direct LLM) > dim_fit + crav_dim_fit (derived)
        direct = (
            _COMPONENT_WEIGHTS["mood_fit"]
            + _COMPONENT_WEIGHTS["ctx_fit"]
            + _COMPONENT_WEIGHTS["crav_fit"]
        )
        derived = _COMPONENT_WEIGHTS["dim_fit"] + _COMPONENT_WEIGHTS["crav_dim_fit"]
        assert direct > derived
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
docker compose exec backend python -m pytest tests/test_scoring_constants.py::TestComponentWeights --no-cov -v
```

Expected: 3 FAILED (`_COMPONENT_WEIGHTS` does not exist yet)

- [ ] **Step 3: Update scoring.py — module docstring, _COMPONENT_WEIGHTS, CONTEXT_MAX_DARKNESS, score_film return**

**3a.** Replace the module docstring (lines 1–15) with:

```python
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
```

**3b.** Add `_COMPONENT_WEIGHTS` constant immediately before the `score_film` function definition:

```python
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
```

**3c.** Replace `CONTEXT_MAX_DARKNESS` with MPAA-cited version:

```python
CONTEXT_MAX_DARKNESS: dict[str, int] = {
    "family":      2,   # G/PG equivalent (MPAA)
    "background":  4,   # PG — darkness proxy; ideally complexity-capped (future work)
    "date-night":  6,   # PG-13 lower bound (MPAA)
    "friends":     7,   # R lower bound (MPAA)
    "movie-night": 8,   # R upper bound (MPAA)
    "solo-night":  10,  # no cap
}
```

**3d.** Replace the final `return` statement in `score_film()` with:

```python
    # ── Weighted sum — always in [0, 1], no clamp needed ──────────────────
    return (
        dim_fit        * _COMPONENT_WEIGHTS["dim_fit"]
        + mood_fit     * _COMPONENT_WEIGHTS["mood_fit"]
        + ctx_fit      * _COMPONENT_WEIGHTS["ctx_fit"]
        + crav_dim_fit * _COMPONENT_WEIGHTS["crav_dim_fit"]
        + crav_fit     * _COMPONENT_WEIGHTS["crav_fit"]
    )
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
docker compose exec backend python -m pytest tests/test_scoring_constants.py --no-cov -v
```

Expected: all 17 PASSED

- [ ] **Step 5: Run full integration suite**

```bash
docker compose exec backend python -m pytest tests/test_sixty.py --no-cov
```

Expected: all PASSED

- [ ] **Step 6: Commit**

```bash
git add backend/tests/test_scoring_constants.py backend/app/core/scoring.py
git commit -m "refactor: extract _COMPONENT_WEIGHTS, rebalance to favor direct LLM signals, add MPAA citations"
```
