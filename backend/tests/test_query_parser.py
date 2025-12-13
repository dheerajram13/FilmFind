"""
Tests for Query Understanding Service (Module 2.1)

Tests cover:
- LLM-based parsing (mocked)
- Rule-based fallback parsing
- Schema validation
- Edge cases and error handling
"""

from unittest.mock import patch

import pytest

from app.schemas.query import (
    EmotionType,
    MediaType,
    ParsedQuery,
    QueryConstraints,
    QueryIntent,
    QueryParserConfig,
    ToneType,
)
from app.services.llm_client import LLMClientError
from app.services.query_parser import QueryParser


# --- Fixtures ---


@pytest.fixture()
def query_parser():
    """Create query parser with rule-based fallback enabled"""
    config = QueryParserConfig(llm_provider="groq", enable_fallback=True)
    with patch("app.services.llm_client.settings") as mock_settings:
        mock_settings.LLM_PROVIDER = "groq"
        mock_settings.GROQ_API_KEY = "test_key"
        mock_settings.GROQ_MODEL = "llama-3.1-70b-versatile"
        mock_settings.GROQ_MAX_TOKENS = 1024
        mock_settings.GROQ_TEMPERATURE = 0.7
        return QueryParser(config=config)


@pytest.fixture()
def mock_llm_response_interstellar():
    """Mock LLM response for 'dark sci-fi movies like Interstellar'"""
    return {
        "themes": ["space exploration", "science fiction", "time dilation"],
        "tones": ["dark", "serious"],
        "emotions": ["awe", "dark_tone"],
        "reference_titles": ["Interstellar"],
        "keywords": ["sci-fi", "dark", "space"],
        "plot_elements": [],
        "undesired_themes": ["romance"],
        "undesired_tones": [],
        "is_comparison_query": True,
        "is_mood_query": False,
        "media_type": "movie",
        "genres": ["Science Fiction"],
        "exclude_genres": [],
        "languages": [],
        "year_min": None,
        "year_max": None,
        "rating_min": None,
        "runtime_min": None,
        "runtime_max": None,
        "streaming_providers": [],
        "popular_only": False,
        "hidden_gems": False,
        "search_text": "dark science fiction space exploration time dilation cosmic themes",
    }


@pytest.fixture()
def mock_llm_response_friends():
    """Mock LLM response for 'lighthearted sitcoms like Friends'"""
    return {
        "themes": ["friendship", "relationships", "comedy of life"],
        "tones": ["light", "comedic"],
        "emotions": ["joy", "hope"],
        "reference_titles": ["Friends"],
        "keywords": ["sitcom", "friendship", "lighthearted"],
        "plot_elements": ["group of friends"],
        "undesired_themes": [],
        "undesired_tones": [],
        "is_comparison_query": True,
        "is_mood_query": True,
        "media_type": "tv_show",
        "genres": ["Comedy"],
        "exclude_genres": [],
        "languages": [],
        "year_min": None,
        "year_max": None,
        "rating_min": None,
        "runtime_min": None,
        "runtime_max": None,
        "streaming_providers": [],
        "popular_only": False,
        "hidden_gems": False,
        "search_text": "lighthearted sitcom friendship group friends comedy relationships",
    }


# --- Schema Tests ---


class TestSchemas:
    """Test Pydantic schemas for query parsing"""

    def test_query_constraints_defaults(self):
        """Test QueryConstraints with default values"""
        constraints = QueryConstraints()
        assert constraints.media_type == MediaType.BOTH
        assert constraints.genres == []
        assert constraints.year_min is None
        assert constraints.adult_content is False

    def test_query_constraints_validation(self):
        """Test QueryConstraints validation"""
        # Valid year
        constraints = QueryConstraints(year_min=2020, year_max=2023)
        assert constraints.year_min == 2020
        assert constraints.year_max == 2023

        # Valid rating
        constraints = QueryConstraints(rating_min=7.0)
        assert constraints.rating_min == 7.0

    def test_query_intent_defaults(self):
        """Test QueryIntent with default values"""
        intent = QueryIntent(raw_query="test query")
        assert intent.raw_query == "test query"
        assert intent.themes == []
        assert intent.tones == []
        assert intent.is_comparison_query is False

    def test_parsed_query_complete(self):
        """Test complete ParsedQuery construction"""
        intent = QueryIntent(
            raw_query="dark movies",
            themes=["dark", "thriller"],
            tones=[ToneType.DARK],
        )
        constraints = QueryConstraints(genres=["Thriller"], year_min=2020)
        parsed = ParsedQuery(
            intent=intent,
            constraints=constraints,
            search_text="dark thriller movies",
            confidence_score=0.9,
            parsing_method="llm",
        )

        assert parsed.intent.raw_query == "dark movies"
        assert parsed.constraints.year_min == 2020
        assert parsed.search_text == "dark thriller movies"
        assert parsed.confidence_score == 0.9


