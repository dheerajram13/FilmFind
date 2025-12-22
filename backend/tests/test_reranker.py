"""
Tests for LLM Re-Ranking Service - Module 2.4

Tests cover:
- Prompt template building
- Re-ranking cache functionality
- LLM re-ranker with mock LLM
- Fallback behavior on errors
- Explanation generation
"""

from unittest.mock import MagicMock, patch

import pytest

from app.schemas.query import EmotionType, ParsedQuery, QueryConstraints, ToneType
from app.services.exceptions import LLMClientError, LLMRateLimitError
from app.services.reranker import (
    LLMReRanker,
    PromptTemplate,
    ReRankingCache,
    rerank_candidates,
)


# Fixtures


@pytest.fixture()
def sample_query():
    """Sample user query"""
    return "dark sci-fi movies like Interstellar with less romance"


@pytest.fixture()
def sample_parsed_query():
    """Sample parsed query intent"""
    from app.schemas.query import QueryIntent

    return ParsedQuery(
        intent=QueryIntent(
            raw_query="dark sci-fi movies like Interstellar with less romance",
            reference_titles=["Interstellar"],
            themes=["space", "exploration"],
            tones=[ToneType.DARK, ToneType.SERIOUS],
            emotions=[EmotionType.AWE, EmotionType.THRILL],
            undesired_themes=["romance"],
            undesired_tones=[ToneType.LIGHT],
            is_comparison_query=True,
        ),
        constraints=QueryConstraints(
            genres=["Science Fiction"],
            year_min=2010,
            rating_min=7.0,
        ),
        search_text="dark sci-fi movies space exploration Interstellar dark serious tone awe thrill",
    )


@pytest.fixture()
def sample_candidates():
    """Sample candidate movies"""
    return [
        {
            "id": 1,
            "tmdb_id": 157336,
            "title": "Interstellar",
            "release_date": "2014-11-05",
            "overview": "The adventures of a group of explorers who make use of a newly discovered wormhole...",
            "genres": [{"id": 12, "name": "Adventure"}, {"id": 878, "name": "Science Fiction"}],
            "keywords": [{"name": "space"}, {"name": "black hole"}, {"name": "time travel"}],
            "cast_members": [{"name": "Matthew McConaughey"}, {"name": "Anne Hathaway"}],
            "vote_average": 8.4,
            "popularity": 145.2,
            "similarity_score": 0.95,
            "final_score": 0.92,
        },
        {
            "id": 2,
            "tmdb_id": 76341,
            "title": "Mad Max: Fury Road",
            "release_date": "2015-05-13",
            "overview": "An apocalyptic story set in the furthest reaches of our planet...",
            "genres": [{"id": 28, "name": "Action"}, {"id": 12, "name": "Adventure"}],
            "keywords": [{"name": "desert"}, {"name": "chase"}, {"name": "survival"}],
            "cast_members": [{"name": "Tom Hardy"}, {"name": "Charlize Theron"}],
            "vote_average": 7.6,
            "popularity": 98.5,
            "similarity_score": 0.72,
            "final_score": 0.75,
        },
        {
            "id": 3,
            "tmdb_id": 550,
            "title": "Fight Club",
            "release_date": "1999-10-15",
            "overview": "A ticking-time-bomb insomniac and a slippery soap salesman...",
            "genres": [{"id": 18, "name": "Drama"}],
            "keywords": [{"name": "nihilism"}, {"name": "identity"}, {"name": "underground"}],
            "cast_members": [{"name": "Brad Pitt"}, {"name": "Edward Norton"}],
            "vote_average": 8.4,
            "popularity": 112.3,
            "similarity_score": 0.68,
            "final_score": 0.71,
        },
        {
            "id": 4,
            "tmdb_id": 13,
            "title": "Forrest Gump",
            "release_date": "1994-07-06",
            "overview": "A man with a low IQ has accomplished great things...",
            "genres": [
                {"id": 35, "name": "Comedy"},
                {"id": 18, "name": "Drama"},
                {"id": 10749, "name": "Romance"},
            ],
            "keywords": [{"name": "vietnam war"}, {"name": "love"}, {"name": "friendship"}],
            "cast_members": [{"name": "Tom Hanks"}, {"name": "Robin Wright"}],
            "vote_average": 8.5,
            "popularity": 125.1,
            "similarity_score": 0.45,
            "final_score": 0.50,
        },
    ]


# Tests for PromptTemplate


