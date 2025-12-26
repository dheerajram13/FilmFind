"""
Tests for filter engine.

This module tests the FilterEngine service which applies hard constraints
to movie candidates.
"""

from datetime import datetime

import pytest

from app.models.movie import Cast, Genre, Keyword, Movie
from app.schemas.query import QueryConstraints
from app.services.filter_engine import FilterEngine, FilterStatistics


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def sample_movies():
    """Create sample movies for testing."""
    # Create genres
    action = Genre(id=1, tmdb_id=28, name="Action")
    drama = Genre(id=2, tmdb_id=18, name="Drama")
    scifi = Genre(id=3, tmdb_id=878, name="Science Fiction")
    comedy = Genre(id=4, tmdb_id=35, name="Comedy")

    # Create keywords
    space = Keyword(id=1, tmdb_id=100, name="space")
    time_travel = Keyword(id=2, tmdb_id=200, name="time travel")

    # Create cast
    actor1 = Cast(id=1, tmdb_id=1, name="Actor One")
    actor2 = Cast(id=2, tmdb_id=2, name="Actor Two")

    movies = [
        # Movie 1: Popular English action/scifi, PG-13, recent
        Movie(
            id=1,
            tmdb_id=550,
            title="Interstellar",
            original_title="Interstellar",
            overview="A space epic",
            release_date=datetime(2014, 11, 7),
            runtime=169,
            adult=False,
            popularity=85.5,
            vote_average=8.6,
            vote_count=25000,
            original_language="en",
            genres=[action, scifi, drama],
            keywords=[space, time_travel],
            cast_members=[actor1],
            streaming_providers={"Netflix": ["US"], "Prime": ["US", "GB"]},
        ),
        # Movie 2: Moderate popularity, older, different language
        Movie(
            id=2,
            tmdb_id=551,
            title="Parasite",
            original_title="기생충",
            overview="Korean thriller",
            release_date=datetime(2019, 5, 30),
            runtime=132,
            adult=False,
            popularity=45.2,
            vote_average=8.5,
            vote_count=15000,
            original_language="ko",
            genres=[drama],
            keywords=[],
            cast_members=[actor2],
            streaming_providers={"Hulu": ["US"]},
        ),
        # Movie 3: Low popularity, very old, short runtime
        Movie(
            id=3,
            tmdb_id=552,
            title="Classic Film",
            original_title="Classic Film",
            overview="Old classic",
            release_date=datetime(1950, 1, 1),
            runtime=90,
            adult=False,
            popularity=12.3,
            vote_average=7.2,
            vote_count=500,
            original_language="en",
            genres=[drama],
            keywords=[],
            cast_members=[],
            streaming_providers={},
        ),
        # Movie 4: Adult content, recent comedy
        Movie(
            id=4,
            tmdb_id=553,
            title="Adult Comedy",
            original_title="Adult Comedy",
            overview="R-rated comedy",
            release_date=datetime(2020, 6, 15),
            runtime=105,
            adult=True,
            popularity=35.7,
            vote_average=6.8,
            vote_count=8000,
            original_language="en",
            genres=[comedy],
            keywords=[],
            cast_members=[],
            streaming_providers={"Netflix": ["US"]},
        ),
        # Movie 5: No release date, no runtime
        Movie(
            id=5,
            tmdb_id=554,
            title="Upcoming Film",
            original_title="Upcoming Film",
            overview="Not released yet",
            release_date=None,
            runtime=None,
            adult=False,
            popularity=25.0,
            vote_average=None,
            vote_count=0,
            original_language="en",
            genres=[scifi],
            keywords=[space],
            cast_members=[],
            streaming_providers={},
        ),
    ]

    return movies


@pytest.fixture
def filter_engine():
    """Create filter engine instance."""
    return FilterEngine()


# =============================================================================
# FilterEngine Tests
# =============================================================================


