"""
Unit tests for 60-Second Mode scoring algorithm.

Tests per V1 spec Section 09.
"""
import random
import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

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
):
    """Build a minimal mock film object matching what score_film() expects."""
    film = SimpleNamespace(
        id=id,
        title=title,
        overview=overview,
        genres=genres or [],
        darkness_score=darkness_score,
        complexity_score=complexity_score,
        energy_score=energy_score,
        mood_scores=mood_scores or {
            "happy": 0.6,
            "sad": 0.3,
            "charged": 0.7,
            "chill": 0.5,
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
        """All valid enum combinations should return a non-negative float."""
        film = _make_film()
        for mood in VALID_MOODS:
            for context in VALID_CONTEXTS:
                for craving in VALID_CRAVINGS:
                    s = score_film(film, mood, context, craving)
                    assert isinstance(s, float), f"Expected float for {mood}/{context}/{craving}"
                    assert s >= 0.0, f"Score must be >= 0.0 for {mood}/{context}/{craving}"
                    assert s <= 1.0, f"Score must be <= 1.0 for {mood}/{context}/{craving}"

    def test_family_context_blocks_dark_films(self):
        """Films with darkness_score > 2 must score 0 for family context."""
        dark_film = _make_film(darkness_score=5)
        max_dark = CONTEXT_MAX_DARKNESS["family"]
        assert dark_film.darkness_score > max_dark
        for mood in VALID_MOODS:
            for craving in VALID_CRAVINGS:
                s = score_film(dark_film, mood, "family", craving)
                assert s == 0.0, f"Dark film should score 0 for family context ({mood}/{craving})"

    def test_family_context_allows_clean_films(self):
        """Films with darkness_score <= 2 can have non-zero score for family."""
        clean_film = _make_film(darkness_score=2)
        s = score_film(clean_film, "happy", "family", "laugh")
        assert s > 0.0, "Clean film should score > 0 for family/happy/laugh"

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


# ---------------------------------------------------------------------------
# Tests: weighted_random_top3
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

    def test_100_runs_show_variance(self):
        """Over 100 runs, at least 2 different films should be selected (top-3 weighted random)."""
        films = [_make_film(id=i, title=f"Film {i}") for i in range(5)]
        scored = [(films[0], 0.9), (films[1], 0.85), (films[2], 0.80), (films[3], 0.3), (films[4], 0.1)]

        chosen_ids = set()
        for _ in range(100):
            f = weighted_random_top3(scored)
            chosen_ids.add(f.id)

        assert len(chosen_ids) >= 2, "Expected variance in top-3 weighted random selection over 100 runs"

    def test_only_considers_top3(self):
        """Films ranked 4th or lower (very low score) should not be selected over 100 runs."""
        films = [_make_film(id=i, title=f"Film {i}") for i in range(6)]
        # Films 0-2 have high scores; films 3-5 have near-zero scores
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
