"""
Prompt eval tests — verifies that:
1. The eval harness scores correctly against known mock responses
2. A v2 prompt scores >= v1 on the same mocked responses (regression guard)
3. Per-field deltas are reported when a version regresses

These tests use mocked LLM responses so they are fast, deterministic,
and don't consume API quota. The actual live accuracy baseline is
established by running: python scripts/utils/run_eval.py
"""

import json
from pathlib import Path
from unittest.mock import patch
import pytest

from app.services.query_parser import QueryParser
from app.prompts import load_prompt
from scripts.utils.run_eval import check_any, score_case, run_eval


# ---------------------------------------------------------------------------
# Unit tests for scoring helpers
# ---------------------------------------------------------------------------

class TestCheckAny:
    def test_exact_match(self):
        assert check_any(["romance"], ["romance"]) is True

    def test_substring_match(self):
        assert check_any(["sci-fi"], ["dark sci-fi thriller"]) is True

    def test_case_insensitive(self):
        assert check_any(["Science Fiction"], ["science fiction"]) is True

    def test_no_match(self):
        assert check_any(["horror"], ["comedy", "romance"]) is False

    def test_empty_expected(self):
        assert check_any([], ["anything"]) is False

    def test_empty_actual(self):
        assert check_any(["drama"], []) is False

    def test_any_of_multiple(self):
        assert check_any(["thriller", "mystery"], ["psychological mystery"]) is True


class TestScoreCase:
    def _make_parsed(self, themes, tones, genres, year_min=None, year_max=None,
                     media_type="both", undesired_themes=None, languages=None,
                     reference_titles=None, rating_min=None):
        from app.schemas.query import ParsedQuery, QueryIntent, QueryConstraints, MediaType
        intent = QueryIntent(
            raw_query="test",
            themes=themes,
            tones=tones,
            undesired_themes=undesired_themes or [],
            reference_titles=reference_titles or [],
        )
        constraints = QueryConstraints(
            genres=genres,
            year_min=year_min,
            year_max=year_max,
            languages=languages or [],
            rating_min=rating_min,
            media_type=MediaType(media_type),
        )
        return ParsedQuery(intent=intent, constraints=constraints, search_text="test")

    def test_themes_pass(self):
        parsed = self._make_parsed(themes=["space exploration", "science fiction"], tones=[], genres=[])
        assert score_case(parsed, {"expect_themes_any": ["space"]})["themes"] is True

    def test_themes_fail(self):
        parsed = self._make_parsed(themes=["romance"], tones=[], genres=[])
        assert score_case(parsed, {"expect_themes_any": ["horror"]})["themes"] is False

    def test_genres_pass(self):
        parsed = self._make_parsed(themes=[], tones=[], genres=["Science Fiction"])
        assert score_case(parsed, {"expect_genres_any": ["Science Fiction"]})["genres"] is True

    def test_year_min_exact(self):
        parsed = self._make_parsed(themes=[], tones=[], genres=[], year_min=2020)
        assert score_case(parsed, {"expect_year_min": 2020})["year_min"] is True

    def test_year_min_mismatch(self):
        parsed = self._make_parsed(themes=[], tones=[], genres=[], year_min=2019)
        assert score_case(parsed, {"expect_year_min": 2020})["year_min"] is False

    def test_media_type_pass(self):
        parsed = self._make_parsed(themes=[], tones=[], genres=[], media_type="movie")
        assert score_case(parsed, {"expect_media_type": "movie"})["media_type"] is True

    def test_undesired_themes_pass(self):
        parsed = self._make_parsed(themes=[], tones=[], genres=[], undesired_themes=["romance"])
        assert score_case(parsed, {"expect_undesired_themes_any": ["romance"]})["undesired_themes"] is True

    def test_empty_expected_undesired(self):
        parsed = self._make_parsed(themes=[], tones=[], genres=[])
        assert score_case(parsed, {"expect_undesired_themes_any": []})["undesired_themes"] is True

    def test_unchecked_field_absent(self):
        parsed = self._make_parsed(themes=["action"], tones=[], genres=[])
        scores = score_case(parsed, {"expect_themes_any": ["action"]})
        assert "genres" not in scores
        assert "year_min" not in scores


# ---------------------------------------------------------------------------
# Mock LLM responses for eval harness tests
# ---------------------------------------------------------------------------

_DEFAULT_RESPONSE = {
    "themes": [], "tones": [], "emotions": [], "reference_titles": [],
    "genres": [], "languages": [], "undesired_themes": [], "undesired_tones": [],
    "media_type": "both", "year_min": None, "year_max": None, "rating_min": None,
    "popular_only": False, "hidden_gems": False,
    "streaming_providers": [], "exclude_genres": [],
    "is_comparison_query": False, "is_mood_query": False,
    "search_text": "",
}

