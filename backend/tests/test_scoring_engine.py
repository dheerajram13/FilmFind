"""
Tests for Multi-Signal Scoring Engine.

Tests cover:
- Individual signal extractors
- Weight management and normalization
- Composite scoring
- Adaptive strategy selection
"""

from datetime import UTC, datetime

import pytest

from app.schemas.query import (
    EmotionType,
    ParsedQuery,
    QueryConstraints,
    QueryIntent,
    ToneType,
)
from app.services.scoring_engine import (
    AdaptiveScoringStrategy,
    MultiSignalScoringEngine,
    ScoringWeights,
)
from app.services.signal_extractors import (
    GenreKeywordMatchExtractor,
    PopularityExtractor,
    RatingQualityExtractor,
    RecencyExtractor,
    SemanticSimilarityExtractor,
    SignalExtractorFactory,
)


# ==============================================================================
# Fixtures
# ==============================================================================


@pytest.fixture()
def sample_movie() -> dict:
    """Sample movie data for testing."""
    return {
        "movie_id": 1,
        "tmdb_id": 123,
        "title": "Interstellar",
        "similarity_score": 0.85,
        "genres": ["Science Fiction", "Drama"],
        "keywords": ["space", "time travel", "black hole"],
        "popularity": 150.5,
        "rating": 8.6,
        "vote_count": 15000,
        "year": 2014,
        "release_date": "2014-11-07",
    }


@pytest.fixture()
def sample_query() -> ParsedQuery:
    """Sample parsed query for testing."""
    return ParsedQuery(
        intent=QueryIntent(
            raw_query="dark sci-fi like Interstellar",
            themes=["space", "time travel"],
            tones=[ToneType.DARK, ToneType.SERIOUS],
            emotions=[EmotionType.AWE],
            reference_titles=["Interstellar"],
        ),
        constraints=QueryConstraints(genres=["Science Fiction"]),
        search_text="dark sci-fi like Interstellar space time travel",
        confidence_score=0.9,
        parsing_method="llm",
    )


@pytest.fixture()
def context() -> dict:
    """Sample context for extractors."""
    return {"max_log_popularity": 6.0, "current_year": 2024}


# ==============================================================================
# Signal Extractor Tests
# ==============================================================================


class TestSemanticSimilarityExtractor:
    """Tests for semantic similarity extractor."""

    def test_extract_basic(self, sample_movie, sample_query, context):
        """Test basic similarity extraction."""
        extractor = SemanticSimilarityExtractor()
        score = extractor.extract(sample_movie, sample_query, context)

        assert score == 0.85
        assert 0.0 <= score <= 1.0

    def test_extract_missing_similarity(self, sample_query, context):
        """Test extraction when similarity_score is missing."""
        movie = {"title": "Test Movie"}
        extractor = SemanticSimilarityExtractor()
        score = extractor.extract(movie, sample_query, context)

        assert score == 0.0

    def test_extract_clamps_values(self, sample_query, context):
        """Test that scores are clamped to [0, 1]."""
        extractor = SemanticSimilarityExtractor()

        # Test upper bound
        movie_high = {"similarity_score": 1.5}
        assert extractor.extract(movie_high, sample_query, context) == 1.0

        # Test lower bound
        movie_low = {"similarity_score": -0.5}
        assert extractor.extract(movie_low, sample_query, context) == 0.0


