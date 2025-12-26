"""
Tests for constraint validator.

This module tests the ConstraintValidator service which validates and
normalizes query constraints.
"""

from datetime import datetime

import pytest
from pydantic import ValidationError

from app.schemas.query import MediaType, QueryConstraints
from app.services.constraint_validator import (
    ConstraintValidationError,
    ConstraintValidator,
    validate_constraints,
)


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def validator():
    """Create constraint validator instance."""
    return ConstraintValidator()


@pytest.fixture
def current_year():
    """Get current year for testing."""
    return datetime.now().year


# =============================================================================
# Basic Validation Tests
# =============================================================================


class TestBasicValidation:
    """Test basic constraint validation."""

    def test_validate_empty_constraints(self, validator):
        """Test validating empty constraints."""
        constraints = QueryConstraints()
        validated = validator.validate(constraints)
        assert validated is not None
        assert isinstance(validated, QueryConstraints)

    def test_validate_valid_constraints(self, validator):
        """Test validating valid constraints."""
        constraints = QueryConstraints(
            languages=["en", "ko"],
            year_min=2000,
            year_max=2020,
            rating_min=7.0,
            runtime_min=90,
            runtime_max=180,
        )
        validated = validator.validate(constraints)
        assert validated is not None


# =============================================================================
# Year Range Validation Tests
# =============================================================================


class TestYearRangeValidation:
    """Test year range constraint validation."""

    def test_year_min_valid(self, validator):
        """Test valid year_min."""
        constraints = QueryConstraints(year_min=2000)
        validated = validator.validate(constraints)
        assert validated.year_min == 2000

    def test_year_min_too_early(self, validator):
        """Test year_min before 1900 (Pydantic validates this)."""
        with pytest.raises(ValidationError):
            QueryConstraints(year_min=1800)

    def test_year_max_valid(self, validator, current_year):
        """Test valid year_max."""
        constraints = QueryConstraints(year_max=current_year)
        validated = validator.validate(constraints)
        assert validated.year_max == current_year

    def test_year_max_too_far_future(self, validator, current_year):
        """Test year_max too far in the future."""
        constraints = QueryConstraints(year_max=current_year + 10)
        with pytest.raises(ConstraintValidationError, match="year_max.*must be <="):
            validator.validate(constraints)

    def test_year_range_inverted(self, validator):
        """Test year_min > year_max (Pydantic validates this)."""
        with pytest.raises(ValidationError):
            QueryConstraints(year_min=2020, year_max=2010)

    def test_year_range_valid(self, validator):
        """Test valid year range."""
        constraints = QueryConstraints(year_min=2010, year_max=2020)
        validated = validator.validate(constraints)
        assert validated.year_min == 2010
        assert validated.year_max == 2020


# =============================================================================
# Runtime Range Validation Tests
# =============================================================================


class TestRuntimeRangeValidation:
    """Test runtime range constraint validation."""

    def test_runtime_min_valid(self, validator):
        """Test valid runtime_min."""
        constraints = QueryConstraints(runtime_min=90)
        validated = validator.validate(constraints)
        assert validated.runtime_min == 90

    def test_runtime_min_negative(self, validator):
        """Test negative runtime_min."""
        constraints = QueryConstraints(runtime_min=-10)
        with pytest.raises(ConstraintValidationError, match="runtime_min.*must be >= 0"):
            validator.validate(constraints)

    def test_runtime_max_valid(self, validator):
        """Test valid runtime_max."""
        constraints = QueryConstraints(runtime_max=180)
        validated = validator.validate(constraints)
        assert validated.runtime_max == 180

    def test_runtime_max_too_high(self, validator):
        """Test unreasonably high runtime_max."""
        constraints = QueryConstraints(runtime_max=700)
        with pytest.raises(
            ConstraintValidationError, match="runtime_max.*is unreasonably high"
        ):
            validator.validate(constraints)

    def test_runtime_range_inverted(self, validator):
        """Test runtime_min > runtime_max."""
        constraints = QueryConstraints(runtime_min=180, runtime_max=90)
        with pytest.raises(
            ConstraintValidationError, match="runtime_min.*must be <= runtime_max"
        ):
            validator.validate(constraints)

    def test_runtime_range_valid(self, validator):
        """Test valid runtime range."""
        constraints = QueryConstraints(runtime_min=90, runtime_max=180)
        validated = validator.validate(constraints)
        assert validated.runtime_min == 90
        assert validated.runtime_max == 180