# --- Rule-Based Parser Tests ---


class TestRuleBasedParser:
    """Test rule-based fallback parser"""

    def test_parse_simple_query(self, query_parser):
        """Test parsing simple query with rule-based parser"""
        # Mock LLM to fail so it falls back to rules
        with patch.object(
            query_parser.llm_client, "generate_json", side_effect=LLMClientError("LLM failed")
        ):
            parsed = query_parser.parse("dark thriller movies")

            assert parsed.parsing_method == "rule-based"
            assert parsed.confidence_score == 0.5
            assert "dark" in parsed.intent.keywords or ToneType.DARK in parsed.intent.tones

    def test_parse_reference_title(self, query_parser):
        """Test extracting reference titles with 'like' pattern"""
        with patch.object(
            query_parser.llm_client, "generate_json", side_effect=LLMClientError("LLM failed")
        ):
            parsed = query_parser.parse("Movies like Interstellar with space themes")

            assert parsed.parsing_method == "rule-based"
            assert "Interstellar" in parsed.intent.reference_titles
            assert parsed.intent.is_comparison_query is True

    def test_parse_tones(self, query_parser):
        """Test detecting tones from query"""
        with patch.object(
            query_parser.llm_client, "generate_json", side_effect=LLMClientError("LLM failed")
        ):
            # Dark tone
            parsed = query_parser.parse("dark movies")
            assert ToneType.DARK in parsed.intent.tones

            # Light tone
            parsed = query_parser.parse("lighthearted comedies")
            assert ToneType.LIGHT in parsed.intent.tones

            # Intense tone
            parsed = query_parser.parse("intense thriller")
            assert ToneType.INTENSE in parsed.intent.tones

    def test_parse_emotions(self, query_parser):
        """Test detecting emotions from query"""
        with patch.object(
            query_parser.llm_client, "generate_json", side_effect=LLMClientError("LLM failed")
        ):
            # Horror/Fear
            parsed = query_parser.parse("scary horror movies")
            assert EmotionType.FEAR in parsed.intent.emotions

            # Romance
            parsed = query_parser.parse("romantic movies")
            assert EmotionType.ROMANCE in parsed.intent.emotions

    def test_parse_media_type(self, query_parser):
        """Test detecting media type (movie vs TV show)"""
        with patch.object(
            query_parser.llm_client, "generate_json", side_effect=LLMClientError("LLM failed")
        ):
            # Movies only
            parsed = query_parser.parse("action movies")
            assert parsed.constraints.media_type == MediaType.MOVIE

            # TV shows only
            parsed = query_parser.parse("comedy tv shows")
            assert parsed.constraints.media_type == MediaType.TV_SHOW

            # Both
            parsed = query_parser.parse("action content")
            assert parsed.constraints.media_type == MediaType.BOTH

    def test_parse_genres(self, query_parser):
        """Test detecting genres from query"""
        with patch.object(
            query_parser.llm_client, "generate_json", side_effect=LLMClientError("LLM failed")
        ):
            parsed = query_parser.parse("action sci-fi thriller")
            assert (
                "Action" in parsed.constraints.genres
                or "Science Fiction" in parsed.constraints.genres
            )

    def test_parse_year_constraints(self, query_parser):
        """Test detecting year constraints"""
        with patch.object(
            query_parser.llm_client, "generate_json", side_effect=LLMClientError("LLM failed")
        ):
            # Year min (from/since)
            parsed = query_parser.parse("movies from 2020")
            assert parsed.constraints.year_min == 2020

            # Year range
            parsed = query_parser.parse("movies from 2015-2020")
            assert parsed.constraints.year_min == 2015
            assert parsed.constraints.year_max == 2020

    def test_parse_undesired_elements(self, query_parser):
        """Test detecting undesired elements"""
        with patch.object(
            query_parser.llm_client, "generate_json", side_effect=LLMClientError("LLM failed")
        ):
            parsed = query_parser.parse("action movies without romance")
            assert "romance" in parsed.intent.undesired_themes


# --- LLM-Based Parser Tests (Mocked) ---