class TestGenreKeywordMatchExtractor:
    """Tests for genre/keyword match extractor."""

    def test_extract_perfect_match(self, sample_movie, sample_query, context):
        """Test perfect genre and keyword match."""
        extractor = GenreKeywordMatchExtractor()
        score = extractor.extract(sample_movie, sample_query, context)

        # Should have good score: 1 genre match (0.3) + 2 theme/keyword matches (0.2) = 0.5
        assert score >= 0.5
        assert 0.0 <= score <= 1.0

    def test_extract_genre_only(self, sample_query, context):
        """Test genre match without keyword match."""
        movie = {"genres": ["Science Fiction"], "keywords": []}
        extractor = GenreKeywordMatchExtractor()
        score = extractor.extract(movie, sample_query, context)

        # Should have some score from genre match
        assert score >= 0.3
        assert score < 1.0

    def test_extract_no_match(self, context):
        """Test no genre or keyword matches."""
        movie = {"genres": ["Comedy"], "keywords": ["funny", "jokes"]}
        query = ParsedQuery(
            intent=QueryIntent(
                raw_query="action movies",
                themes=["explosions", "car chases"],
            ),
            constraints=QueryConstraints(genres=["Action"]),
            search_text="action movies explosions car chases",
        )
        extractor = GenreKeywordMatchExtractor()
        score = extractor.extract(movie, query, context)

        # Should have low score (0.5 default when no genre match)
        assert score < 0.7

    def test_extract_missing_metadata(self, sample_query, context):
        """Test extraction with missing genre/keyword data."""
        movie = {"title": "Unknown Movie"}
        extractor = GenreKeywordMatchExtractor()
        score = extractor.extract(movie, sample_query, context)

        # Query has genres but movie doesn't, so no match score (0.0)
        # Query has themes but movie has no keywords, so no theme match either
        assert score == 0.0


class TestPopularityExtractor:
    """Tests for popularity extractor."""

    def test_extract_high_popularity(self, sample_movie, sample_query, context):
        """Test extraction for highly popular movie."""
        sample_movie["popularity"] = 500.0
        extractor = PopularityExtractor()
        score = extractor.extract(sample_movie, sample_query, context)

        # High popularity should give high score
        assert score > 0.7
        assert score <= 1.0

    def test_extract_low_popularity(self, sample_query, context):
        """Test extraction for low popularity movie."""
        movie = {"popularity": 5.0}
        extractor = PopularityExtractor()
        score = extractor.extract(movie, sample_query, context)

        # Low popularity should give lower score
        assert 0.0 <= score < 0.5

    def test_extract_zero_popularity(self, sample_query, context):
        """Test extraction with zero popularity."""
        movie = {"popularity": 0.0}
        extractor = PopularityExtractor()
        score = extractor.extract(movie, sample_query, context)

        assert score == 0.0

    def test_extract_logarithmic_scaling(self, sample_query, context):
        """Test that popularity uses logarithmic scaling."""
        extractor = PopularityExtractor()

        # Double popularity should not double score (log scaling)
        movie_100 = {"popularity": 100.0}
        movie_200 = {"popularity": 200.0}

        score_100 = extractor.extract(movie_100, sample_query, context)
        score_200 = extractor.extract(movie_200, sample_query, context)

        # Score increase should be less than 2x
        assert score_200 < score_100 * 2


class TestRatingQualityExtractor:
    """Tests for rating quality extractor."""

    def test_extract_high_rating_high_votes(self, sample_movie, sample_query, context):
        """Test extraction for high-rated movie with many votes."""
        sample_movie["rating"] = 9.0
        sample_movie["vote_count"] = 10000
        extractor = RatingQualityExtractor()
        score = extractor.extract(sample_movie, sample_query, context)

        # Should have high score
        assert score > 0.7
        assert score <= 1.0

    def test_extract_high_rating_low_votes(self, sample_query, context):
        """Test extraction for high-rated movie with few votes."""
        movie = {"rating": 9.0, "vote_count": 10}
        extractor = RatingQualityExtractor()
        score = extractor.extract(movie, sample_query, context)

        # Score should be lower due to low vote count
        assert 0.3 < score < 0.8

    def test_extract_low_rating(self, sample_query, context):
        """Test extraction for low-rated movie."""
        movie = {"rating": 3.0, "vote_count": 1000}
        extractor = RatingQualityExtractor()
        score = extractor.extract(movie, sample_query, context)

        # Should have low score
        assert score < 0.5

    def test_extract_zero_rating(self, sample_query, context):
        """Test extraction with zero rating."""
        movie = {"rating": 0.0, "vote_count": 0}
        extractor = RatingQualityExtractor()
        score = extractor.extract(movie, sample_query, context)

        assert score == 0.0

    def test_vote_confidence_weighting(self, sample_query, context):
        """Test that vote count affects confidence weighting."""
        extractor = RatingQualityExtractor()

        # Same rating, different vote counts
        movie_few_votes = {"rating": 8.0, "vote_count": 50}
        movie_many_votes = {"rating": 8.0, "vote_count": 5000}

        score_few = extractor.extract(movie_few_votes, sample_query, context)
        score_many = extractor.extract(movie_many_votes, sample_query, context)

        # More votes should result in higher score
        assert score_many > score_few