class TestFilterEngine:
    """Test cases for FilterEngine."""

    def test_no_filters_returns_all(self, filter_engine, sample_movies):
        """Test that empty constraints return all movies."""
        constraints = QueryConstraints()
        filtered = filter_engine.apply_filters(sample_movies, constraints)
        # Adult content is False by default, so movie 4 should be filtered out
        assert len(filtered) == 4

    def test_empty_candidates_returns_empty(self, filter_engine):
        """Test filtering empty list returns empty list."""
        constraints = QueryConstraints(languages=["en"])
        filtered = filter_engine.apply_filters([], constraints)
        assert filtered == []

    def test_filter_adult_content_exclude(self, filter_engine, sample_movies):
        """Test excluding adult content (default)."""
        constraints = QueryConstraints(adult_content=False)
        filtered = filter_engine.apply_filters(sample_movies, constraints)
        assert len(filtered) == 4
        assert all(not m.adult for m in filtered)
        assert sample_movies[3] not in filtered  # Adult Comedy

    def test_filter_adult_content_include(self, filter_engine, sample_movies):
        """Test including adult content."""
        constraints = QueryConstraints(adult_content=True)
        filtered = filter_engine.apply_filters(sample_movies, constraints)
        assert len(filtered) == 5
        assert sample_movies[3] in filtered  # Adult Comedy

    def test_filter_language_single(self, filter_engine, sample_movies):
        """Test filtering by single language."""
        constraints = QueryConstraints(languages=["en"])
        filtered = filter_engine.apply_filters(sample_movies, constraints)
        assert len(filtered) == 3  # Interstellar, Classic Film, Upcoming Film (Adult Comedy filtered)
        assert all(m.original_language == "en" for m in filtered)

    def test_filter_language_multiple(self, filter_engine, sample_movies):
        """Test filtering by multiple languages."""
        constraints = QueryConstraints(languages=["en", "ko"])
        filtered = filter_engine.apply_filters(sample_movies, constraints)
        assert len(filtered) == 4  # All except Adult Comedy
        assert all(m.original_language in ["en", "ko"] for m in filtered)

    def test_filter_language_case_insensitive(self, filter_engine, sample_movies):
        """Test that language filtering is case-insensitive."""
        constraints = QueryConstraints(languages=["EN", "Ko"])
        filtered = filter_engine.apply_filters(sample_movies, constraints)
        assert len(filtered) == 4

    def test_filter_year_min(self, filter_engine, sample_movies):
        """Test filtering by minimum year."""
        constraints = QueryConstraints(year_min=2010)
        filtered = filter_engine.apply_filters(sample_movies, constraints)
        # Interstellar (2014) and Parasite (2019) only (Adult Comedy filtered by default)
        assert len(filtered) == 2
        assert all(m.release_date and m.release_date.year >= 2010 for m in filtered)

    def test_filter_year_max(self, filter_engine, sample_movies):
        """Test filtering by maximum year."""
        constraints = QueryConstraints(year_max=2015)
        filtered = filter_engine.apply_filters(sample_movies, constraints)
        # Interstellar (2014) and Classic Film (1950) only
        assert len(filtered) == 2
        assert all(m.release_date and m.release_date.year <= 2015 for m in filtered)

    def test_filter_year_range(self, filter_engine, sample_movies):
        """Test filtering by year range."""
        constraints = QueryConstraints(year_min=2014, year_max=2019)
        filtered = filter_engine.apply_filters(sample_movies, constraints)
        # Interstellar (2014) and Parasite (2019)
        assert len(filtered) == 2
        years = [m.release_date.year for m in filtered]
        assert all(2014 <= y <= 2019 for y in years)

    def test_filter_year_excludes_no_date(self, filter_engine, sample_movies):
        """Test that year filtering excludes movies without release date."""
        constraints = QueryConstraints(year_min=2000)
        filtered = filter_engine.apply_filters(sample_movies, constraints)
        assert all(m.release_date is not None for m in filtered)

    def test_filter_rating_min(self, filter_engine, sample_movies):
        """Test filtering by minimum rating."""
        constraints = QueryConstraints(rating_min=8.0)
        filtered = filter_engine.apply_filters(sample_movies, constraints)
        # Interstellar (8.6) and Parasite (8.5)
        assert len(filtered) == 2
        assert all(m.vote_average >= 8.0 for m in filtered)

    def test_filter_runtime_min(self, filter_engine, sample_movies):
        """Test filtering by minimum runtime."""
        constraints = QueryConstraints(runtime_min=120)
        filtered = filter_engine.apply_filters(sample_movies, constraints)
        # Interstellar (169) and Parasite (132)
        assert len(filtered) == 2
        assert all(m.runtime >= 120 for m in filtered)

    def test_filter_runtime_max(self, filter_engine, sample_movies):
        """Test filtering by maximum runtime."""
        constraints = QueryConstraints(runtime_max=100)
        filtered = filter_engine.apply_filters(sample_movies, constraints)
        # Classic Film (90)
        assert len(filtered) == 1
        assert filtered[0].title == "Classic Film"

    def test_filter_runtime_range(self, filter_engine, sample_movies):
        """Test filtering by runtime range."""
        constraints = QueryConstraints(runtime_min=100, runtime_max=150)
        filtered = filter_engine.apply_filters(sample_movies, constraints)
        # Parasite (132)
        assert len(filtered) == 1
        assert filtered[0].title == "Parasite"

    def test_filter_runtime_excludes_no_runtime(self, filter_engine, sample_movies):
        """Test that runtime filtering excludes movies without runtime."""
        constraints = QueryConstraints(runtime_min=50)
        filtered = filter_engine.apply_filters(sample_movies, constraints)
        assert all(m.runtime is not None for m in filtered)

    def test_filter_genres_required_single(self, filter_engine, sample_movies):
        """Test filtering by single required genre."""
        constraints = QueryConstraints(genres=["Drama"])
        filtered = filter_engine.apply_filters(sample_movies, constraints)
        # Interstellar, Parasite, Classic Film
        assert len(filtered) == 3
        assert all(any(g.name == "Drama" for g in m.genres) for m in filtered)

    def test_filter_genres_required_multiple(self, filter_engine, sample_movies):
        """Test filtering by multiple required genres (AND logic)."""
        constraints = QueryConstraints(genres=["Action", "Science Fiction"])
        filtered = filter_engine.apply_filters(sample_movies, constraints)
        # Only Interstellar has both
        assert len(filtered) == 1
        assert filtered[0].title == "Interstellar"

    def test_filter_genres_excluded(self, filter_engine, sample_movies):
        """Test filtering by excluded genres."""
        constraints = QueryConstraints(exclude_genres=["Comedy"])
        filtered = filter_engine.apply_filters(sample_movies, constraints)
        # All except Adult Comedy (already filtered by adult content)
        assert len(filtered) == 4
        assert all(not any(g.name == "Comedy" for g in m.genres) for m in filtered)

    def test_filter_genres_case_insensitive(self, filter_engine, sample_movies):
        """Test that genre filtering is case-insensitive."""
        constraints = QueryConstraints(genres=["drama"])
        filtered = filter_engine.apply_filters(sample_movies, constraints)
        assert len(filtered) == 3

    def test_filter_streaming_providers_single(self, filter_engine, sample_movies):
        """Test filtering by single streaming provider."""
        constraints = QueryConstraints(streaming_providers=["Netflix"])
        filtered = filter_engine.apply_filters(sample_movies, constraints)
        # Interstellar only (Adult Comedy filtered by default)
        assert len(filtered) == 1
        assert "Netflix" in filtered[0].streaming_providers

    def test_filter_streaming_providers_multiple(self, filter_engine, sample_movies):
        """Test filtering by multiple streaming providers (OR logic)."""
        constraints = QueryConstraints(streaming_providers=["Netflix", "Hulu"])
        filtered = filter_engine.apply_filters(sample_movies, constraints)
        # Interstellar and Parasite
        assert len(filtered) == 2

    def test_filter_streaming_excludes_no_providers(self, filter_engine, sample_movies):
        """Test that streaming filter excludes movies without provider data."""
        constraints = QueryConstraints(streaming_providers=["Netflix"])
        filtered = filter_engine.apply_filters(sample_movies, constraints)
        assert all(m.streaming_providers for m in filtered)

    def test_filter_popular_only(self, filter_engine, sample_movies):
        """Test filtering for popular movies only."""
        constraints = QueryConstraints(popular_only=True)
        filtered = filter_engine.apply_filters(sample_movies, constraints)
        # Above median popularity
        assert len(filtered) > 0
        popularities = [m.popularity for m in filtered]
        median = sorted([m.popularity for m in sample_movies if m.popularity])[2]
        assert all(p >= median for p in popularities)

    def test_filter_hidden_gems(self, filter_engine, sample_movies):
        """Test filtering for hidden gems (low popularity)."""
        constraints = QueryConstraints(hidden_gems=True)
        filtered = filter_engine.apply_filters(sample_movies, constraints)
        # Below median popularity
        assert len(filtered) > 0
        popularities = [m.popularity for m in filtered]
        median = sorted([m.popularity for m in sample_movies if m.popularity])[2]
        assert all(p < median for p in popularities)

    def test_filter_combined_constraints(self, filter_engine, sample_movies):
        """Test applying multiple constraints together."""
        constraints = QueryConstraints(
            languages=["en"],
            year_min=2010,
            rating_min=8.0,
            runtime_min=160,
            genres=["Science Fiction"],
        )
        filtered = filter_engine.apply_filters(sample_movies, constraints)
        # Only Interstellar matches all constraints
        assert len(filtered) == 1
        assert filtered[0].title == "Interstellar"

    def test_filter_no_results(self, filter_engine, sample_movies):
        """Test that overly restrictive constraints return empty list."""
        constraints = QueryConstraints(
            languages=["ja"],  # No Japanese movies
            rating_min=9.5,  # Very high rating
        )
        filtered = filter_engine.apply_filters(sample_movies, constraints)
        assert len(filtered) == 0


