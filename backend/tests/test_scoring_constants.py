"""
Property tests for scoring.py constants.
Tests assert on data values directly — no mocks, no network calls.
"""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.scoring import CRAVING_BOOSTERS, MOOD_PROFILES, _COMPONENT_WEIGHTS


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
