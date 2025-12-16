"""
Tests for Semantic Retrieval Engine.

Tests the complete retrieval pipeline including vector search,
metadata enrichment, and constraint filtering.
"""

from datetime import date
from unittest.mock import MagicMock, Mock, patch

import numpy as np
import pytest

from app.models.movie import Cast, Genre, Keyword, Movie, MovieCast
from app.schemas.query import (
    ParsedQuery,
    QueryConstraints,
    QueryIntent,
    ToneType,
)
from app.services.retrieval_engine import (
    RetrievalConfig,
    SemanticRetrievalEngine,
)


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def mock_embedding_service():
    """Mock embedding service."""
    service = Mock()
    service.generate_embedding.return_value = np.random.randn(768)
    return service


@pytest.fixture
def mock_vector_search():
    """Mock vector search service."""
    service = Mock()
    # Return (movie_id, similarity_score) tuples
    service.search.return_value = [
        (1, 0.95),
        (2, 0.92),
        (3, 0.88),
        (4, 0.85),
        (5, 0.80),
    ]
    return service


@pytest.fixture
def mock_movie_repo():
    """Mock movie repository."""
    repo = Mock()

    # Create mock movies with relationships
    def create_mock_movie(movie_id, tmdb_id, title):
        movie = Mock(spec=Movie)
        movie.id = movie_id
        movie.tmdb_id = tmdb_id
        movie.title = title
        movie.original_title = title
        movie.plot_summary = f"Plot for {title}"
        movie.tagline = f"Tagline for {title}"
        movie.release_date = date(2020, 1, 1)
        movie.year = 2020
        movie.runtime = 120
        movie.vote_average = 8.0
        movie.vote_count = 1000
        movie.popularity = 100.0
        movie.original_language = "en"
        movie.adult = False
        movie.poster_url = f"https://example.com/poster/{movie_id}.jpg"
        movie.backdrop_url = f"https://example.com/backdrop/{movie_id}.jpg"

        # Mock genres
        genre = Mock(spec=Genre)
        genre.name = "Sci-Fi"
        movie.genres = [genre]

        # Mock keywords
        keyword = Mock(spec=Keyword)
        keyword.name = "space"
        movie.keywords = [keyword]

        # Mock cast
        cast_member = Mock(spec=Cast)
        cast_member.name = "Actor Name"

        movie_cast = Mock(spec=MovieCast)
        movie_cast.cast_member = cast_member
        movie_cast.character_name = "Character"
        movie_cast.order_position = 0

        movie.cast_members = [movie_cast]

        return movie

    # Mock find_by_ids to return movies
    def mock_find_by_ids(movie_ids, **kwargs):
        return [
            create_mock_movie(mid, mid + 1000, f"Movie {mid}") for mid in movie_ids
        ]

    repo.find_by_ids = Mock(side_effect=mock_find_by_ids)

    return repo


@pytest.fixture
def retrieval_engine(mock_embedding_service, mock_vector_search, mock_movie_repo):
    """Create retrieval engine with mocked dependencies."""
    return SemanticRetrievalEngine(
        embedding_service=mock_embedding_service,
        vector_search=mock_vector_search,
        movie_repo=mock_movie_repo,
    )


@pytest.fixture
def simple_parsed_query():
    """Simple parsed query for testing."""
    return ParsedQuery(
        raw_query="sci-fi movies",
        intent=QueryIntent(
            raw_query="sci-fi movies",
            themes=["space", "technology"],
        ),
        confidence="high",
        source="llm",
    )


@pytest.fixture
def parsed_query_with_constraints():
    """Parsed query with constraints."""
    return ParsedQuery(
        raw_query="sci-fi movies from 2020-2023",
        intent=QueryIntent(
            raw_query="sci-fi movies from 2020-2023",
            themes=["space"],
            constraints=QueryConstraints(
                year_min=2020,
                year_max=2023,
                languages=["en"],
                rating_min=7.0,
                genres=["Science Fiction"],
            ),
        ),
        confidence="high",
        source="llm",
    )