# =============================================================================
# Rating Validation Tests
# =============================================================================


class TestRatingValidation:
    """Test rating constraint validation."""

    def test_rating_min_valid(self, validator):
        """Test valid rating_min."""
        constraints = QueryConstraints(rating_min=7.5)
        validated = validator.validate(constraints)
        assert validated.rating_min == 7.5

    def test_rating_min_zero(self, validator):
        """Test rating_min = 0."""
        constraints = QueryConstraints(rating_min=0.0)
        validated = validator.validate(constraints)
        assert validated.rating_min == 0.0

    def test_rating_min_max_value(self, validator):
        """Test rating_min = 10."""
        constraints = QueryConstraints(rating_min=10.0)
        validated = validator.validate(constraints)
        assert validated.rating_min == 10.0

    def test_rating_min_negative(self, validator):
        """Test negative rating_min (Pydantic validates this)."""
        with pytest.raises(ValidationError):
            QueryConstraints(rating_min=-1.0)

    def test_rating_min_too_high(self, validator):
        """Test rating_min > 10 (Pydantic validates this)."""
        with pytest.raises(ValidationError):
            QueryConstraints(rating_min=11.0)


# =============================================================================
# Media Type Validation Tests
# =============================================================================


class TestMediaTypeValidation:
    """Test media type constraint validation."""

    def test_media_type_movie(self, validator):
        """Test media_type = MOVIE."""
        constraints = QueryConstraints(media_type=MediaType.MOVIE)
        validated = validator.validate(constraints)
        assert validated.media_type == MediaType.MOVIE

    def test_media_type_tv_show(self, validator):
        """Test media_type = TV_SHOW."""
        constraints = QueryConstraints(media_type=MediaType.TV_SHOW)
        validated = validator.validate(constraints)
        assert validated.media_type == MediaType.TV_SHOW

    def test_media_type_both(self, validator):
        """Test media_type = BOTH."""
        constraints = QueryConstraints(media_type=MediaType.BOTH)
        validated = validator.validate(constraints)
        assert validated.media_type == MediaType.BOTH


# =============================================================================
# Language Validation Tests
# =============================================================================


class TestLanguageValidation:
    """Test language constraint validation."""

    def test_valid_language_codes(self, validator):
        """Test valid 2-character language codes."""
        constraints = QueryConstraints(languages=["en", "ko", "ja"])
        validated = validator.validate(constraints)
        # Should not raise error
        assert validated is not None

    def test_invalid_language_code_too_long(self, validator):
        """Test language code longer than 2 characters (warning only)."""
        constraints = QueryConstraints(languages=["eng"])
        # Should warn but not raise error
        validated = validator.validate(constraints)
        assert validated is not None

    def test_invalid_language_code_too_short(self, validator):
        """Test language code shorter than 2 characters (warning only)."""
        constraints = QueryConstraints(languages=["e"])
        # Should warn but not raise error
        validated = validator.validate(constraints)
        assert validated is not None


# =============================================================================
# Popularity Flags Validation Tests
# =============================================================================


class TestPopularityFlagsValidation:
    """Test popularity preference flags validation."""

    def test_popular_only_true(self, validator):
        """Test popular_only = True."""
        constraints = QueryConstraints(popular_only=True)
        validated = validator.validate(constraints)
        assert validated.popular_only is True

    def test_hidden_gems_true(self, validator):
        """Test hidden_gems = True."""
        constraints = QueryConstraints(hidden_gems=True)
        validated = validator.validate(constraints)
        assert validated.hidden_gems is True

    def test_both_flags_false(self, validator):
        """Test both flags = False."""
        constraints = QueryConstraints(popular_only=False, hidden_gems=False)
        validated = validator.validate(constraints)
        assert validated.popular_only is False
        assert validated.hidden_gems is False

    def test_both_flags_true(self, validator):
        """Test both flags = True (invalid)."""
        constraints = QueryConstraints(popular_only=True, hidden_gems=True)
        with pytest.raises(
            ConstraintValidationError,
            match="Cannot set both popular_only and hidden_gems to True",
        ):
            validator.validate(constraints)


# =============================================================================
# Normalization Tests
# =============================================================================