class TestRecencyExtractor:
    """Tests for recency extractor."""

    def test_extract_current_year(self, sample_query):
        """Test extraction for movie released this year."""
        current_year = 2024
        movie = {"year": current_year}
        context = {"current_year": current_year}

        extractor = RecencyExtractor()
        score = extractor.extract(movie, sample_query, context)

        # Current year should give max score
        assert score == 1.0

    def test_extract_last_year(self, sample_query):
        """Test extraction for movie released last year."""
        movie = {"year": 2023}
        context = {"current_year": 2024}

        extractor = RecencyExtractor()
        score = extractor.extract(movie, sample_query, context)

        # Last year should have high but not perfect score
        assert 0.8 < score < 1.0

    def test_extract_old_movie(self, sample_query):
        """Test extraction for old movie."""
        movie = {"year": 1990}
        context = {"current_year": 2024}

        extractor = RecencyExtractor()
        score = extractor.extract(movie, sample_query, context)

        # Old movie should have low score
        assert 0.1 <= score < 0.3

    def test_extract_from_release_date(self, sample_query):
        """Test extraction using release_date instead of year."""
        movie = {"release_date": "2024-06-15"}
        context = {"current_year": 2024}

        extractor = RecencyExtractor()
        score = extractor.extract(movie, sample_query, context)

        # Should extract year from release_date
        assert score == 1.0

    def test_extract_missing_year(self, sample_query):
        """Test extraction with missing year data."""
        movie = {"title": "Unknown Movie"}
        context = {"current_year": 2024}

        extractor = RecencyExtractor()
        score = extractor.extract(movie, sample_query, context)

        # Should return default score
        assert score == 0.5

    def test_exponential_decay(self, sample_query):
        """Test that recency uses exponential decay."""
        context = {"current_year": 2024}
        extractor = RecencyExtractor()

        # Test decay over years
        movie_2023 = {"year": 2023}
        movie_2022 = {"year": 2022}
        movie_2020 = {"year": 2020}

        score_2023 = extractor.extract(movie_2023, sample_query, context)
        score_2022 = extractor.extract(movie_2022, sample_query, context)
        score_2020 = extractor.extract(movie_2020, sample_query, context)

        # Scores should decay exponentially
        assert score_2023 > score_2022 > score_2020


# ==============================================================================
# Signal Extractor Factory Tests
# ==============================================================================


class TestSignalExtractorFactory:
    """Tests for signal extractor factory."""

    def test_create_all_extractors(self):
        """Test creating all extractors."""
        extractors = SignalExtractorFactory.create_all_extractors()

        assert len(extractors) == 5
        assert "semantic_similarity" in extractors
        assert "genre_keyword_match" in extractors
        assert "popularity" in extractors
        assert "rating_quality" in extractors
        assert "recency" in extractors

    def test_get_extractor_valid(self):
        """Test getting a valid extractor."""
        extractor = SignalExtractorFactory.get_extractor("semantic_similarity")
        assert isinstance(extractor, SemanticSimilarityExtractor)

    def test_get_extractor_invalid(self):
        """Test getting an invalid extractor raises error."""
        with pytest.raises(ValueError, match="Unknown signal"):
            SignalExtractorFactory.get_extractor("invalid_signal")


# ==============================================================================
# Scoring Weights Tests
# ==============================================================================