# =============================================================================
# Retrieval Pipeline Tests
# =============================================================================


class TestRetrievalPipeline:
    """Test the complete retrieval pipeline."""

    def test_retrieve_basic(self, retrieval_engine, simple_parsed_query):
        """Test basic retrieval without filters."""
        config = RetrievalConfig(
            top_k=5,
            apply_filters=False,
            max_results=10,
        )

        results = retrieval_engine.retrieve(simple_parsed_query, config)

        # Should return results
        assert isinstance(results, list)
        assert len(results) > 0
        assert len(results) <= config.max_results

        # Check result structure
        result = results[0]
        assert "movie_id" in result
        assert "title" in result
        assert "similarity_score" in result
        assert "plot_summary" in result
        assert "genres" in result

    def test_retrieve_with_filters(
        self, retrieval_engine, parsed_query_with_constraints
    ):
        """Test retrieval with constraint filtering."""
        config = RetrievalConfig(
            top_k=10,
            apply_filters=True,
            max_results=5,
        )

        results = retrieval_engine.retrieve(parsed_query_with_constraints, config)

        # Should return filtered results
        assert isinstance(results, list)

        # All results should match constraints
        for result in results:
            assert result["original_language"] in ["en"]
            assert result["year"] >= 2020
            assert result["year"] <= 2023
            assert result["rating"] >= 7.0

    def test_retrieve_respects_max_results(self, retrieval_engine, simple_parsed_query):
        """Test that max_results limit is respected."""
        config = RetrievalConfig(
            top_k=100,
            max_results=3,
        )

        results = retrieval_engine.retrieve(simple_parsed_query, config)

        # Should not exceed max_results
        assert len(results) <= 3

    def test_retrieve_filters_adult_content_by_default(
        self, retrieval_engine, simple_parsed_query, mock_movie_repo
    ):
        """Test that adult content is filtered by default."""
        # Add an adult movie to mock results
        adult_movie = Mock(spec=Movie)
        adult_movie.id = 99
        adult_movie.adult = True
        adult_movie.title = "Adult Movie"
        adult_movie.original_language = "en"
        adult_movie.year = 2020

        def mock_find_with_adult(movie_ids, **kwargs):
            movies = [
                Mock(
                    spec=Movie,
                    id=mid,
                    adult=(mid == 99),
                    title=f"Movie {mid}",
                    original_language="en",
                    year=2020,
                    vote_average=8.0,
                    runtime=120,
                    genres=[],
                    keywords=[],
                    cast_members=[],
                    release_date=date(2020, 1, 1),
                    popularity=100,
                    vote_count=1000,
                    plot_summary="Plot",
                    tagline="Tag",
                    original_title=f"Movie {mid}",
                    poster_url="",
                    backdrop_url="",
                )
                for mid in movie_ids
            ]
            return movies

        mock_movie_repo.find_by_ids = Mock(side_effect=mock_find_with_adult)

        config = RetrievalConfig(include_adult=False)
        results = retrieval_engine.retrieve(simple_parsed_query, config)

        # Should not include adult movie
        assert all(not result.get("adult", False) for result in results)

    def test_retrieve_includes_adult_when_specified(
        self, retrieval_engine, simple_parsed_query
    ):
        """Test that adult content is included when explicitly requested."""
        config = RetrievalConfig(include_adult=True, apply_filters=False)

        results = retrieval_engine.retrieve(simple_parsed_query, config)

        # Should not filter by adult flag (though our mock doesn't have adult content)
        assert isinstance(results, list)

    def test_retrieve_empty_vector_results(
        self, retrieval_engine, simple_parsed_query, mock_vector_search
    ):
        """Test handling when vector search returns no results."""
        mock_vector_search.search.return_value = []

        results = retrieval_engine.retrieve(simple_parsed_query)

        # Should return empty list
        assert results == []

    def test_retrieve_applies_minimum_similarity(
        self, retrieval_engine, simple_parsed_query
    ):
        """Test filtering by minimum similarity threshold."""
        config = RetrievalConfig(
            min_similarity=0.9,
            apply_filters=False,
        )

        results = retrieval_engine.retrieve(simple_parsed_query, config)

        # All results should have similarity >= 0.9
        for result in results:
            assert result["similarity_score"] >= 0.9