class TestNormalization:
    """Test constraint normalization."""

    def test_normalize_languages_lowercase(self, validator):
        """Test languages are normalized to lowercase."""
        constraints = QueryConstraints(languages=["EN", "Ko", "JA"])
        validated = validator.validate(constraints)
        assert validated.languages == ["en", "ja", "ko"]  # sorted

    def test_normalize_languages_trim(self, validator):
        """Test languages are trimmed."""
        constraints = QueryConstraints(languages=["  en  ", " ko "])
        validated = validator.validate(constraints)
        assert validated.languages == ["en", "ko"]

    def test_normalize_languages_deduplicate(self, validator):
        """Test duplicate languages are removed."""
        constraints = QueryConstraints(languages=["en", "EN", "en"])
        validated = validator.validate(constraints)
        assert validated.languages == ["en"]

    def test_normalize_languages_sort(self, validator):
        """Test languages are sorted."""
        constraints = QueryConstraints(languages=["ko", "en", "ja"])
        validated = validator.validate(constraints)
        assert validated.languages == ["en", "ja", "ko"]

    def test_normalize_genres_lowercase(self, validator):
        """Test genres are normalized to lowercase."""
        constraints = QueryConstraints(genres=["Action", "DRAMA"])
        validated = validator.validate(constraints)
        assert validated.genres == ["action", "drama"]

    def test_normalize_genres_deduplicate(self, validator):
        """Test duplicate genres are removed."""
        constraints = QueryConstraints(genres=["action", "Action", "ACTION"])
        validated = validator.validate(constraints)
        assert validated.genres == ["action"]

    def test_normalize_exclude_genres(self, validator):
        """Test exclude_genres are normalized."""
        constraints = QueryConstraints(exclude_genres=["Comedy", "HORROR"])
        validated = validator.validate(constraints)
        assert validated.exclude_genres == ["comedy", "horror"]

    def test_normalize_streaming_providers(self, validator):
        """Test streaming providers are normalized."""
        constraints = QueryConstraints(streaming_providers=["Netflix", "HULU", "prime"])
        validated = validator.validate(constraints)
        assert validated.streaming_providers == ["hulu", "netflix", "prime"]


# =============================================================================
# Active Constraints Tests
# =============================================================================


class TestActiveConstraints:
    """Test getting active constraints."""

    def test_get_active_constraints_empty(self, validator):
        """Test getting active constraints from empty constraints."""
        constraints = QueryConstraints()
        active = validator.get_active_constraints(constraints)
        # Only adult_content=False should be active (default)
        assert len(active) == 1
        assert "adult_content=False" in active

    def test_get_active_constraints_multiple(self, validator):
        """Test getting multiple active constraints."""
        constraints = QueryConstraints(
            languages=["en"],
            year_min=2000,
            rating_min=7.0,
            genres=["Action"],
        )
        validated = validator.validate(constraints)  # Normalize first
        active = validator.get_active_constraints(validated)
        assert len(active) == 5  # 4 + adult_content=False
        assert "languages=en" in active
        assert "year_min=2000" in active
        assert "rating_min=7.0" in active
        assert "genres=action" in active  # normalized

    def test_get_active_constraints_media_type_default(self, validator):
        """Test that BOTH media_type is not listed as active."""
        constraints = QueryConstraints(media_type=MediaType.BOTH)
        active = validator.get_active_constraints(constraints)
        assert not any("media_type" in c for c in active)

    def test_get_active_constraints_media_type_movie(self, validator):
        """Test that non-default media_type is listed."""
        constraints = QueryConstraints(media_type=MediaType.MOVIE)
        active = validator.get_active_constraints(constraints)
        assert any("media_type=movie" in c for c in active)


# =============================================================================
# Conflict Detection Tests
# =============================================================================


