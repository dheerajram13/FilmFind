"""
Tests for enum parsing in query parser.

Tests the fix for enum validation bug where invalid enum values
were being accepted due to incorrect membership checking.
"""

import pytest
from unittest.mock import patch

from app.schemas.query import EmotionType, ToneType, QueryParserConfig
from app.services.query_parser import QueryParser


class TestEnumParsing:
    """Test that enum parsing correctly handles valid and invalid values"""

    @pytest.fixture
    def query_parser(self):
        """Create query parser with mocked LLM"""
        config = QueryParserConfig(llm_provider="groq", enable_fallback=True)
        with patch("app.services.llm_client.settings") as mock_settings:
            mock_settings.LLM_PROVIDER = "groq"
            mock_settings.GROQ_API_KEY = "test_key"
            mock_settings.GROQ_MODEL = "llama-3.1-70b-versatile"
            return QueryParser(config=config)

    def test_valid_tone_values(self, query_parser):
        """Test that valid tone values are parsed correctly"""
        mock_response = {
            "themes": [],
            "tones": ["dark", "serious", "intense"],  # All valid
            "emotions": [],
            "reference_titles": [],
            "keywords": [],
            "plot_elements": [],
            "undesired_themes": [],
            "undesired_tones": [],
            "is_comparison_query": False,
            "is_mood_query": True,
            "media_type": "both",
            "genres": [],
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
            "search_text": "test",
        }

        with patch.object(query_parser.llm_client, "generate_json", return_value=mock_response):
            parsed = query_parser.parse("test query")

            assert len(parsed.intent.tones) == 3
            assert ToneType.DARK in parsed.intent.tones
            assert ToneType.SERIOUS in parsed.intent.tones
            assert ToneType.INTENSE in parsed.intent.tones

    def test_invalid_tone_values_skipped(self, query_parser):
        """Test that invalid tone values are skipped with warning"""
        mock_response = {
            "themes": [],
            "tones": ["dark", "invalid_tone", "serious", "another_bad_one"],  # Mix of valid/invalid
            "emotions": [],
            "reference_titles": [],
            "keywords": [],
            "plot_elements": [],
            "undesired_themes": [],
            "undesired_tones": [],
            "is_comparison_query": False,
            "is_mood_query": True,
            "media_type": "both",
            "genres": [],
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
            "search_text": "test",
        }

        with patch.object(query_parser.llm_client, "generate_json", return_value=mock_response):
            parsed = query_parser.parse("test query")

            # Should only have the 2 valid tones
            assert len(parsed.intent.tones) == 2
            assert ToneType.DARK in parsed.intent.tones
            assert ToneType.SERIOUS in parsed.intent.tones

    def test_valid_emotion_values(self, query_parser):
        """Test that valid emotion values are parsed correctly"""
        mock_response = {
            "themes": [],
            "tones": [],
            "emotions": ["joy", "fear", "awe"],  # All valid
            "reference_titles": [],
            "keywords": [],
            "plot_elements": [],
            "undesired_themes": [],
            "undesired_tones": [],
            "is_comparison_query": False,
            "is_mood_query": True,
            "media_type": "both",
            "genres": [],
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
            "search_text": "test",
        }

        with patch.object(query_parser.llm_client, "generate_json", return_value=mock_response):
            parsed = query_parser.parse("test query")

            assert len(parsed.intent.emotions) == 3
            assert EmotionType.JOY in parsed.intent.emotions
            assert EmotionType.FEAR in parsed.intent.emotions
            assert EmotionType.AWE in parsed.intent.emotions

    def test_invalid_emotion_values_skipped(self, query_parser):
        """Test that invalid emotion values are skipped"""
        mock_response = {
            "themes": [],
            "tones": [],
            "emotions": ["joy", "bad_emotion", "fear"],  # Mix of valid/invalid
            "reference_titles": [],
            "keywords": [],
            "plot_elements": [],
            "undesired_themes": [],
            "undesired_tones": [],
            "is_comparison_query": False,
            "is_mood_query": True,
            "media_type": "both",
            "genres": [],
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
            "search_text": "test",
        }

        with patch.object(query_parser.llm_client, "generate_json", return_value=mock_response):
            parsed = query_parser.parse("test query")

            # Should only have the 2 valid emotions
            assert len(parsed.intent.emotions) == 2
            assert EmotionType.JOY in parsed.intent.emotions
            assert EmotionType.FEAR in parsed.intent.emotions

    def test_all_invalid_enum_values(self, query_parser):
        """Test handling when all enum values are invalid"""
        mock_response = {
            "themes": [],
            "tones": ["invalid1", "invalid2"],  # All invalid
            "emotions": ["bad1", "bad2"],  # All invalid
            "reference_titles": [],
            "keywords": [],
            "plot_elements": [],
            "undesired_themes": [],
            "undesired_tones": [],
            "is_comparison_query": False,
            "is_mood_query": False,
            "media_type": "both",
            "genres": [],
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
            "search_text": "test",
        }

        with patch.object(query_parser.llm_client, "generate_json", return_value=mock_response):
            parsed = query_parser.parse("test query")

            # Should have empty lists when all values are invalid
            assert len(parsed.intent.tones) == 0
            assert len(parsed.intent.emotions) == 0

    def test_empty_enum_lists(self, query_parser):
        """Test handling empty enum lists"""
        mock_response = {
            "themes": [],
            "tones": [],  # Empty
            "emotions": [],  # Empty
            "reference_titles": [],
            "keywords": [],
            "plot_elements": [],
            "undesired_themes": [],
            "undesired_tones": [],
            "is_comparison_query": False,
            "is_mood_query": False,
            "media_type": "both",
            "genres": [],
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
            "search_text": "test",
        }

        with patch.object(query_parser.llm_client, "generate_json", return_value=mock_response):
            parsed = query_parser.parse("test query")

            assert len(parsed.intent.tones) == 0
            assert len(parsed.intent.emotions) == 0

    def test_undesired_tones_parsing(self, query_parser):
        """Test that undesired_tones are also parsed correctly"""
        mock_response = {
            "themes": [],
            "tones": [],
            "emotions": [],
            "reference_titles": [],
            "keywords": [],
            "plot_elements": [],
            "undesired_themes": [],
            "undesired_tones": ["light", "invalid_tone", "comedic"],  # Mix
            "is_comparison_query": False,
            "is_mood_query": False,
            "media_type": "both",
            "genres": [],
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
            "search_text": "test",
        }

        with patch.object(query_parser.llm_client, "generate_json", return_value=mock_response):
            parsed = query_parser.parse("test query")

            # Should only have the 2 valid tones
            assert len(parsed.intent.undesired_tones) == 2
            assert ToneType.LIGHT in parsed.intent.undesired_tones
            assert ToneType.COMEDIC in parsed.intent.undesired_tones