# =============================================================================
# Vector Search Tests
# =============================================================================


class TestVectorSearch:
    """Test vector search integration."""

    def test_search_similar_calls_vector_search(
        self, retrieval_engine, mock_vector_search
    ):
        """Test that _search_similar calls vector search service."""
        query_embedding = np.random.randn(768)

        results = retrieval_engine._search_similar(
            query_embedding=query_embedding,
            top_k=10,
            min_similarity=0.0,
        )

        # Should call vector search
        mock_vector_search.search.assert_called_once()
        call_args = mock_vector_search.search.call_args
        assert call_args[1]["k"] == 10

    def test_search_similar_filters_by_similarity(self, retrieval_engine):
        """Test similarity threshold filtering."""
        query_embedding = np.random.randn(768)

        results = retrieval_engine._search_similar(
            query_embedding=query_embedding,
            top_k=10,
            min_similarity=0.90,
        )

        # Should filter low-similarity results
        assert all(score >= 0.90 for _, score in results)


# =============================================================================
# Metadata Enrichment Tests
# =============================================================================


class TestMetadataEnrichment:
    """Test metadata enrichment from database."""

    def test_enrich_metadata_fetches_movies(
        self, retrieval_engine, mock_movie_repo
    ):
        """Test that enrichment fetches movies from repository."""
        candidates = [(1, 0.95), (2, 0.92), (3, 0.88)]

        enriched = retrieval_engine._enrich_metadata(candidates)

        # Should call repository
        mock_movie_repo.find_by_ids.assert_called_once()
        call_args = mock_movie_repo.find_by_ids.call_args[0][0]
        assert set(call_args) == {1, 2, 3}

    def test_enrich_metadata_includes_similarity_scores(self, retrieval_engine):
        """Test that enriched results include similarity scores."""
        candidates = [(1, 0.95), (2, 0.92)]

        enriched = retrieval_engine._enrich_metadata(candidates)

        # Check similarity scores are included
        assert enriched[0]["similarity_score"] == 0.95
        assert enriched[1]["similarity_score"] == 0.92

    def test_enrich_metadata_sorts_by_similarity(self, retrieval_engine):
        """Test that results are sorted by similarity score."""
        candidates = [(1, 0.85), (2, 0.95), (3, 0.90)]

        enriched = retrieval_engine._enrich_metadata(candidates)

        # Should be sorted descending by similarity
        scores = [r["similarity_score"] for r in enriched]
        assert scores == sorted(scores, reverse=True)

    def test_enrich_metadata_includes_all_fields(self, retrieval_engine):
        """Test that all required movie fields are included."""
        candidates = [(1, 0.95)]

        enriched = retrieval_engine._enrich_metadata(candidates)
        result = enriched[0]

        # Check all expected fields
        required_fields = [
            "movie_id",
            "tmdb_id",
            "title",
            "original_title",
            "plot_summary",
            "tagline",
            "release_date",
            "year",
            "runtime",
            "rating",
            "vote_count",
            "popularity",
            "original_language",
            "adult",
            "poster_url",
            "backdrop_url",
            "similarity_score",
            "genres",
            "keywords",
            "cast",
        ]

        for field in required_fields:
            assert field in result

    def test_enrich_metadata_empty_candidates(self, retrieval_engine):
        """Test enrichment with empty candidate list."""
        enriched = retrieval_engine._enrich_metadata([])

        assert enriched == []


# =============================================================================
# Filter Application Tests
# =============================================================================