class TestScoringWeights:
    """Tests for scoring weights configuration."""

    def test_init_default_weights(self):
        """Test default weight initialization."""
        weights = ScoringWeights()

        assert weights.semantic_similarity == 0.5
        assert weights.genre_keyword_match == 0.2
        assert weights.popularity == 0.1
        assert weights.rating_quality == 0.1
        assert weights.recency == 0.1

    def test_init_custom_weights(self):
        """Test custom weight initialization."""
        weights = ScoringWeights(
            semantic_similarity=0.6,
            genre_keyword_match=0.3,
            popularity=0.05,
            rating_quality=0.03,
            recency=0.02,
        )

        assert weights.semantic_similarity == 0.6
        assert weights.genre_keyword_match == 0.3

    def test_get_total_weight(self):
        """Test total weight calculation."""
        weights = ScoringWeights()
        total = weights.get_total_weight()

        assert abs(total - 1.0) < 0.001  # Use tolerance for floating point comparison

    def test_normalize(self):
        """Test weight normalization."""
        weights = ScoringWeights(
            semantic_similarity=2.0,
            genre_keyword_match=1.0,
            popularity=0.5,
            rating_quality=0.5,
            recency=1.0,
        )

        normalized = weights.normalize()

        # Should sum to 1.0
        assert abs(normalized.get_total_weight() - 1.0) < 0.001
        # Relative proportions should be maintained
        assert normalized.semantic_similarity > normalized.genre_keyword_match

    def test_to_dict(self):
        """Test converting weights to dictionary."""
        weights = ScoringWeights()
        weights_dict = weights.to_dict()

        assert isinstance(weights_dict, dict)
        assert len(weights_dict) == 5
        assert "semantic_similarity" in weights_dict
        assert weights_dict["semantic_similarity"] == 0.5

    def test_from_dict(self):
        """Test creating weights from dictionary."""
        weights_dict = {
            "semantic_similarity": 0.7,
            "genre_keyword_match": 0.15,
            "popularity": 0.05,
            "rating_quality": 0.05,
            "recency": 0.05,
        }

        weights = ScoringWeights.from_dict(weights_dict)

        assert weights.semantic_similarity == 0.7
        assert weights.genre_keyword_match == 0.15

    def test_semantic_focused_preset(self):
        """Test semantic-focused preset weights."""
        weights = ScoringWeights.semantic_focused()

        assert weights.semantic_similarity == 0.7
        assert weights.semantic_similarity > weights.genre_keyword_match

    def test_popularity_focused_preset(self):
        """Test popularity-focused preset weights."""
        weights = ScoringWeights.popularity_focused()

        assert weights.popularity == 0.3
        # popularity equals semantic in this preset
        assert weights.popularity >= weights.semantic_similarity

    def test_discovery_focused_preset(self):
        """Test discovery-focused preset weights."""
        weights = ScoringWeights.discovery_focused()

        assert weights.recency == 0.25
        assert weights.recency > weights.popularity

    def test_quality_focused_preset(self):
        """Test quality-focused preset weights."""
        weights = ScoringWeights.quality_focused()

        assert weights.rating_quality == 0.35
        assert weights.rating_quality > weights.popularity


# ==============================================================================
# Multi-Signal Scoring Engine Tests
# ==============================================================================


