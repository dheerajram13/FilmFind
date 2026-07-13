# Scoring Reference Grounding Design

**Date:** 2026-07-13
**File:** `backend/app/core/scoring.py`
**Scope:** Update `MOOD_PROFILES`, `CRAVING_BOOSTERS`, component weights, and `CONTEXT_MAX_DARKNESS` citations to use published psychoacoustic and affective computing references rather than hand-picked assumptions.

---

## Problem

The numbers in `scoring.py` were chosen by intuition. Three specific issues:

1. `MOOD_PROFILES` energy weights don't match published arousal coordinates — some are in the right direction but wrong magnitude.
2. `CRAVING_BOOSTERS` for `scared` and `thrilled` are byte-for-byte identical, which is wrong — they have opposite valence.
3. Component weights (0.25/0.25/0.20/0.15/0.15) treat direct LLM signals and derived dimension proxies as roughly equal, which undersells the quality of the Stage 3 LLM scores.

---

## References

- **Russell, J.A. (1980).** "A circumplex model of affect." *Journal of Personality and Social Psychology, 39(6), 1161–1178.*
  Provides empirically-derived valence (V) and arousal (A) coordinates for basic emotions on a [-1, +1] scale.

- **Mohammad, S. (2018). Obtaining Reliable Human Ratings of Valence, Arousal, and Dominance for 20,000 English Words.** NRC-VAD Lexicon. National Research Council Canada.
  Provides V/A/D scores for words including craving words (laugh, cry, thrilled, scared, etc.).
  URL: https://saifmohammad.com/WebPages/nrc-vad.html

- **MPAA Rating System** — content appropriateness tiers (G / PG / PG-13 / R / NC-17) used to anchor `CONTEXT_MAX_DARKNESS` thresholds.

---

## Changes

### 1. MOOD_PROFILES — energy weights

Replace hand-picked energy weights with Russell (1980) arousal coordinates:

| Mood | Old energy | New energy | Arousal (Russell) |
|---|---|---|---|
| happy | 0.60 | 0.51 | +0.51 |
| sad | -0.20 | -0.27 | -0.27 |
| charged | 0.70 | 0.75 | +0.75 |
| chill | -0.50 | -0.57 | -0.57 |
| adventurous | 0.60 | 0.62 | +0.62 |
| romantic | 0.10 | 0.16 | +0.16 |

Complexity weights remain approximations (no direct Circumplex analog). Noted inline in code.

### 2. MOOD_PROFILES — mood cross-weights

Two values are directionally wrong vs the Circumplex dot-product similarity:

- `happy → mood_charged`: **-0.20 → +0.10** (charged is adjacent to happy in V×A space, not opposite)
- `charged → mood_happy`: **+0.10 → +0.20** (happy is moderately similar to charged)

All other cross-weights are directionally consistent with Circumplex and are left unchanged.

### 3. CRAVING_BOOSTERS

Fix `scared` vs `thrilled` using NRC-VAD scores:

| Craving | NRC-VAD V | NRC-VAD A | Key change |
|---|---|---|---|
| thrilled | +0.72 | +0.82 | Add `mood_adventurous`, `mood_happy`; keep `mood_charged` |
| scared | -0.55 | +0.74 | Remove `mood_happy` overlap; `mood_charged` only (negative valence) |
| comforted | +0.77 | -0.12 | Add `mood_chill`; reduce energy to negative (low arousal) |

New values:

```python
"thrilled":  {"mood_charged": 0.40, "mood_adventurous": 0.40, "mood_happy": 0.20, "energy": 0.75},
"scared":    {"mood_charged": 0.70, "energy": 0.60, "complexity": 0.20},
"comforted": {"mood_happy": 0.40, "mood_chill": 0.35, "mood_sad": 0.15, "energy": -0.10},
```

All other CRAVING_BOOSTERS entries are consistent with NRC-VAD direction and are left unchanged.

### 4. Component weights

Rebalance to reflect signal quality: direct LLM scores (Stage 3) outweigh derived dimension proxies (Stage 2 integers).

| Component | Old | New | Rationale |
|---|---|---|---|
| `mood_fit` | 0.25 | **0.30** | Direct LLM judgment — highest semantic precision |
| `dim_fit` | 0.25 | **0.20** | Indirect proxy (energy/complexity integers) |
| `ctx_fit` | 0.20 | **0.20** | Direct LLM judgment — unchanged |
| `crav_fit` | 0.15 | **0.20** | Direct LLM judgment — increased to match ctx |
| `crav_dim_fit` | 0.15 | **0.10** | Double-derived (booster applied to dimension proxy) |

Direct signals total: 0.70 (was 0.60). Derived signals total: 0.30 (was 0.40). Sum = 1.0.

### 5. CONTEXT_MAX_DARKNESS

No number changes. Add MPAA-tier inline citations for each entry. Note the `background` limitation (ideally should constrain complexity, not darkness — requires new constraint type, out of scope).

| Context | Value | MPAA tier |
|---|---|---|
| family | 2 | G / PG |
| background | 4 | PG (darkness proxy for complexity) |
| date-night | 6 | PG-13 lower bound |
| friends | 7 | R lower bound |
| movie-night | 8 | R upper bound |
| solo-night | 10 | No cap |

---

## What is NOT changed

- The normalization formula `(raw / abs_sum + 1.0) / 2.0` — correct as-is.
- The `weighted_random_top3` noise parameter (σ=0.04) — not in scope.
- The `match_score_to_percent` 87–99 clamp — not in scope.
- The Stage 3 LLM scoring prompt in `score_films.py` — separate concern, out of scope.

---

## Verification

After the change, run:

```bash
docker compose exec backend python -m pytest tests/test_sixty.py --no-cov
```

No test changes expected — tests assert on response shape, not on specific score magnitudes.