# =============================================================================
# FilterStatistics Tests
# =============================================================================


class TestFilterStatistics:
    """Test cases for FilterStatistics."""

    def test_record_statistics(self):
        """Test recording filter statistics."""
        stats = FilterStatistics()
        stats.record("language", 100, 80)
        stats.record("year", 80, 50)

        assert stats.filter_counts["language"] == (100, 80)
        assert stats.filter_counts["year"] == (80, 50)

    def test_get_selectivity(self):
        """Test calculating filter selectivity."""
        stats = FilterStatistics()
        stats.record("language", 100, 80)  # 20% removed

        selectivity = stats.get_selectivity("language")
        assert selectivity == 20.0

    def test_get_selectivity_zero_before(self):
        """Test selectivity calculation with zero input."""
        stats = FilterStatistics()
        stats.record("empty", 0, 0)

        selectivity = stats.get_selectivity("empty")
        assert selectivity == 0.0

    def test_get_selectivity_unknown_filter(self):
        """Test selectivity for unknown filter."""
        stats = FilterStatistics()
        selectivity = stats.get_selectivity("unknown")
        assert selectivity is None

    def test_get_summary(self):
        """Test getting summary of all statistics."""
        stats = FilterStatistics()
        stats.record("language", 100, 80)
        stats.record("year", 80, 50)

        summary = stats.get_summary()
        assert "language" in summary
        assert "year" in summary
        assert summary["language"]["before"] == 100
        assert summary["language"]["after"] == 80
        assert summary["language"]["removed"] == 20
        assert summary["language"]["selectivity"] == 20.0

    def test_repr(self):
        """Test string representation."""
        stats = FilterStatistics()
        stats.record("language", 100, 80)
        stats.record("year", 80, 50)

        repr_str = repr(stats)
        assert "Filter Statistics:" in repr_str
        assert "language" in repr_str
        assert "year" in repr_str


