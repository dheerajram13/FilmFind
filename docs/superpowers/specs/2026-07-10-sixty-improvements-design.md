# Sixty-Mode Improvements Design

**Date:** 2026-07-10
**Status:** Draft — awaiting user approval

---

## Background

A full end-to-end audit of the sixty-second mode feature revealed four categories of issues: a broken data pipeline, a misleading score display, a frontend↔backend enum mismatch, and minor code hygiene problems. This spec designs fixes for all four.

---

## Issue Summary

| # | Issue | Severity |
|---|-------|----------|
| 1 | `score_films.py` references `Media.mood_scores`, `Media.narrative_dna`, etc. — columns that live on `MediaEnrichment`, not `Media`. The script crashes on launch with `AttributeError`. No films have scores. | **Blocker** |
| 2 | `SixtyPickResponse` only returns a single `match_score` (87–99%). The frontend "Mood fit / Context fit / Craving fit" bars are fabricated as `(resultMatch, resultMatch-2, resultMatch-5)`. | High |
| 3 | Frontend presents 6 moods (drained, bored, curious + 3 real ones), 6 contexts (solo-day, partner, date + 3 real ones), 6 cravings (pumped, cosy + 4 real ones). Backend has no profiles for the 7 frontend-only keys — they're silently mapped to nearest equivalents. | Medium |
| 4 | `_SIXTY_CACHE_TTL = 86400` duplicated in `sixty.py` and `cache_service.py`. `generate_why_reasons` navigates the object graph defensively with `getattr` chains — works but unclear. Dead buttons in result screen. | Low |

---

## A. Pipeline Fix — score_films.py

### Problem

`score_films.py` queries the `Media` model and references `Media.mood_scores`, `Media.narrative_dna`, `Media.tone_tags`, `Media.is_fully_scored` — all of which are columns on `MediaEnrichment`, not `Media`. The ORM would raise `AttributeError` immediately.

### Solution

Rewrite the query to target `MediaEnrichment`, joined with its concrete movie/show for title and overview context.

**Query logic:**
1. Query `MediaEnrichment` where `mood_scores IS NULL AND narrative_dna IS NOT NULL`, ordered by `Media.popularity DESC` (join via `media_id`).
2. For each enrichment row, access the concrete type via `enrichment.media.movie or enrichment.media.tv_show` to get title, overview, genres for the LLM prompt.
3. Call LLM, parse response, write `mood_scores`, `context_scores`, `craving_scores` back to the `MediaEnrichment` row.
4. Set `enrichment.is_fully_scored = True` on the `MediaEnrichment` object.

**Prompt context** (unchanged fields, now correctly sourced):
- `title`, `overview` — from concrete (Movie/TVShow)
- `narrative_dna`, `tone_tags`, `darkness_score`, `complexity_score`, `energy_score` — from `MediaEnrichment`
- `genres` — from `Media.genres` (relationship)

**Fallback:** if `narrative_dna IS NULL`, score from title + overview + genres alone (same as current fallback path).

### Files affected
- `backend/scripts/ml/score_films.py` — rewrite query and write paths

---

## B. Real Component Scores in API Response

### Problem

The scoring formula has five meaningful sub-scores: `dim_fit`, `mood_fit`, `ctx_fit`, `crav_dim_fit`, `crav_fit`. Currently only the final weighted sum is returned. The frontend renders fake bars from the total match score.

### Solution

**Backend — `score_films_sql` return type:**

Change return type from `list[tuple[Media, float]]` to `list[tuple[Media, float, dict]]` where the dict contains per-component scores. The SQL query already computes each term separately — expose them as named columns.

Concrete: add named sub-expressions to the SELECT clause:
```sql
SELECT
    c.media_id,
    <total_score> AS score,
    <dim_fit_expr>      AS dim_fit,
    <mood_fit_expr>     AS mood_fit,
    <ctx_fit_expr>      AS ctx_fit,
    <crav_dim_fit_expr> AS crav_dim_fit,
    <crav_fit_expr>     AS crav_fit
FROM ...
```

Return as `list[tuple[Media, float, dict[str, float]]]`.

**Backend — `SixtyPickResponse` schema (in `sixty.py`):**

Add a `component_scores` field:
```python
class ComponentScores(BaseModel):
    dim_fit: float       # energy + complexity match [0, 1]
    mood_fit: float      # mood fingerprint match [0, 1]
    ctx_fit: float       # context match [0, 1]
    crav_fit: float      # craving match [0, 1]

class SixtyPickResponse(BaseModel):
    film: MovieResponse
    match_score: int
    component_scores: ComponentScores
    why_reasons: list[str]
    session_id: str
```