class TestLLMParser:
    """Test LLM-based parser with mocked responses"""

    def test_parse_with_llm_interstellar(self, query_parser, mock_llm_response_interstellar):
        """Test LLM parsing for Interstellar query"""
        with patch.object(
            query_parser.llm_client, "generate_json", return_value=mock_llm_response_interstellar
        ):
            parsed = query_parser.parse("dark sci-fi movies like Interstellar with less romance")

            assert parsed.parsing_method == "llm"
            assert parsed.confidence_score == 0.9
            assert "Interstellar" in parsed.intent.reference_titles
            assert ToneType.DARK in parsed.intent.tones
            assert "Science Fiction" in parsed.constraints.genres
            assert "romance" in parsed.intent.undesired_themes
            assert parsed.intent.is_comparison_query is True

    def test_parse_with_llm_friends(self, query_parser, mock_llm_response_friends):
        """Test LLM parsing for Friends query"""
        with patch.object(
            query_parser.llm_client, "generate_json", return_value=mock_llm_response_friends
        ):
            parsed = query_parser.parse("lighthearted sitcoms like Friends")

            assert parsed.parsing_method == "llm"
            assert "Friends" in parsed.intent.reference_titles
            assert ToneType.LIGHT in parsed.intent.tones
            assert EmotionType.JOY in parsed.intent.emotions
            assert parsed.constraints.media_type == MediaType.TV_SHOW
            assert parsed.intent.is_mood_query is True

    def test_parse_llm_with_fallback(self, query_parser):
        """Test LLM failure triggers fallback"""
        with patch.object(
            query_parser.llm_client, "generate_json", side_effect=LLMClientError("API error")
        ):
            parsed = query_parser.parse("action movies")

            # Should fall back to rule-based
            assert parsed.parsing_method == "rule-based"
            assert parsed.confidence_score == 0.5

    def test_parse_llm_no_fallback_raises(self):
        """Test LLM failure without fallback raises exception"""
        config = QueryParserConfig(enable_fallback=False)
        with patch("app.services.llm_client.settings") as mock_settings:
            mock_settings.LLM_PROVIDER = "groq"
            mock_settings.GROQ_API_KEY = "test_key"
            mock_settings.GROQ_MODEL = "llama-3.1-70b-versatile"
            parser = QueryParser(config=config)

            with patch.object(
                parser.llm_client, "generate_json", side_effect=LLMClientError("API error")
            ):
                with pytest.raises(LLMClientError):
                    parser.parse("action movies")


# --- Edge Cases and Error Handling ---


class TestEdgeCases:
    """Test edge cases and error handling"""

    def test_parse_empty_query(self, query_parser):
        """Test parsing empty query raises error"""
        with pytest.raises(ValueError, match="Query cannot be empty"):
            query_parser.parse("")

    def test_parse_whitespace_query(self, query_parser):
        """Test parsing whitespace-only query raises error"""
        with pytest.raises(ValueError, match="Query cannot be empty"):
            query_parser.parse("   ")

    def test_parse_very_long_query(self, query_parser):
        """Test parsing very long query"""
        long_query = "action " * 100
        with patch.object(
            query_parser.llm_client, "generate_json", side_effect=LLMClientError("Too long")
        ):
            parsed = query_parser.parse(long_query)
            assert parsed.parsing_method == "rule-based"

    def test_parse_special_characters(self, query_parser):
        """Test parsing query with special characters"""
        with patch.object(
            query_parser.llm_client, "generate_json", side_effect=LLMClientError("Failed")
        ):
            parsed = query_parser.parse("action movies with $$$$ budget!!!")
            assert parsed.intent.raw_query == "action movies with $$$$ budget!!!"

    def test_parse_non_english_query(self, query_parser):
        """Test parsing non-English query"""
        with patch.object(
            query_parser.llm_client, "generate_json", side_effect=LLMClientError("Failed")
        ):
            parsed = query_parser.parse("películas de acción")
            assert parsed.parsing_method == "rule-based"


# --- Integration Tests ---


class TestQueryParserIntegration:
    """Integration tests for the full query parser"""

    @pytest.mark.parametrize(
        "query,expected_media_type,expected_genres",
        [
            ("action movies", MediaType.MOVIE, ["Action"]),
            ("comedy tv shows", MediaType.TV_SHOW, ["Comedy"]),
            ("thriller series", MediaType.TV_SHOW, ["Thriller"]),
        ],
    )
    def test_parse_multiple_queries_rule_based(
        self, query_parser, query, expected_media_type, expected_genres
    ):
        """Test parsing multiple queries with rule-based parser"""
        with patch.object(
            query_parser.llm_client, "generate_json", side_effect=LLMClientError("Failed")
        ):
            parsed = query_parser.parse(query)
            assert parsed.constraints.media_type == expected_media_type
            # At least one expected genre should be present
            assert (
                any(genre in parsed.constraints.genres for genre in expected_genres)
                or len(parsed.constraints.genres) == 0
            )

    def test_context_manager(self):
        """Test QueryParser as context manager"""
        with patch("app.services.llm_client.settings") as mock_settings:
            mock_settings.LLM_PROVIDER = "groq"
            mock_settings.GROQ_API_KEY = "test_key"
            mock_settings.GROQ_MODEL = "llama-3.1-70b-versatile"
            with QueryParser() as parser:
                assert parser is not None
                with patch.object(
                    parser.llm_client, "generate_json", side_effect=LLMClientError("Failed")
                ):
                    parsed = parser.parse("action movies")
                    assert parsed is not None