MOCK_RESPONSES_V1 = {
    "dark sci-fi movies like Interstellar with less romance": {
        **_DEFAULT_RESPONSE,
        "themes": ["space exploration", "science fiction", "time dilation"],
        "tones": ["dark", "serious"],
        "reference_titles": ["Interstellar"],
        "genres": ["Science Fiction"],
        "undesired_themes": ["romance"],
        "media_type": "movie",
        "is_comparison_query": True,
        "search_text": "dark science fiction space exploration",
    },
    "Korean drama series about love and loss": {
        **_DEFAULT_RESPONSE,
        "themes": ["love", "loss", "romance"],
        "tones": ["serious"],
        "genres": ["Drama", "Romance"],
        "languages": ["ko"],
        "media_type": "tv_show",
        "search_text": "Korean drama love loss romance",
    },
    "thriller without jump scares and no violence": {
        **_DEFAULT_RESPONSE,
        "themes": ["suspense", "mystery", "psychological thriller"],
        "tones": ["suspenseful"],
        "genres": ["Thriller"],
        "undesired_themes": ["jump scares", "violence"],
        "search_text": "psychological thriller suspense mystery",
    },
}

# v2: same as v1 but adds rating_min extraction for one query
MOCK_RESPONSES_V2 = {
    **MOCK_RESPONSES_V1,
    "war movies rated above 8 on IMDB": {
        **_DEFAULT_RESPONSE,
        "themes": ["war", "battle", "military"],
        "tones": ["serious", "intense"],
        "genres": ["War", "Drama"],
        "media_type": "movie",
        "rating_min": 8.0,
        "search_text": "war battle military drama",
    },
}


def _make_mock_parse(responses: dict):
    """Returns a _parse_with_llm replacement that looks up responses by query substring."""
    from app.schemas.query import (
        ParsedQuery, QueryIntent, QueryConstraints, MediaType, ToneType, EmotionType
    )

    def mock_parse(self_or_query, query=None):
        # Handle both bound (self, query) and unbound (query) call patterns
        q = query if query is not None else self_or_query
        response = next(
            (v for k, v in responses.items() if k.lower() in q.lower()),
            _DEFAULT_RESPONSE,
        )

        def to_enums(vals, cls):
            result = []
            for v in (vals or []):
                try:
                    result.append(cls(v))
                except ValueError:
                    pass
            return result

        intent = QueryIntent(
            raw_query=q,
            themes=response.get("themes", []),
            tones=to_enums(response.get("tones", []), ToneType),
            emotions=to_enums(response.get("emotions", []), EmotionType),
            reference_titles=response.get("reference_titles", []),
            keywords=response.get("keywords", []),
            undesired_themes=response.get("undesired_themes", []),
            undesired_tones=to_enums(response.get("undesired_tones", []), ToneType),
            is_comparison_query=response.get("is_comparison_query", False),
            is_mood_query=response.get("is_mood_query", False),
        )
        constraints = QueryConstraints(
            media_type=MediaType(response.get("media_type", "both")),
            genres=response.get("genres", []),
            exclude_genres=response.get("exclude_genres", []),
            languages=response.get("languages", []),
            year_min=response.get("year_min"),
            year_max=response.get("year_max"),
            rating_min=response.get("rating_min"),
            streaming_providers=response.get("streaming_providers", []),
            popular_only=response.get("popular_only", False),
            hidden_gems=response.get("hidden_gems", False),
        )
        populated = sum([
            bool(response.get("themes")),
            bool(response.get("tones")),
            bool(response.get("emotions")),
            bool(response.get("search_text") and response.get("search_text") != q),
        ])
        return ParsedQuery(
            intent=intent,
            constraints=constraints,
            search_text=response.get("search_text", q),
            confidence_score=0.6 + (populated / 4) * 0.35,
            parsing_method="llm",
        )
    return mock_parse


def _run_with_mock(prompt_version: str, responses: dict) -> dict:
    def safe_load(name, version):
        try:
            return load_prompt(name, version)
        except FileNotFoundError:
            return f"mock system prompt v{version}"

    # Patch _parse_with_llm directly — bypasses all LLM call machinery cleanly
    with patch("app.services.query_parser.QueryParser._parse_with_llm",
               new=_make_mock_parse(responses)):
        with patch("scripts.utils.run_eval.load_prompt", side_effect=safe_load):
            return run_eval(prompt_version=prompt_version, output_json=True)


# ---------------------------------------------------------------------------
# Eval harness integration tests
# ---------------------------------------------------------------------------