`crav_dim_fit` is collapsed into `crav_fit` for the API (it's an implementation detail of the scoring formula, not meaningful to consumers). Frontend displays 4 bars instead of 3 if needed, or collapses the two craving terms server-side: `crav_combined = crav_dim_fit * 0.15 + crav_fit * 0.15`.

**Frontend — result score strip:**

Replace the three fabricated bars with real data from `response.component_scores`. Labels:
- "Mood match" ← `mood_fit * 100`%
- "Context fit" ← `ctx_fit * 100`%
- "Craving fit" ← `crav_fit * 100`% (collapsed craving score)

Remove the fake `Math.min(99, resultMatch)` / `Math.max(70, resultMatch-2)` arithmetic.

**Cache impact:** The cache stores `(film_id, score)` pairs — component scores are not cached. On a cache hit, component scores are recomputed for the selected film after `weighted_random_top3()` picks it. This requires a new function `score_film_detailed(enrichment, mood, context, craving) -> ComponentScores` in `scoring.py` that returns the per-component breakdown without a DB query. It uses the same arithmetic as `score_film()` but returns each term instead of the weighted sum. On a cache miss, the SQL query returns the component columns directly.

### Files affected
- `backend/app/services/sixty_scorer.py` — add per-component columns to SELECT, update return type
- `backend/app/api/routes/sixty.py` — add `ComponentScores` model, extract scores from selected film, include in response
- `frontend/components/home/SixtySecondMode.tsx` — use `component_scores` from response, remove fabricated arithmetic

---

## C. Backend Enum Expansion

### Problem

The frontend shows 7 enum values that don't exist in the backend:
- **Moods:** `drained`, `bored`, `curious`
- **Contexts:** `solo-day`, `partner`, `date`
- **Cravings:** `pumped`, `cosy`

These are silently mapped to nearest-neighbor backend values in the frontend key maps. A user who selects "Drained & tired" gets scored the same as "chill", which is close but not precise.

### Solution

Add the 7 missing values to the backend, then remove the mapping layer from the frontend.

**New `MOOD_PROFILES` entries (`core/scoring.py`):**

| Mood | Intent | Profile |
|------|--------|---------|
| `drained` | Low energy, want low cognitive load | `energy: -0.70, complexity: -0.40, mood_chill: 0.70, mood_happy: 0.30, mood_sad: 0.10, rest 0 or small` |
| `bored` | Need surprise and novelty | `energy: 0.40, complexity: 0.50, mood_adventurous: 0.70, mood_charged: 0.30, mood_chill: -0.40` |
| `curious` | Alert, wants depth and ideas | `complexity: 0.70, energy: 0.20, mood_charged: 0.50, mood_adventurous: 0.30, mood_chill: -0.30` |

**New `CONTEXT_MAX_DARKNESS` entries:**

| Context | Max darkness | Rationale |
|---------|-------------|-----------|
| `solo-day` | 5 | Lazy daytime solo — lighter content appropriate |
| `partner` | 7 | Two people, relaxed constraint |
| `date` | 6 | Same intent as date-night, slightly lighter default |

**New `CRAVING_BOOSTERS` entries:**

| Craving | Booster |
|---------|---------|
| `pumped` | `mood_charged: 0.70, energy: 0.50` (stronger than `thrilled`) |
| `cosy` | `mood_happy: 0.50, mood_chill: 0.40, mood_sad: 0.10` (warmth emphasis) |

**Frontend cleanup:**

Remove `MOOD_KEY_MAP`, `CONTEXT_KEY_MAP`, `CRAVING_KEY_MAP` and the three `toBackend*()` mapper functions from `SixtySecondMode.tsx`. The option `key` values in `MOOD_OPTIONS`, `CONTEXT_OPTIONS`, `CRAVING_OPTIONS` already match the backend enum values once the backend is extended. The API call passes the key directly.

**Validation:** The `@field_validator` in `SixtyPickRequest` reads from `VALID_MOODS`, `VALID_CONTEXTS`, `VALID_CRAVINGS` — these auto-update when the dicts are extended. No validator changes needed.

**Cache implications:** Current total: `6 moods × 6 contexts × 8 cravings = 288` combinations. After expansion: `9 moods × 9 contexts × 10 cravings = 810` combinations. `SixtyRefreshService.refresh()` iterates all combinations — this is fine, it runs admin-side only.

### Files affected
- `backend/app/core/scoring.py` — add 7 new entries to the three dicts
- `frontend/components/home/SixtySecondMode.tsx` — remove key maps and mapper functions, use option keys directly

---

## D. Code Cleanup

### D1. Deduplicate `_SIXTY_CACHE_TTL`

`_SIXTY_CACHE_TTL = 86400` appears in both `sixty.py` and `cache_service.py`. Move it to `cache_service.py` as the single source of truth. Import it in `sixty.py`.

### D2. Clarify `generate_why_reasons` object traversal

The current code navigates: `film` (Movie/TVShow) → `film.media` (Media) → `anchor.enrichment` (MediaEnrichment). This works because SQLAlchemy loads the `media` back-reference when `Media.movie` is selectin-loaded. But the `getattr` defensive chain obscures this. Add a clear comment explaining the traversal, or simplify to direct attribute access with a single guard.

### D3. Dead buttons in result screen

The result screen has three non-functional buttons:
- `+ Add to watchlist` — no onClick
- `Details →` — no onClick
- Share "📷 Story" and "💬 Share" — both call `shareNative()` which does the same thing

**Decision:** These are stub features. Remove them from the DOM rather than leaving dead buttons. If watchlist and detail views are built later, they can be added back with real handlers.

### Files affected
- `backend/app/services/cache_service.py` — export `_SIXTY_CACHE_TTL` (rename to `SIXTY_CACHE_TTL`, public)
- `backend/app/api/routes/sixty.py` — import `SIXTY_CACHE_TTL` from `cache_service`
- `backend/app/services/sixty_why.py` — add comment on traversal
- `frontend/components/home/SixtySecondMode.tsx` — remove dead buttons, deduplicate share handlers

---

## Implementation Order

1. **A** (pipeline fix) — unblocks everything; sixty mode returns 503 until films are scored
2. **C** (enum expansion) — backend-only, no dependencies, can be done in parallel with A
3. **B** (component scores) — backend + frontend change, depends on pipeline being real
4. **D** (cleanup) — independent, can be bundled with any of the above

---

## Out of Scope

- Hardcoded `filmfind.app/pick/{slug}` share URL — routes don't exist yet; remove the copy-link button from the share modal (covered in D3)
- `asyncio.create_task` in `log_sixty_session` — inherent to fire-and-forget pattern; acceptable risk given it only affects analytics
- `enrich_films.py` (Stage 4) — separate pipeline stage, not touched here