class TestPromptTemplate:
    """Test prompt template building"""

    def test_format_query_context_with_all_fields(self, sample_query, sample_parsed_query):
        """Test formatting query context with all fields populated"""
        context = PromptTemplate._format_query_context(sample_query, sample_parsed_query)

        assert "USER QUERY" in context
        assert sample_query in context
        assert "PARSED INTENT" in context
        assert "Reference Movies: Interstellar" in context
        assert "Genres: Science Fiction" in context
        assert "Themes: space, exploration" in context
        assert "Desired Tones: dark, serious" in context
        assert "Desired Emotions: awe, thrill" in context
        assert "Avoid Themes: romance" in context
        assert "Avoid Tones: light" in context
        assert "Years: 2010-any" in context
        assert "Min Rating: 7.0/10" in context

    def test_format_query_context_minimal(self):
        """Test formatting query context with minimal fields"""
        from app.schemas.query import QueryIntent

        query = "good movies"
        parsed_query = ParsedQuery(
            intent=QueryIntent(raw_query=query),
            constraints=QueryConstraints(),
            search_text=query,
        )

        context = PromptTemplate._format_query_context(query, parsed_query)

        assert "USER QUERY" in context
        assert "good movies" in context
        assert "PARSED INTENT" in context
        # Should not have empty sections
        assert "Reference Movies:" not in context
        assert "Genres:" not in context

    def test_format_candidates(self, sample_candidates):
        """Test formatting candidates for prompt"""
        candidates_text = PromptTemplate._format_candidates(sample_candidates)

        assert "CANDIDATE MOVIES" in candidates_text
        assert "[0] Interstellar (2014)" in candidates_text
        assert "[1] Mad Max: Fury Road (2015)" in candidates_text
        assert "Adventure, Science Fiction" in candidates_text
        assert "Keywords: space, black hole, time travel" in candidates_text
        assert "Cast: Matthew McConaughey, Anne Hathaway" in candidates_text
        assert "Rating: 8.4/10" in candidates_text
        assert "Similarity=0.950, Final=0.920" in candidates_text

    def test_format_candidates_truncates_long_overview(self):
        """Test that long overviews are truncated"""
        candidates = [
            {
                "title": "Test Movie",
                "release_date": "2020-01-01",
                "overview": "A" * 400,  # Very long overview
                "genres": [],
                "keywords": [],
                "cast_members": [],
                "vote_average": 7.0,
                "popularity": 50.0,
                "similarity_score": 0.8,
                "final_score": 0.75,
            }
        ]

        candidates_text = PromptTemplate._format_candidates(candidates)

        # Should be truncated to 300 chars + "..."
        assert "A" * 297 + "..." in candidates_text
        assert "A" * 400 not in candidates_text

    def test_build_reranking_prompt(self, sample_query, sample_parsed_query, sample_candidates):
        """Test building complete re-ranking prompt"""
        prompt = PromptTemplate.build_reranking_prompt(
            user_query=sample_query,
            parsed_query=sample_parsed_query,
            candidates=sample_candidates,
            top_k=10,
        )

        # Check all sections are present
        assert "USER QUERY" in prompt
        assert "PARSED INTENT" in prompt
        assert "CANDIDATE MOVIES" in prompt
        assert "Rank the top 10 most relevant movies" in prompt
        assert "Respond with ONLY a valid JSON object" in prompt
        assert '"ranked_movies"' in prompt
        assert '"movie_index"' in prompt
        assert '"relevance_score"' in prompt
        assert '"explanation"' in prompt


# Tests for ReRankingCache