class TestFilterApplication:
    """Test constraint filtering."""

    def test_filter_by_language(self, retrieval_engine):
        """Test language filtering."""
        candidates = [
            {"movie_id": 1, "original_language": "en", "adult": False, "year": 2020},
            {"movie_id": 2, "original_language": "fr", "adult": False, "year": 2020},
            {"movie_id": 3, "original_language": "en", "adult": False, "year": 2020},
        ]

        constraints = QueryConstraints(languages=["en"])

        filtered = retrieval_engine._apply_filters(
            candidates=candidates,
            constraints=constraints,
            include_adult=False,
        )

        # Should only include English movies
        assert len(filtered) == 2
        assert all(c["original_language"] == "en" for c in filtered)

    def test_filter_by_year_range(self, retrieval_engine):
        """Test year range filtering."""
        candidates = [
            {"movie_id": 1, "year": 2019, "adult": False},
            {"movie_id": 2, "year": 2020, "adult": False},
            {"movie_id": 3, "year": 2021, "adult": False},
            {"movie_id": 4, "year": 2022, "adult": False},
        ]

        constraints = QueryConstraints(year_min=2020, year_max=2021)

        filtered = retrieval_engine._apply_filters(
            candidates=candidates,
            constraints=constraints,
            include_adult=False,
        )

        # Should only include 2020-2021 movies
        assert len(filtered) == 2
        assert all(2020 <= c["year"] <= 2021 for c in filtered)

    def test_filter_by_rating(self, retrieval_engine):
        """Test rating minimum filtering."""
        candidates = [
            {"movie_id": 1, "rating": 6.5, "adult": False},
            {"movie_id": 2, "rating": 7.5, "adult": False},
            {"movie_id": 3, "rating": 8.5, "adult": False},
        ]

        constraints = QueryConstraints(rating_min=7.0)

        filtered = retrieval_engine._apply_filters(
            candidates=candidates,
            constraints=constraints,
            include_adult=False,
        )

        # Should only include rating >= 7.0
        assert len(filtered) == 2
        assert all(c["rating"] >= 7.0 for c in filtered)

    def test_filter_by_runtime(self, retrieval_engine):
        """Test runtime range filtering."""
        candidates = [
            {"movie_id": 1, "runtime": 90, "adult": False},
            {"movie_id": 2, "runtime": 120, "adult": False},
            {"movie_id": 3, "runtime": 150, "adult": False},
        ]

        constraints = QueryConstraints(runtime_min=100, runtime_max=140)

        filtered = retrieval_engine._apply_filters(
            candidates=candidates,
            constraints=constraints,
            include_adult=False,
        )

        # Should only include runtime 100-140
        assert len(filtered) == 1
        assert filtered[0]["runtime"] == 120

    def test_filter_adult_content(self, retrieval_engine):
        """Test adult content filtering."""
        candidates = [
            {"movie_id": 1, "adult": False},
            {"movie_id": 2, "adult": True},
            {"movie_id": 3, "adult": False},
        ]

        filtered = retrieval_engine._apply_filters(
            candidates=candidates,
            constraints=None,
            include_adult=False,
        )

        # Should exclude adult movies
        assert len(filtered) == 2
        assert all(not c["adult"] for c in filtered)

    def test_filter_multiple_constraints(self, retrieval_engine):
        """Test applying multiple constraints together."""
        candidates = [
            {
                "movie_id": 1,
                "year": 2020,
                "original_language": "en",
                "rating": 8.0,
                "adult": False,
            },
            {
                "movie_id": 2,
                "year": 2019,
                "original_language": "en",
                "rating": 8.5,
                "adult": False,
            },
            {
                "movie_id": 3,
                "year": 2020,
                "original_language": "fr",
                "rating": 7.5,
                "adult": False,
            },
        ]

        constraints = QueryConstraints(
            year_min=2020,
            languages=["en"],
            rating_min=7.0,
        )

        filtered = retrieval_engine._apply_filters(
            candidates=candidates,
            constraints=constraints,
            include_adult=False,
        )

        # Should only include movie 1 (meets all criteria)
        assert len(filtered) == 1
        assert filtered[0]["movie_id"] == 1

    def test_filter_no_constraints(self, retrieval_engine):
        """Test filtering with no constraints (only adult filter)."""
        candidates = [
            {"movie_id": 1, "adult": False},
            {"movie_id": 2, "adult": False},
        ]

        filtered = retrieval_engine._apply_filters(
            candidates=candidates,
            constraints=None,
            include_adult=False,
        )

        # Should return all non-adult candidates
        assert len(filtered) == 2