class TestEvalHarness:
    def test_v1_mocked_queries_pass(self):
        result = _run_with_mock("1", MOCK_RESPONSES_V1)
        # Only check queries that have an explicit mock response — others return the default
        mocked_queries = list(MOCK_RESPONSES_V1.keys())
        passed = [
            r for r in result["results"]
            if r.get("query") in mocked_queries and not r.get("failed") and "error" not in r
        ]
        assert len(passed) == len(mocked_queries), (
            f"Expected all {len(mocked_queries)} mocked queries to pass, got {len(passed)}: "
            f"{[r for r in result['results'] if r.get('query') in mocked_queries and r.get('failed')]}"
        )

    def test_overall_pct_is_valid_float(self):
        result = _run_with_mock("1", MOCK_RESPONSES_V1)
        assert isinstance(result["overall_pct"], float)
        assert 0.0 <= result["overall_pct"] <= 100.0

    def test_per_field_structure(self):
        result = _run_with_mock("1", MOCK_RESPONSES_V1)
        for field, data in result["per_field"].items():
            assert "pass" in data and "total" in data
            assert data["pass"] <= data["total"]

    def test_undesired_themes_pass_on_mock(self):
        result = _run_with_mock("1", MOCK_RESPONSES_V1)
        field = result["per_field"].get("undesired_themes")
        if field:
            assert field["pass"] > 0

    def test_reference_titles_scored_when_expected(self):
        # Friends query expects reference_titles_any=["Friends"] — check it passes
        result = _run_with_mock("1", {
            "lighthearted comedies like Friends about a group of friends": {
                **_DEFAULT_RESPONSE,
                "themes": ["friendship", "comedy"],
                "tones": ["light", "comedic"],
                "genres": ["Comedy"],
                "reference_titles": ["Friends"],
                "search_text": "lighthearted comedy friendship group",
            }
        })
        friends = next(
            (r for r in result["results"] if "Friends" in r.get("query", "")), None
        )
        assert friends is not None
        assert "reference_titles" in friends.get("passed", []), (
            f"reference_titles not in passed: {friends}"
        )


# ---------------------------------------------------------------------------
# Regression guard: v2 must not score lower than v1
# ---------------------------------------------------------------------------

class TestPromptRegression:
    """
    When you write query_parser_v2.txt, add its mock responses to
    MOCK_RESPONSES_V2 above. This test enforces that v2 >= v1 overall
    and flags any single field that drops more than 10%.
    """

    def test_v2_overall_gte_v1(self):
        v1 = _run_with_mock("1", MOCK_RESPONSES_V1)
        v2 = _run_with_mock("2", MOCK_RESPONSES_V2)

        delta = v2["overall_pct"] - v1["overall_pct"]

        # Print per-field delta table (visible with pytest -s)
        all_fields = sorted(set(v1["per_field"]) | set(v2["per_field"]))
        print(f"\n{'field':<22} {'v1':>6} {'v2':>6} {'delta':>8}")
        print("-" * 46)
        for field in all_fields:
            p1 = v1["per_field"].get(field, {})
            p2 = v2["per_field"].get(field, {})
            pct1 = round(p1["pass"] / p1["total"] * 100, 1) if p1.get("total") else 0.0
            pct2 = round(p2["pass"] / p2["total"] * 100, 1) if p2.get("total") else 0.0
            arrow = "↑" if pct2 > pct1 else ("↓" if pct2 < pct1 else " ")
            print(f"  {field:<20} {pct1:>5.1f}% {pct2:>5.1f}%  {arrow} {pct2-pct1:+.1f}%")
        print(f"\n  Overall: {v1['overall_pct']}% → {v2['overall_pct']}%  ({delta:+.1f}%)")

        assert v2["overall_pct"] >= v1["overall_pct"], (
            f"Prompt v2 regressed: {v2['overall_pct']}% < v1 {v1['overall_pct']}% "
            f"(delta: {delta:+.1f}%). Check per-field breakdown above."
        )

    def test_v2_no_field_regression_gt_10pct(self):
        v1 = _run_with_mock("1", MOCK_RESPONSES_V1)
        v2 = _run_with_mock("2", MOCK_RESPONSES_V2)

        regressions = []
        for field in v1["per_field"]:
            p1 = v1["per_field"][field]
            p2 = v2["per_field"].get(field, {"pass": 0, "total": p1["total"]})
            pct1 = p1["pass"] / p1["total"] * 100
            pct2 = p2["pass"] / p2["total"] * 100 if p2.get("total") else 0.0
            if pct1 - pct2 > 10:
                regressions.append(f"{field}: {pct1:.1f}% → {pct2:.1f}%")

        assert not regressions, (
            f"Field regressions >10% in v2: {', '.join(regressions)}"
        )