class TestMultiSignalScoringEngine:
    """Tests for multi-signal scoring engine."""

    def test_init_default_extractors(self):
        """Test initialization with default extractors."""
        engine = MultiSignalScoringEngine()

        assert len(engine.extractors) == 5
        assert "semantic_similarity" in engine.extractors

    def test_init_custom_extractors(self):
        """Test initialization with custom extractors."""
        custom_extractors = {
            "semantic_similarity": SemanticSimilarityExtractor(),
            "popularity": PopularityExtractor(),
        }

        engine = MultiSignalScoringEngine(extractors=custom_extractors)

        assert len(engine.extractors) == 2
        assert "semantic_similarity" in engine.extractors

    def test_score_candidates_empty(self, sample_query):
        """Test scoring empty candidate list."""
        engine = MultiSignalScoringEngine()
        results = engine.score_candidates([], sample_query)

        assert results == []

    def test_score_candidates_basic(self, sample_movie, sample_query):
        """Test basic candidate scoring."""
        engine = MultiSignalScoringEngine()
        candidates = [sample_movie.copy()]

        results = engine.score_candidates(candidates, sample_query)

        assert len(results) == 1
        assert "final_score" in results[0]
        assert "signal_scores" in results[0]
        assert 0.0 <= results[0]["final_score"] <= 1.0

    def test_score_candidates_multiple(self, sample_query):
        """Test scoring multiple candidates."""
        candidates = [
            {
                "title": "Movie A",
                "similarity_score": 0.9,
                "genres": ["Science Fiction"],
                "keywords": ["space"],
                "popularity": 200.0,
                "rating": 8.5,
                "vote_count": 10000,
                "year": 2023,
            },
            {
                "title": "Movie B",
                "similarity_score": 0.6,
                "genres": ["Drama"],
                "keywords": [],
                "popularity": 50.0,
                "rating": 7.0,
                "vote_count": 1000,
                "year": 2010,
            },
        ]

        engine = MultiSignalScoringEngine()
        results = engine.score_candidates(candidates, sample_query)

        assert len(results) == 2
        # Results should be sorted by final_score
        assert results[0]["final_score"] >= results[1]["final_score"]
        # Movie A should rank higher due to better semantic match
        assert results[0]["title"] == "Movie A"

    def test_score_candidates_custom_weights(self, sample_movie, sample_query):
        """Test scoring with custom weights."""
        engine = MultiSignalScoringEngine()
        weights = ScoringWeights.popularity_focused()

        results = engine.score_candidates([sample_movie], sample_query, weights=weights)

        assert "final_score" in results[0]
        # Score should reflect popularity-focused weighting

    def test_score_candidates_without_breakdown(self, sample_movie, sample_query):
        """Test scoring without signal breakdown."""
        engine = MultiSignalScoringEngine()

        results = engine.score_candidates(
            [sample_movie], sample_query, include_signal_breakdown=False
        )

        assert "final_score" in results[0]
        assert "signal_scores" not in results[0]

    def test_score_candidates_handles_errors(self, sample_query):
        """Test that scoring handles individual candidate errors gracefully."""
        # Create candidate with invalid data
        bad_candidate = {"title": "Bad Movie"}  # Missing required fields

        engine = MultiSignalScoringEngine()
        results = engine.score_candidates([bad_candidate], sample_query)

        # Should still return result with default score
        assert len(results) == 1
        assert "final_score" in results[0]

    def test_prepare_context(self, sample_movie, sample_query):
        """Test context preparation for extractors."""
        engine = MultiSignalScoringEngine()
        candidates = [sample_movie, {"popularity": 500.0}]

        context = engine._prepare_context(candidates)

        assert "max_log_popularity" in context
        assert "current_year" in context
        assert context["current_year"] == datetime.now(UTC).year

    def test_score_single_candidate(self, sample_movie, sample_query):
        """Test scoring a single candidate."""
        engine = MultiSignalScoringEngine()
        weights = ScoringWeights()
        context = {"max_log_popularity": 6.0, "current_year": 2024}

        result = engine._score_single_candidate(
            movie=sample_movie,
            parsed_query=sample_query,
            weights=weights,
            context=context,
            include_breakdown=True,
        )

        assert "final_score" in result
        assert "signal_scores" in result
        assert len(result["signal_scores"]) == 5
        # Final score should be weighted average of signal scores
        assert 0.0 <= result["final_score"] <= 1.0


# ==============================================================================
# Adaptive Scoring Strategy Tests
# ==============================================================================


class TestAdaptiveScoringStrategy:
    """Tests for adaptive scoring strategy."""

    def test_select_weights_trending_query(self):
        """Test weight selection for trending queries."""
        query = ParsedQuery(
            intent=QueryIntent(
                raw_query="trending movies",
                themes=["popular"],
            ),
            constraints=QueryConstraints(),
            search_text="trending movies popular",
        )

        weights = AdaptiveScoringStrategy.select_weights(query)

        # Should use popularity-focused weights
        assert weights.popularity > 0.2

    def test_select_weights_recent_query(self):
        """Test weight selection for recent content queries."""
        query = ParsedQuery(
            intent=QueryIntent(
                raw_query="new movies in 2024",
                themes=["recent"],
            ),
            constraints=QueryConstraints(),
            search_text="new movies in 2024 recent",
        )

        weights = AdaptiveScoringStrategy.select_weights(query)

        # Should use discovery-focused weights
        assert weights.recency > 0.2

    def test_select_weights_quality_query(self):
        """Test weight selection for quality-focused queries."""
        query = ParsedQuery(
            intent=QueryIntent(
                raw_query="best movies of all time",
                themes=["quality"],
            ),
            constraints=QueryConstraints(),
            search_text="best movies of all time quality",
        )

        weights = AdaptiveScoringStrategy.select_weights(query)

        # Should use quality-focused weights
        assert weights.rating_quality > 0.2

    def test_select_weights_similarity_query(self):
        """Test weight selection for similarity queries."""
        query = ParsedQuery(
            intent=QueryIntent(
                raw_query="movies like Interstellar",
                themes=["space"],
                reference_titles=["Interstellar"],
            ),
            constraints=QueryConstraints(),
            search_text="movies like Interstellar space",
        )

        weights = AdaptiveScoringStrategy.select_weights(query)

        # Should use semantic-focused weights
        assert weights.semantic_similarity > 0.6

    def test_select_weights_default(self):
        """Test weight selection for generic queries."""
        query = ParsedQuery(
            intent=QueryIntent(
                raw_query="action movies",
                themes=["action"],
            ),
            constraints=QueryConstraints(),
            search_text="action movies",
        )

        weights = AdaptiveScoringStrategy.select_weights(query)

        # Should use default balanced weights
        assert abs(weights.semantic_similarity - 0.5) < 0.1