# =============================================================================
# Helper Method Tests
# =============================================================================


class TestHelperMethods:
    """Test helper methods."""

    def test_matches_year_range_within(self):
        """Test year matching within range."""
        assert SemanticRetrievalEngine._matches_year_range(2020, 2019, 2021)

    def test_matches_year_range_boundary(self):
        """Test year matching on boundaries."""
        assert SemanticRetrievalEngine._matches_year_range(2020, 2020, 2020)

    def test_matches_year_range_outside(self):
        """Test year outside range."""
        assert not SemanticRetrievalEngine._matches_year_range(2018, 2019, 2021)

    def test_matches_year_range_none_year(self):
        """Test matching with None year."""
        assert not SemanticRetrievalEngine._matches_year_range(None, 2019, 2021)

    def test_matches_year_range_no_bounds(self):
        """Test year matching with no bounds."""
        assert SemanticRetrievalEngine._matches_year_range(2020, None, None)

    def test_matches_runtime_range(self):
        """Test runtime matching within range."""
        assert SemanticRetrievalEngine._matches_runtime_range(120, 100, 150)
        assert not SemanticRetrievalEngine._matches_runtime_range(90, 100, 150)
        assert not SemanticRetrievalEngine._matches_runtime_range(None, 100, 150)


# =============================================================================
# Configuration Tests
# =============================================================================


class TestRetrievalConfig:
    """Test retrieval configuration."""

    def test_default_config(self):
        """Test default configuration values."""
        config = RetrievalConfig()

        assert config.top_k == 100
        assert config.min_similarity == 0.0
        assert config.apply_filters is True
        assert config.include_adult is False
        assert config.max_results == 50

    def test_custom_config(self):
        """Test custom configuration."""
        config = RetrievalConfig(
            top_k=50,
            min_similarity=0.8,
            apply_filters=False,
            include_adult=True,
            max_results=10,
        )

        assert config.top_k == 50
        assert config.min_similarity == 0.8
        assert config.apply_filters is False
        assert config.include_adult is True
        assert config.max_results == 10


# =============================================================================
# Lazy Loading Tests
# =============================================================================


class TestLazyLoading:
    """Test lazy loading of services."""

    def test_lazy_load_embedding_service(self):
        """Test embedding service is lazy-loaded."""
        engine = SemanticRetrievalEngine(movie_repo=Mock())

        # Should not be loaded yet
        assert engine._embedding_service is None

        # Should load on access
        service = engine.embedding_service
        assert service is not None

        # Should return same instance
        assert engine.embedding_service is service

    def test_lazy_load_vector_search(self):
        """Test vector search is lazy-loaded."""
        engine = SemanticRetrievalEngine(movie_repo=Mock())

        # Should not be loaded yet
        assert engine._vector_search is None

        # Should load on access (and attempt to load index)
        with patch.object(
            SemanticRetrievalEngine,
            "_vector_search",
            new_callable=lambda: Mock(),
        ):
            service = engine.vector_search
            assert service is not None

    def test_movie_repo_must_be_injected(self):
        """Test that movie repo cannot be lazy-loaded (raises error)."""
        engine = SemanticRetrievalEngine()

        with pytest.raises(ValueError, match="MovieRepository must be injected"):
            _ = engine.movie_repo