# =============================================================================
# Edge Cases
# =============================================================================


class TestFilterEngineEdgeCases:
    """Test edge cases for FilterEngine."""

    def test_movie_missing_fields(self, filter_engine):
        """Test filtering movies with missing fields."""
        movie = Movie(
            id=1,
            tmdb_id=1,
            title="Incomplete Movie",
            original_title="Incomplete Movie",
            adult=False,
            genres=[],
            keywords=[],
            cast_members=[],
        )

        # Should not crash
        constraints = QueryConstraints(
            languages=["en"],
            year_min=2000,
            rating_min=7.0,
            runtime_min=90,
        )
        filtered = filter_engine.apply_filters([movie], constraints)
        # Movie filtered out due to missing fields
        assert len(filtered) == 0

    def test_all_movies_filtered_out(self, filter_engine, sample_movies):
        """Test when all movies are filtered out."""
        constraints = QueryConstraints(
            languages=["zz"],  # Non-existent language
        )
        filtered = filter_engine.apply_filters(sample_movies, constraints)
        assert len(filtered) == 0

    def test_filter_preserves_order(self, filter_engine, sample_movies):
        """Test that filtering preserves original order."""
        constraints = QueryConstraints(languages=["en"])
        filtered = filter_engine.apply_filters(sample_movies, constraints)

        # Get IDs of English movies in original order
        expected_ids = [m.id for m in sample_movies if m.original_language == "en" and not m.adult]
        actual_ids = [m.id for m in filtered]

        assert expected_ids == actual_ids