class TestConflictDetection:
    """Test constraint conflict detection."""

    def test_detect_no_conflicts(self, validator):
        """Test detecting no conflicts in reasonable constraints."""
        constraints = QueryConstraints(
            languages=["en"],
            year_min=2000,
            year_max=2020,
            rating_min=7.0,
        )
        conflicts = validator.detect_conflicts(constraints)
        assert len(conflicts) == 0

    def test_detect_narrow_year_range(self, validator):
        """Test detecting very narrow year range."""
        constraints = QueryConstraints(year_min=2020, year_max=2022)
        conflicts = validator.detect_conflicts(constraints)
        assert len(conflicts) > 0
        assert any("narrow year range" in c.lower() for c in conflicts)

    def test_detect_narrow_runtime_range(self, validator):
        """Test detecting very narrow runtime range."""
        constraints = QueryConstraints(runtime_min=90, runtime_max=100)
        conflicts = validator.detect_conflicts(constraints)
        assert len(conflicts) > 0
        assert any("narrow runtime range" in c.lower() for c in conflicts)

    def test_detect_high_rating_threshold(self, validator):
        """Test detecting high rating threshold."""
        constraints = QueryConstraints(rating_min=9.0)
        conflicts = validator.detect_conflicts(constraints)
        assert len(conflicts) > 0
        assert any("high rating threshold" in c.lower() for c in conflicts)

    def test_detect_many_languages(self, validator):
        """Test detecting many language constraints."""
        constraints = QueryConstraints(languages=["en", "ko", "ja", "fr", "de"])
        conflicts = validator.detect_conflicts(constraints)
        assert len(conflicts) > 0
        assert any("many language constraints" in c.lower() for c in conflicts)

    def test_detect_genre_overlap(self, validator):
        """Test detecting genre in both required and excluded."""
        constraints = QueryConstraints(genres=["action"], exclude_genres=["action"])
        conflicts = validator.detect_conflicts(constraints)
        assert len(conflicts) > 0
        assert any("both required and excluded" in c.lower() for c in conflicts)

    def test_detect_multiple_conflicts(self, validator):
        """Test detecting multiple conflicts."""
        constraints = QueryConstraints(
            year_min=2020,
            year_max=2021,
            rating_min=9.5,
            runtime_min=90,
            runtime_max=100,
        )
        conflicts = validator.detect_conflicts(constraints)
        assert len(conflicts) >= 3  # year, rating, runtime


# =============================================================================
# Convenience Function Tests
# =============================================================================


class TestConvenienceFunction:
    """Test validate_constraints convenience function."""

    def test_validate_constraints_function(self):
        """Test validate_constraints convenience function."""
        constraints = QueryConstraints(languages=["EN", "ko"])
        validated = validate_constraints(constraints)
        assert validated.languages == ["en", "ko"]

    def test_validate_constraints_function_error(self):
        """Test validate_constraints function with invalid constraints (Pydantic validates year range)."""
        with pytest.raises(ValidationError):
            # Pydantic will raise ValidationError before our validator runs
            constraints = QueryConstraints(year_min=2020, year_max=2010)
            validate_constraints(constraints)


# =============================================================================
# Edge Cases
# =============================================================================


class TestEdgeCases:
    """Test edge cases for ConstraintValidator."""

    def test_boundary_year_1900(self, validator):
        """Test year_min = 1900 (boundary)."""
        constraints = QueryConstraints(year_min=1900)
        validated = validator.validate(constraints)
        assert validated.year_min == 1900

    def test_boundary_rating_0(self, validator):
        """Test rating_min = 0 (boundary)."""
        constraints = QueryConstraints(rating_min=0.0)
        validated = validator.validate(constraints)
        assert validated.rating_min == 0.0

    def test_boundary_rating_10(self, validator):
        """Test rating_min = 10 (boundary)."""
        constraints = QueryConstraints(rating_min=10.0)
        validated = validator.validate(constraints)
        assert validated.rating_min == 10.0

    def test_boundary_runtime_0(self, validator):
        """Test runtime_min = 0 (boundary)."""
        constraints = QueryConstraints(runtime_min=0)
        validated = validator.validate(constraints)
        assert validated.runtime_min == 0

    def test_boundary_runtime_600(self, validator):
        """Test runtime_max = 600 (boundary)."""
        constraints = QueryConstraints(runtime_max=600)
        validated = validator.validate(constraints)
        assert validated.runtime_max == 600

    def test_empty_lists(self, validator):
        """Test empty lists in constraints."""
        constraints = QueryConstraints(
            languages=[],
            genres=[],
            exclude_genres=[],
            streaming_providers=[],
        )
        validated = validator.validate(constraints)
        assert validated.languages == []
        assert validated.genres == []

    def test_all_constraints_set(self, validator, current_year):
        """Test all possible constraints set at once."""
        constraints = QueryConstraints(
            media_type=MediaType.MOVIE,
            languages=["en", "ko"],
            genres=["action"],
            exclude_genres=["comedy"],
            year_min=2000,
            year_max=current_year,
            rating_min=7.0,
            runtime_min=90,
            runtime_max=180,
            streaming_providers=["netflix"],
            adult_content=False,
            popular_only=False,
            hidden_gems=False,
        )
        validated = validator.validate(constraints)
        assert validated is not None
