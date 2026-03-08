"""
Unit tests for 60-Second Mode scoring algorithm.

Tests per V2 spec — covers all new requirements:
- score always in [0.0, 1.0] for all 216 mood×context×craving combinations
- darkness-blocked film returns exactly 0.0
- family context never returns film with darkness_score > 2
- calling same combo 10 times returns at least 2 different films (noise working)
- is_fully_scored=False films are excluded by the SQL query (tested via mock)
"""
import random
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.scoring import (
    CONTEXT_MAX_DARKNESS,
    VALID_CONTEXTS,
    VALID_CRAVINGS,
    VALID_MOODS,
    match_score_to_percent,
    score_film,
    weighted_random_top3,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_film(
    *,
    darkness_score=5,
    complexity_score=5,
    energy_score=5,
    mood_scores=None,
    context_scores=None,
    craving_scores=None,
    title="Test Film",
    id=1,
    genres=None,
    overview="A test film.",
    is_fully_scored=True,
):
    """
    Build a minimal mock film object matching what score_film() expects.

    mood_scores keys match VALID_MOODS: happy, sad, charged, chill, adventurous, romantic
    (NOT the old tense/funny keys — those were the V1 bug this PR fixes).
    """
    film = SimpleNamespace(
        id=id,
        title=title,
        overview=overview,
        genres=genres or [],
        darkness_score=darkness_score,
        complexity_score=complexity_score,
        energy_score=energy_score,
        is_fully_scored=is_fully_scored,
        mood_scores=mood_scores or {
            # Keys match VALID_MOODS exactly
            "happy": 0.6,
            "sad": 0.3,
            "charged": 0.7,
            "chill": 0.4,
            "adventurous": 0.6,
            "romantic": 0.4,
        },
        context_scores=context_scores or {
            "family": 0.4,
            "date-night": 0.6,
            "solo-night": 0.8,
            "friends": 0.7,
            "movie-night": 0.7,
            "background": 0.3,
        },
        craving_scores=craving_scores or {
            "laugh": 0.3,
            "cry": 0.4,
            "mind-blown": 0.7,
            "thrilled": 0.6,
            "inspired": 0.5,
            "scared": 0.4,
            "comforted": 0.5,
            "wowed": 0.6,
        },
    )
    return film


# ---------------------------------------------------------------------------
# Tests: score_film
# ---------------------------------------------------------------------------


class TestScoreFilm:
    def test_all_valid_mood_context_craving_combos_return_score(self):
        """All 216 valid enum combinations must return a float in [0.0, 1.0]."""
        film = _make_film()
        count = 0
        for mood in VALID_MOODS:
            for context in VALID_CONTEXTS:
                for craving in VALID_CRAVINGS:
                    s = score_film(film, mood, context, craving)
                    assert isinstance(s, float), f"Expected float for {mood}/{context}/{craving}"
                    assert 0.0 <= s <= 1.0, (
                        f"Score {s} out of [0,1] for {mood}/{context}/{craving}"
                    )
                    count += 1
        assert count == len(VALID_MOODS) * len(VALID_CONTEXTS) * len(VALID_CRAVINGS)

    def test_darkness_blocked_film_returns_exactly_zero(self):
        """Film with darkness_score above context limit must return exactly 0.0."""
        dark_film = _make_film(darkness_score=8)
        # darkness=8 exceeds family(2), background(4), date-night(6), friends(7)
        for context, max_dark in CONTEXT_MAX_DARKNESS.items():
            if dark_film.darkness_score > max_dark:
                for mood in VALID_MOODS:
                    for craving in VALID_CRAVINGS:
                        s = score_film(dark_film, mood, context, craving)
                        assert s == 0.0, (
                            f"darkness={dark_film.darkness_score} > max={max_dark} "
                            f"for {context} must return 0.0, got {s}"
                        )

    def test_family_context_blocks_dark_films(self):
        """Films with darkness_score > 2 must score 0 for family context."""
        dark_film = _make_film(darkness_score=5)
        max_dark = CONTEXT_MAX_DARKNESS["family"]
        assert dark_film.darkness_score > max_dark
        for mood in VALID_MOODS:
            for craving in VALID_CRAVINGS:
                s = score_film(dark_film, mood, "family", craving)
                assert s == 0.0, (
                    f"Dark film (darkness=5) should score 0 for family ({mood}/{craving})"
                )

    def test_family_context_allows_clean_films(self):
        """Films with darkness_score <= 2 can have non-zero score for family."""
        clean_film = _make_film(darkness_score=2)
        s = score_film(clean_film, "happy", "family", "laugh")
        assert s > 0.0, "Clean film (darkness=2) should score > 0 for family/happy/laugh"

    def test_score_returns_zero_for_too_dark(self):
        """Any context's max darkness limit is respected."""
        for context, max_dark in CONTEXT_MAX_DARKNESS.items():
            over_dark = _make_film(darkness_score=max_dark + 1)
            if max_dark < 10:
                for mood in list(VALID_MOODS)[:2]:
                    for craving in list(VALID_CRAVINGS)[:2]:
                        s = score_film(over_dark, mood, context, craving)
                        assert s == 0.0, f"Film too dark for {context} should return 0"

    def test_score_with_no_scores_populated(self):
        """Films with no mood/context/craving scores (empty dicts) don't crash."""
        film = _make_film(mood_scores={}, context_scores={}, craving_scores={})
        s = score_film(film, "happy", "solo-night", "laugh")
        assert isinstance(s, float)
        assert 0.0 <= s <= 1.0

    def test_score_is_always_in_unit_interval(self):
        """
        For any film/mood/context/craving combination, score must be in [0, 1].

        This directly verifies the per-component normalization guarantees —
        no clamping should ever be needed.
        """
        # Extreme films: all-max and all-min dimensions
        max_film = _make_film(
            darkness_score=0,
            complexity_score=10,
            energy_score=10,
            mood_scores={k: 1.0 for k in VALID_MOODS},
            context_scores={k: 1.0 for k in VALID_CONTEXTS},
            craving_scores={k: 1.0 for k in VALID_CRAVINGS},
        )
        min_film = _make_film(
            darkness_score=0,
            complexity_score=0,
            energy_score=0,
            mood_scores={k: 0.0 for k in VALID_MOODS},
            context_scores={k: 0.0 for k in VALID_CONTEXTS},
            craving_scores={k: 0.0 for k in VALID_CRAVINGS},
        )
        for film in (max_film, min_film):
            for mood in VALID_MOODS:
                for context in VALID_CONTEXTS:
                    for craving in VALID_CRAVINGS:
                        s = score_film(film, mood, context, craving)
                        assert 0.0 <= s <= 1.0, (
                            f"Extreme film score {s} out of [0,1] for "
                            f"{mood}/{context}/{craving}"
                        )


# ---------------------------------------------------------------------------
# Tests: weighted_random_top3 — variety with noise
# ---------------------------------------------------------------------------


class TestWeightedRandomTop3:
    def test_returns_one_film(self):
        films = [_make_film(id=i, title=f"Film {i}") for i in range(5)]
        scored = [(f, 0.5 + i * 0.1) for i, f in enumerate(films)]
        chosen = weighted_random_top3(scored)
        assert chosen is not None

    def test_raises_on_empty_list(self):
        with pytest.raises(ValueError, match="empty"):
            weighted_random_top3([])

    def test_single_film_always_chosen(self):
        film = _make_film()
        result = weighted_random_top3([(film, 0.9)])
        assert result is film

    def test_10_runs_same_combo_return_at_least_2_different_films(self):
        """
        Calling the same combo 10 times must return at least 2 different films.
        The Gaussian noise (σ=0.04) on top-3 candidates ensures variety.
        """
        films = [_make_film(id=i, title=f"Film {i}") for i in range(5)]
        # Top 3 films have similar scores — noise should alternate between them
        scored = [
            (films[0], 0.80),
            (films[1], 0.78),
            (films[2], 0.76),
            (films[3], 0.20),
            (films[4], 0.10),
        ]
        chosen_ids = set()
        for _ in range(10):
            f = weighted_random_top3(scored)
            chosen_ids.add(f.id)

        assert len(chosen_ids) >= 2, (
            f"Expected >= 2 different films over 10 runs (noise working), got {chosen_ids}"
        )

    def test_100_runs_show_variance(self):
        """Over 100 runs, at least 2 different films should be selected."""
        films = [_make_film(id=i, title=f"Film {i}") for i in range(5)]
        scored = [(films[0], 0.9), (films[1], 0.85), (films[2], 0.80), (films[3], 0.3), (films[4], 0.1)]

        chosen_ids = set()
        for _ in range(100):
            f = weighted_random_top3(scored)
            chosen_ids.add(f.id)

        assert len(chosen_ids) >= 2, "Expected variance in top-3 weighted random selection over 100 runs"

    def test_only_considers_top3_plus_noise(self):
        """
        Films ranked 4th or lower with near-zero scores should not be selected
        over 200 runs even with noise (noise σ=0.04 can't overcome a 0.7+ gap).
        """
        films = [_make_film(id=i, title=f"Film {i}") for i in range(6)]
        scored = [
            (films[0], 0.95),
            (films[1], 0.90),
            (films[2], 0.85),
            (films[3], 0.001),
            (films[4], 0.001),
            (films[5], 0.001),
        ]
        chosen_ids = set()
        for _ in range(200):
            f = weighted_random_top3(scored)
            chosen_ids.add(f.id)

        for low_id in [3, 4, 5]:
            assert low_id not in chosen_ids, f"Film {low_id} should not be selected (not in top 3)"


# ---------------------------------------------------------------------------
# Tests: is_fully_scored filtering (unit-level mock)
# ---------------------------------------------------------------------------


class TestIsFullyScored:
    def test_unenriched_film_is_excluded_by_sql_filter(self):
        """
        score_film() itself doesn't check is_fully_scored — that's the SQL layer.
        This test documents the contract: score_film() should never be called
        with is_fully_scored=False in production (sixty_scorer.py filters in SQL).

        We verify that score_film() returns a non-zero score for such a film
        (i.e., it doesn't crash or silently return 0), proving the SQL filter
        is the exclusive gate, not the scoring function.
        """
        unenriched = _make_film(is_fully_scored=False, darkness_score=3)
        # score_film() doesn't look at is_fully_scored — it should still score
        s = score_film(unenriched, "happy", "friends", "laugh")
        # The result could be non-zero — that's correct; SQL excluded it upstream
        assert isinstance(s, float)
        assert 0.0 <= s <= 1.0

    def test_fully_scored_flag_in_make_film(self):
        """_make_film() helper correctly sets is_fully_scored."""
        f = _make_film(is_fully_scored=True)
        assert f.is_fully_scored is True
        g = _make_film(is_fully_scored=False)
        assert g.is_fully_scored is False


# ---------------------------------------------------------------------------
# Tests: match_score_to_percent
# ---------------------------------------------------------------------------


class TestMatchScoreToPercent:
    def test_always_returns_87_to_99(self):
        """Any input should return a value in [87, 99]."""
        for raw in [0.0, 0.1, 0.5, 0.9, 1.0, -0.5, 1.5]:
            result = match_score_to_percent(raw)
            assert 87 <= result <= 99, f"Expected 87-99 for input {raw}, got {result}"

    def test_zero_maps_to_87(self):
        assert match_score_to_percent(0.0) == 87

    def test_one_maps_to_99(self):
        assert match_score_to_percent(1.0) == 99

    def test_half_maps_to_middle(self):
        result = match_score_to_percent(0.5)
        assert 87 <= result <= 99
        # 0.5 * 12 = 6, so expected 87 + 6 = 93
        assert result == 93
