"""
Tests for query schema validation.

Tests cover:
- Schema validation rules
- Field constraints
- Edge cases
"""

import pytest
from pydantic import ValidationError

from app.schemas.query import (
    EmotionType,
    MediaType,
    QueryConstraints,
    QueryIntent,
    ToneType,
)


class TestQueryConstraintsValidation:
    """Test QueryConstraints validation"""

    def test_valid_year_range(self):
        """Test valid year range"""
        constraints = QueryConstraints(year_min=2000, year_max=2023)
        assert constraints.year_min == 2000
        assert constraints.year_max == 2023

    def test_year_max_equals_year_min(self):
        """Test year_max can equal year_min"""
        constraints = QueryConstraints(year_min=2020, year_max=2020)
        assert constraints.year_min == 2020
        assert constraints.year_max == 2020

    def test_year_max_less_than_year_min_raises(self):
        """Test that year_max < year_min raises ValidationError"""
        with pytest.raises(ValidationError, match="year_max.*must be >= year_min"):
            QueryConstraints(year_min=2020, year_max=2010)

    def test_year_min_below_1900_raises(self):
        """Test that year_min < 1900 raises ValidationError"""
        with pytest.raises(ValidationError):
            QueryConstraints(year_min=1800)

    def test_year_max_below_1900_raises(self):
        """Test that year_max < 1900 raises ValidationError"""
        with pytest.raises(ValidationError):
            QueryConstraints(year_max=1800)

    def test_only_year_min_valid(self):
        """Test providing only year_min is valid"""
        constraints = QueryConstraints(year_min=2000)
        assert constraints.year_min == 2000
        assert constraints.year_max is None

    def test_only_year_max_valid(self):
        """Test providing only year_max is valid"""
        constraints = QueryConstraints(year_max=2023)
        assert constraints.year_min is None
        assert constraints.year_max == 2023

    def test_negative_year_raises(self):
        """Test negative years are rejected"""
        with pytest.raises(ValidationError):
            QueryConstraints(year_min=-100)

    def test_rating_min_validation(self):
        """Test rating_min is between 0-10"""
        # Valid
        constraints = QueryConstraints(rating_min=7.5)
        assert constraints.rating_min == 7.5

        # Invalid - below 0
        with pytest.raises(ValidationError):
            QueryConstraints(rating_min=-1.0)

        # Invalid - above 10
        with pytest.raises(ValidationError):
            QueryConstraints(rating_min=11.0)

    def test_runtime_constraints(self):
        """Test runtime min/max"""
        constraints = QueryConstraints(runtime_min=90, runtime_max=180)
        assert constraints.runtime_min == 90
        assert constraints.runtime_max == 180

    def test_media_type_enum(self):
        """Test MediaType enum values"""
        constraints = QueryConstraints(media_type=MediaType.MOVIE)
        assert constraints.media_type == MediaType.MOVIE

        constraints = QueryConstraints(media_type="tv_show")
        assert constraints.media_type == MediaType.TV_SHOW

    def test_genres_list(self):
        """Test genres as list"""
        constraints = QueryConstraints(genres=["Action", "Thriller"])
        assert "Action" in constraints.genres
        assert "Thriller" in constraints.genres

    def test_exclude_genres_list(self):
        """Test exclude_genres as list"""
        constraints = QueryConstraints(exclude_genres=["Horror", "Romance"])
        assert "Horror" in constraints.exclude_genres
        assert "Romance" in constraints.exclude_genres

    def test_languages_list(self):
        """Test languages as ISO codes"""
        constraints = QueryConstraints(languages=["en", "hi", "ko"])
        assert constraints.languages == ["en", "hi", "ko"]

    def test_streaming_providers(self):
        """Test streaming providers list"""
        constraints = QueryConstraints(streaming_providers=["Netflix", "Prime Video"])
        assert "Netflix" in constraints.streaming_providers

    def test_boolean_flags(self):
        """Test boolean constraint flags"""
        constraints = QueryConstraints(popular_only=True, hidden_gems=False, adult_content=False)
        assert constraints.popular_only is True
        assert constraints.hidden_gems is False
        assert constraints.adult_content is False


class TestQueryIntentValidation:
    """Test QueryIntent validation"""

    def test_valid_tones(self):
        """Test valid tone types"""
        intent = QueryIntent(raw_query="test", tones=[ToneType.DARK, ToneType.SERIOUS])
        assert ToneType.DARK in intent.tones
        assert ToneType.SERIOUS in intent.tones

    def test_valid_emotions(self):
        """Test valid emotion types"""
        intent = QueryIntent(raw_query="test", emotions=[EmotionType.JOY, EmotionType.AWE])
        assert EmotionType.JOY in intent.emotions
        assert EmotionType.AWE in intent.emotions

    def test_themes_as_strings(self):
        """Test themes as list of strings"""
        intent = QueryIntent(raw_query="test", themes=["time travel", "space exploration"])
        assert "time travel" in intent.themes

    def test_reference_titles(self):
        """Test reference titles"""
        intent = QueryIntent(raw_query="test", reference_titles=["Interstellar", "Inception"])
        assert "Interstellar" in intent.reference_titles

    def test_undesired_elements(self):
        """Test undesired themes and tones"""
        intent = QueryIntent(
            raw_query="test",
            undesired_themes=["romance"],
            undesired_tones=[ToneType.LIGHT],
        )
        assert "romance" in intent.undesired_themes
        assert ToneType.LIGHT in intent.undesired_tones

    def test_context_flags(self):
        """Test context boolean flags"""
        intent = QueryIntent(raw_query="test", is_comparison_query=True, is_mood_query=False)
        assert intent.is_comparison_query is True
        assert intent.is_mood_query is False


class TestEdgeCases:
    """Test edge cases and boundary conditions"""

    def test_empty_constraints(self):
        """Test creating constraints with all defaults"""
        constraints = QueryConstraints()
        assert constraints.media_type == MediaType.BOTH
        assert constraints.genres == []
        assert constraints.year_min is None

    def test_empty_intent(self):
        """Test creating intent with minimal data"""
        intent = QueryIntent(raw_query="test")
        assert intent.raw_query == "test"
        assert intent.themes == []
        assert intent.tones == []

    def test_year_boundary_1900(self):
        """Test exact 1900 boundary"""
        constraints = QueryConstraints(year_min=1900, year_max=1900)
        assert constraints.year_min == 1900
        assert constraints.year_max == 1900

    def test_rating_boundary_values(self):
        """Test rating at exact boundaries"""
        # Min boundary
        constraints = QueryConstraints(rating_min=0.0)
        assert constraints.rating_min == 0.0

        # Max boundary
        constraints = QueryConstraints(rating_min=10.0)
        assert constraints.rating_min == 10.0

    def test_future_year(self):
        """Test future years are allowed"""
        constraints = QueryConstraints(year_min=2025, year_max=2030)
        assert constraints.year_min == 2025
        assert constraints.year_max == 2030