# ==============================================================================
# Integration Tests
# ==============================================================================


class TestScoringEngineIntegration:
    """Integration tests for complete scoring pipeline."""

    def test_end_to_end_scoring(self, sample_query):
        """Test complete end-to-end scoring pipeline."""
        # Setup candidates
        candidates = [
            {
                "title": "Interstellar",
                "similarity_score": 0.9,
                "genres": ["Science Fiction", "Drama"],
                "keywords": ["space", "time travel"],
                "popularity": 200.0,
                "rating": 8.6,
                "vote_count": 15000,
                "year": 2014,
            },
            {
                "title": "Gravity",
                "similarity_score": 0.8,
                "genres": ["Science Fiction", "Thriller"],
                "keywords": ["space", "survival"],
                "popularity": 150.0,
                "rating": 7.7,
                "vote_count": 12000,
                "year": 2013,
            },
            {
                "title": "The Martian",
                "similarity_score": 0.75,
                "genres": ["Science Fiction", "Adventure"],
                "keywords": ["space", "mars", "survival"],
                "popularity": 180.0,
                "rating": 8.0,
                "vote_count": 14000,
                "year": 2015,
            },
        ]

        # Score with different strategies
        engine = MultiSignalScoringEngine()

        # Default weights
        results_default = engine.score_candidates(candidates.copy(), sample_query)

        # Quality-focused weights
        results_quality = engine.score_candidates(
            candidates.copy(), sample_query, weights=ScoringWeights.quality_focused()
        )

        # Results should be sorted
        assert len(results_default) == 3
        assert len(results_quality) == 3

        # All candidates should have scores
        for result in results_default:
            assert "final_score" in result
            assert "signal_scores" in result

        # Interstellar should rank highly due to high semantic similarity
        assert results_default[0]["title"] == "Interstellar"

    def test_adaptive_strategy_integration(self):
        """Test adaptive strategy selection with scoring."""
        queries = [
            ParsedQuery(
                intent=QueryIntent(
                    raw_query="trending sci-fi movies",
                    themes=["sci-fi"],
                ),
                constraints=QueryConstraints(),
                search_text="trending sci-fi movies",
            ),
            ParsedQuery(
                intent=QueryIntent(
                    raw_query="best rated movies",
                    themes=["quality"],
                ),
                constraints=QueryConstraints(),
                search_text="best rated movies quality",
            ),
            ParsedQuery(
                intent=QueryIntent(
                    raw_query="recent releases",
                    themes=["new"],
                ),
                constraints=QueryConstraints(),
                search_text="recent releases new",
            ),
        ]

        candidate = {
            "title": "Test Movie",
            "similarity_score": 0.8,
            "genres": ["Science Fiction"],
            "keywords": ["space"],
            "popularity": 150.0,
            "rating": 8.5,
            "vote_count": 10000,
            "year": 2023,
        }

        engine = MultiSignalScoringEngine()

        for query in queries:
            # Select weights adaptively
            weights = AdaptiveScoringStrategy.select_weights(query)

            # Score with selected weights
            results = engine.score_candidates([candidate.copy()], query, weights=weights)

            assert len(results) == 1
            assert "final_score" in results[0]
