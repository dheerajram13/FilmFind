"""
Tests for Pydantic schema validation in search and sixty-mode request models.

Tests:
- SearchRequest: min_length, max_length, HTML injection guard, limit bounds, whitespace stripping
- SixtyPickRequest: enum whitelisting for mood/context/craving
"""
import sys
from pathlib import Path

import pytest
from pydantic import ValidationError

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.scoring import VALID_CONTEXTS, VALID_CRAVINGS, VALID_MOODS
from app.schemas.search import SearchRequest


# =============================================================================
# SearchRequest
# =============================================================================


class TestSearchRequest:
    def test_valid_query_accepted(self):
        req = SearchRequest(query="sci-fi movies with time travel")
        assert req.query == "sci-fi movies with time travel"

    def test_query_too_short_raises(self):
        with pytest.raises(ValidationError) as exc_info:
            SearchRequest(query="hi")
        assert "min_length" in str(exc_info.value).lower() or "3" in str(exc_info.value)

    def test_query_one_char_raises(self):
        with pytest.raises(ValidationError):
            SearchRequest(query="a")

    def test_query_at_min_length_passes(self):
        req = SearchRequest(query="abc")
        assert req.query == "abc"

    def test_query_too_long_raises(self):
        with pytest.raises(ValidationError):
            SearchRequest(query="x" * 501)

    def test_query_at_max_length_passes(self):
        req = SearchRequest(query="a" * 500)
        assert len(req.query) == 500

    def test_html_script_tag_rejected(self):
        with pytest.raises(ValidationError):
            SearchRequest(query="<script>alert(1)</script>")

    def test_html_img_tag_rejected(self):
        with pytest.raises(ValidationError):
            SearchRequest(query="<img src=x onerror=alert(1)>")

    def test_html_generic_tag_rejected(self):
        with pytest.raises(ValidationError):
            SearchRequest(query="<b>bold</b> movie")

    def test_angle_brackets_no_tag_passes(self):
        """Bare < or > without forming a tag should pass."""
        req = SearchRequest(query="movie with budget > 100 million")
        assert req.query == "movie with budget > 100 million"

    def test_whitespace_stripped(self):
        req = SearchRequest(query="  action film  ")
        assert req.query == "action film"

    def test_default_limit(self):
        req = SearchRequest(query="action films")
        assert req.limit == 10

    def test_limit_minimum_1(self):
        req = SearchRequest(query="action films", limit=1)
        assert req.limit == 1

    def test_limit_zero_raises(self):
        with pytest.raises(ValidationError):
            SearchRequest(query="action films", limit=0)

    def test_limit_max_20_passes(self):
        req = SearchRequest(query="action films", limit=20)
        assert req.limit == 20

    def test_limit_above_20_raises(self):
        with pytest.raises(ValidationError):
            SearchRequest(query="action films", limit=21)

    def test_limit_50_raises(self):
        """Old max was 50 — must now be rejected."""
        with pytest.raises(ValidationError):
            SearchRequest(query="action films", limit=50)


# =============================================================================
# SixtyPickRequest — imported inline so we can test after schema validators are added
# =============================================================================


class TestSixtyPickRequest:
    """
    Tests for SixtyPickRequest Pydantic validators.

    These tests exercise the field_validator whitelist checks that
    replace the in-endpoint if-not-in-VALID_* runtime checks.
    """

    def _make(self, mood="happy", context="solo-night", craving="laugh"):
        from app.api.routes.sixty import SixtyPickRequest
        return SixtyPickRequest(mood=mood, context=context, craving=craving)

    def test_valid_inputs_accepted(self):
        req = self._make("happy", "solo-night", "laugh")
        assert req.mood == "happy"
        assert req.context == "solo-night"
        assert req.craving == "laugh"

    def test_invalid_mood_raises(self):
        with pytest.raises(ValidationError):
            self._make(mood="evil")

    def test_invalid_context_raises(self):
        with pytest.raises(ValidationError):
            self._make(context="underground-rave")

    def test_invalid_craving_raises(self):
        with pytest.raises(ValidationError):
            self._make(craving="destroy")

    @pytest.mark.parametrize("mood", sorted(VALID_MOODS))
    def test_all_valid_moods_accepted(self, mood):
        req = self._make(mood=mood)
        assert req.mood == mood

    @pytest.mark.parametrize("context", sorted(VALID_CONTEXTS))
    def test_all_valid_contexts_accepted(self, context):
        req = self._make(context=context)
        assert req.context == context

    @pytest.mark.parametrize("craving", sorted(VALID_CRAVINGS))
    def test_all_valid_cravings_accepted(self, craving):
        req = self._make(craving=craving)
        assert req.craving == craving

    def test_empty_mood_raises(self):
        with pytest.raises(ValidationError):
            self._make(mood="")

    def test_uppercase_mood_raises(self):
        """Enum matching is case-sensitive — 'HAPPY' is not 'happy'."""
        with pytest.raises(ValidationError):
            self._make(mood="HAPPY")