class TestReRankingCache:
    """Test re-ranking cache functionality"""

    def test_cache_miss(self):
        """Test cache miss returns None"""
        cache = ReRankingCache()
        result = cache.get("test query", [1, 2, 3], 10)
        assert result is None

    def test_cache_hit(self):
        """Test cache hit returns stored result"""
        cache = ReRankingCache()
        expected = {"results": [1, 2, 3]}

        cache.store("test query", [1, 2, 3], 10, expected)
        result = cache.get("test query", [1, 2, 3], 10)

        assert result == expected

    def test_cache_key_generation_consistent(self):
        """Test that cache key generation is consistent"""
        cache = ReRankingCache()
        expected = {"results": [1, 2, 3]}

        # Set with one order
        cache.store("test query", [3, 1, 2], 10, expected)

        # Get with same IDs in different order (should still hit because we sort)
        result = cache.get("test query", [1, 2, 3], 10)
        assert result == expected

    def test_cache_different_queries(self):
        """Test that different queries don't collide"""
        cache = ReRankingCache()

        cache.store("query1", [1, 2, 3], 10, {"result": "A"})
        cache.store("query2", [1, 2, 3], 10, {"result": "B"})

        assert cache.get("query1", [1, 2, 3], 10) == {"result": "A"}
        assert cache.get("query2", [1, 2, 3], 10) == {"result": "B"}

    def test_cache_different_top_k(self):
        """Test that different top_k values don't collide"""
        cache = ReRankingCache()

        cache.store("query", [1, 2, 3], 10, {"result": "top10"})
        cache.store("query", [1, 2, 3], 5, {"result": "top5"})

        assert cache.get("query", [1, 2, 3], 10) == {"result": "top10"}
        assert cache.get("query", [1, 2, 3], 5) == {"result": "top5"}

    def test_cache_expiration(self):
        """Test that cache entries expire after TTL"""
        cache = ReRankingCache(ttl_seconds=0)  # Instant expiration

        cache.store("query", [1, 2, 3], 10, {"result": "test"})

        # Should be expired immediately
        result = cache.get("query", [1, 2, 3], 10)
        assert result is None

    def test_cache_clear(self):
        """Test cache clear removes all entries"""
        cache = ReRankingCache()

        cache.store("query1", [1, 2, 3], 10, {"result": "A"})
        cache.store("query2", [4, 5, 6], 5, {"result": "B"})

        cache.clear()

        assert cache.get("query1", [1, 2, 3], 10) is None
        assert cache.get("query2", [4, 5, 6], 5) is None


# Tests for LLMReRanker


class TestLLMReRanker:
    """Test LLM re-ranker service"""

    def test_rerank_empty_candidates(self, sample_query, sample_parsed_query):
        """Test re-ranking with empty candidates list"""
        # Create mock LLM client
        mock_llm = MagicMock()
        reranker = LLMReRanker(llm_client=mock_llm)
        result = reranker.rerank([], sample_query, sample_parsed_query)
        assert result == []

    @patch("app.services.reranker.LLMClient")
    def test_rerank_success(
        self,
        mock_llm_class,
        sample_query,
        sample_parsed_query,
        sample_candidates,
    ):
        """Test successful re-ranking with LLM"""
        # Mock LLM response
        mock_llm = MagicMock()
        mock_llm_class.return_value = mock_llm

        llm_response = {
            "ranked_movies": [
                {
                    "movie_index": 0,
                    "relevance_score": 0.95,
                    "explanation": "Perfect match - space exploration with dark, serious tone",
                },
                {
                    "movie_index": 2,
                    "relevance_score": 0.80,
                    "explanation": "Dark, serious tone but different themes",
                },
                {
                    "movie_index": 1,
                    "relevance_score": 0.65,
                    "explanation": "Dark tone but more action-focused",
                },
            ],
            "reasoning": "Ranked by thematic similarity to Interstellar",
        }

        mock_llm.generate_json.return_value = llm_response

        # Create reranker (will use mocked LLM)
        reranker = LLMReRanker(llm_client=mock_llm)

        # Re-rank
        result = reranker.rerank(
            candidates=sample_candidates,
            user_query=sample_query,
            parsed_query=sample_parsed_query,
            top_k=3,
        )

        # Verify results
        assert len(result) == 3
        assert result[0]["title"] == "Interstellar"
        assert (
            result[0]["match_explanation"]
            == "Perfect match - space exploration with dark, serious tone"
        )
        assert result[0]["llm_relevance_score"] == 0.95

        assert result[1]["title"] == "Fight Club"
        assert result[1]["llm_relevance_score"] == 0.80

        assert result[2]["title"] == "Mad Max: Fury Road"
        assert result[2]["llm_relevance_score"] == 0.65

        # Verify LLM was called
        mock_llm.generate_json.assert_called_once()

    @patch("app.services.reranker.LLMClient")
    def test_rerank_with_invalid_indices(
        self,
        mock_llm_class,
        sample_query,
        sample_parsed_query,
        sample_candidates,
    ):
        """Test re-ranking handles invalid movie indices gracefully"""
        mock_llm = MagicMock()
        mock_llm_class.return_value = mock_llm

        # LLM returns some invalid indices
        llm_response = {
            "ranked_movies": [
                {"movie_index": 0, "relevance_score": 0.95, "explanation": "Good match"},
                {
                    "movie_index": 99,
                    "relevance_score": 0.90,
                    "explanation": "Invalid index",
                },  # Invalid
                {
                    "movie_index": -1,
                    "relevance_score": 0.85,
                    "explanation": "Negative index",
                },  # Invalid
                {"movie_index": 1, "relevance_score": 0.80, "explanation": "Another match"},
            ],
            "reasoning": "Test with invalid indices",
        }

        mock_llm.generate_json.return_value = llm_response

        reranker = LLMReRanker(llm_client=mock_llm)
        result = reranker.rerank(
            candidates=sample_candidates,
            user_query=sample_query,
            parsed_query=sample_parsed_query,
            top_k=10,
        )

        # Should only include valid indices (0 and 1)
        # Plus backfill from original candidates
        assert len(result) >= 2
        assert result[0]["title"] == "Interstellar"
        assert result[1]["title"] == "Mad Max: Fury Road"

    @patch("app.services.reranker.LLMClient")
    def test_rerank_fallback_on_rate_limit(
        self,
        mock_llm_class,
        sample_query,
        sample_parsed_query,
        sample_candidates,
    ):
        """Test fallback to original order when rate limit is hit"""
        mock_llm = MagicMock()
        mock_llm_class.return_value = mock_llm

        # Simulate rate limit error
        mock_llm.generate_json.side_effect = LLMRateLimitError("Rate limit exceeded")

        reranker = LLMReRanker(llm_client=mock_llm)
        result = reranker.rerank(
            candidates=sample_candidates,
            user_query=sample_query,
            parsed_query=sample_parsed_query,
            top_k=3,
        )

        # Should fallback to original order (top 3)
        assert len(result) == 3
        assert result[0]["title"] == "Interstellar"
        assert result[1]["title"] == "Mad Max: Fury Road"
        assert result[2]["title"] == "Fight Club"

        # Explanations should not be added
        assert "match_explanation" not in result[0]

    @patch("app.services.reranker.LLMClient")
    def test_rerank_fallback_on_llm_error(
        self,
        mock_llm_class,
        sample_query,
        sample_parsed_query,
        sample_candidates,
    ):
        """Test fallback to original order when LLM fails"""
        mock_llm = MagicMock()
        mock_llm_class.return_value = mock_llm

        # Simulate LLM error
        mock_llm.generate_json.side_effect = LLMClientError("LLM API error")

        reranker = LLMReRanker(llm_client=mock_llm)
        result = reranker.rerank(
            candidates=sample_candidates,
            user_query=sample_query,
            parsed_query=sample_parsed_query,
            top_k=2,
        )

        # Should fallback to original order (top 2)
        assert len(result) == 2
        assert result[0]["title"] == "Interstellar"
        assert result[1]["title"] == "Mad Max: Fury Road"

    @patch("app.services.reranker.LLMClient")
    def test_rerank_uses_cache(
        self,
        mock_llm_class,
        sample_query,
        sample_parsed_query,
        sample_candidates,
    ):
        """Test that re-ranking uses cache for identical queries"""
        mock_llm = MagicMock()
        mock_llm_class.return_value = mock_llm

        llm_response = {
            "ranked_movies": [
                {"movie_index": 0, "relevance_score": 0.95, "explanation": "Test"},
            ],
            "reasoning": "Test",
        }

        mock_llm.generate_json.return_value = llm_response

        reranker = LLMReRanker(llm_client=mock_llm, enable_cache=True)

        # First call - should hit LLM
        result1 = reranker.rerank(
            candidates=sample_candidates,
            user_query=sample_query,
            parsed_query=sample_parsed_query,
            top_k=1,
        )

        # Second call - should use cache
        result2 = reranker.rerank(
            candidates=sample_candidates,
            user_query=sample_query,
            parsed_query=sample_parsed_query,
            top_k=1,
        )

        # LLM should only be called once
        assert mock_llm.generate_json.call_count == 1

        # Results should be identical
        assert result1 == result2

    @patch("app.services.reranker.LLMClient")
    def test_rerank_without_cache(
        self,
        mock_llm_class,
        sample_query,
        sample_parsed_query,
        sample_candidates,
    ):
        """Test re-ranking with cache disabled"""
        mock_llm = MagicMock()
        mock_llm_class.return_value = mock_llm

        llm_response = {
            "ranked_movies": [
                {"movie_index": 0, "relevance_score": 0.95, "explanation": "Test"},
            ],
            "reasoning": "Test",
        }

        mock_llm.generate_json.return_value = llm_response

        reranker = LLMReRanker(llm_client=mock_llm, enable_cache=False)

        # Two calls
        reranker.rerank(sample_candidates, sample_query, sample_parsed_query, top_k=1)
        reranker.rerank(sample_candidates, sample_query, sample_parsed_query, top_k=1)

        # LLM should be called twice (no caching)
        assert mock_llm.generate_json.call_count == 2

    @patch("app.services.reranker.LLMClient")
    def test_rerank_respects_max_candidates(
        self,
        mock_llm_class,
        sample_query,
        sample_parsed_query,
    ):
        """Test that re-ranking respects max_candidates limit"""
        mock_llm = MagicMock()
        mock_llm_class.return_value = mock_llm

        # Create 50 candidates
        many_candidates = [
            {
                "id": i,
                "tmdb_id": i,
                "title": f"Movie {i}",
                "release_date": "2020-01-01",
                "overview": f"Description {i}",
                "genres": [],
                "keywords": [],
                "cast_members": [],
                "vote_average": 7.0,
                "popularity": 50.0,
                "similarity_score": 0.8,
                "final_score": 0.75,
            }
            for i in range(50)
        ]

        llm_response = {
            "ranked_movies": [
                {"movie_index": 0, "relevance_score": 0.95, "explanation": "Best"},
            ],
            "reasoning": "Test",
        }

        mock_llm.generate_json.return_value = llm_response

        reranker = LLMReRanker(llm_client=mock_llm)

        # Call with max_candidates=20
        reranker.rerank(
            candidates=many_candidates,
            user_query=sample_query,
            parsed_query=sample_parsed_query,
            top_k=10,
            max_candidates=20,
        )

        # Check that prompt only included 20 candidates
        call_args = mock_llm.generate_json.call_args
        prompt = call_args.kwargs["prompt"]

        # Should have indices [0] through [19] but not [20] or beyond
        assert "[19]" in prompt
        assert "[20]" not in prompt

    @patch("app.services.reranker.LLMClient")
    def test_rerank_backfills_missing_results(
        self,
        mock_llm_class,
        sample_query,
        sample_parsed_query,
        sample_candidates,
    ):
        """Test that re-ranking backfills when LLM returns fewer results than requested"""
        mock_llm = MagicMock()
        mock_llm_class.return_value = mock_llm

        # LLM only returns 2 results, but we asked for 4
        llm_response = {
            "ranked_movies": [
                {"movie_index": 0, "relevance_score": 0.95, "explanation": "Best match"},
                {"movie_index": 1, "relevance_score": 0.80, "explanation": "Good match"},
            ],
            "reasoning": "Only found 2 good matches",
        }

        mock_llm.generate_json.return_value = llm_response

        reranker = LLMReRanker(llm_client=mock_llm)
        result = reranker.rerank(
            candidates=sample_candidates,
            user_query=sample_query,
            parsed_query=sample_parsed_query,
            top_k=4,  # Request 4 results
        )

        # Should get 4 results (2 from LLM + 2 backfilled)
        assert len(result) == 4

        # First 2 should have LLM explanations
        assert result[0]["match_explanation"] == "Best match"
        assert result[1]["match_explanation"] == "Good match"

        # Last 2 should be backfilled with default explanation
        assert result[2]["match_explanation"] == "Additional match based on scoring signals"
        assert result[3]["match_explanation"] == "Additional match based on scoring signals"

        # Backfilled results should not have been in LLM response
        assert result[2]["title"] != result[0]["title"]
        assert result[2]["title"] != result[1]["title"]


# Tests for convenience function


@patch("app.services.reranker.LLMClient")
def test_rerank_candidates_convenience_function(
    mock_llm_class,
    sample_query,
    sample_parsed_query,
    sample_candidates,
):
    """Test convenience function for re-ranking"""
    mock_llm = MagicMock()
    mock_llm_class.return_value = mock_llm

    llm_response = {
        "ranked_movies": [
            {"movie_index": 0, "relevance_score": 0.95, "explanation": "Test"},
        ],
        "reasoning": "Test",
    }

    mock_llm.generate_json.return_value = llm_response

    # Use convenience function
    result = rerank_candidates(
        candidates=sample_candidates,
        user_query=sample_query,
        parsed_query=sample_parsed_query,
        top_k=1,
        llm_client=mock_llm,
    )

    assert len(result) >= 1
    assert result[0]["title"] == "Interstellar"
    assert result[0]["match_explanation"] == "Test"

    # Verify LLM was called
    mock_llm.generate_json.assert_called_once()
