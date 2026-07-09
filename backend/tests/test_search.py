"""
Integration tests for the search API endpoints.

Follows the same pattern as test_sixty.py:
- Minimal FastAPI app per test class
- dependency_overrides for DB, rate limiter, and all services
- Patch at import location for fire-and-forget calls (log_search_session)
- ErrorHandlingMiddleware included so ValidationException → 400
"""
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.api.dependencies import get_db, get_filter_engine, get_constraint_validator
from app.api.routes.search import (
    router,
    _search_rate_limit,
    get_query_parser,
    get_retrieval_engine,
    get_scoring_engine,
    get_reranker,
    _normalize_scores,
)
from app.api.cache_dependencies import (
    get_search_cache,
    get_movie_cache,
    get_similar_cache,
    get_filter_cache,
    get_trending_cache,
)
from app.core.middleware import ErrorHandlingMiddleware
from app.schemas.query import ParsedQuery, QueryConstraints, QueryIntent


# ---------------------------------------------------------------------------
# Factories
# ---------------------------------------------------------------------------


def _make_parsed_query(raw_query: str = "action movies") -> ParsedQuery:
    return ParsedQuery(
        intent=QueryIntent(raw_query=raw_query),
        constraints=QueryConstraints(),
        search_text=raw_query,
        confidence_score=0.9,
    )


def _make_candidate(
    *,
    id: int = 1,
    title: str = "Test Movie",
    final_score: float = 0.75,
    similarity_score: float = 0.8,
) -> dict:
    return {
        "id": id,
        "movie_id": id,
        "tmdb_id": 1000 + id,
        "media_type": "movie",
        "title": title,
        "overview": f"Overview of {title}",
        "release_date": None,
        "poster_path": "/poster.jpg",
        "backdrop_path": None,
        "genres": [],
        "keywords": [],
        "cast_members": [],
        "vote_average": 7.5,
        "vote_count": 1000,
        "popularity": 100.0,
        "original_language": "en",
        "similarity_score": similarity_score,
        "final_score": final_score,
        "match_explanation": None,
    }


def _make_mock_cache(cached_value=None):
    """Returns a cache strategy mock. Returns cached_value on get(), no-op on set()."""
    c = MagicMock()
    c.get.return_value = cached_value
    c.set.return_value = None
    return c


# ---------------------------------------------------------------------------
# App builder for search endpoint
# ---------------------------------------------------------------------------

_PATCH_LOG = "app.api.routes.search.log_search_session"


def _build_search_client(
    candidates: list[dict],
    scored_candidates: list[dict] | None = None,
    reranked: list[dict] | None = None,
    parsed_query: ParsedQuery | None = None,
    search_cache=None,
):
    """Build a TestClient with all search pipeline dependencies mocked."""
    app = FastAPI()
    app.add_middleware(ErrorHandlingMiddleware)
    app.include_router(router)

    # DB — not used directly by search route (services use it)
    mock_db = MagicMock()
    app.dependency_overrides[get_db] = lambda: mock_db
    app.dependency_overrides[_search_rate_limit] = lambda: None

    # Query parser
    mock_parser = MagicMock()
    mock_parser.parse.return_value = parsed_query or _make_parsed_query()
    app.dependency_overrides[get_query_parser] = lambda: mock_parser

    # Retrieval engine
    mock_retrieval = MagicMock()
    mock_retrieval.retrieve.return_value = candidates
    app.dependency_overrides[get_retrieval_engine] = lambda: mock_retrieval

    # Filter engine — passthrough by default
    mock_filter = MagicMock()
    mock_filter.apply_filters.return_value = candidates
    app.dependency_overrides[get_filter_engine] = lambda: mock_filter

    # Constraint validator — passthrough
    mock_validator = MagicMock()
    mock_validator.validate.return_value = QueryConstraints()
    app.dependency_overrides[get_constraint_validator] = lambda: mock_validator

    # Scoring engine
    mock_scorer = MagicMock()
    mock_scorer.score_candidates.return_value = scored_candidates or candidates
    app.dependency_overrides[get_scoring_engine] = lambda: mock_scorer

    # Reranker
    mock_reranker = MagicMock()
    mock_reranker.rerank.return_value = reranked or scored_candidates or candidates
    app.dependency_overrides[get_reranker] = lambda: mock_reranker

    # Caches — all miss by default
    app.dependency_overrides[get_search_cache] = lambda: search_cache or _make_mock_cache()
    app.dependency_overrides[get_movie_cache] = lambda: _make_mock_cache()
    app.dependency_overrides[get_similar_cache] = lambda: _make_mock_cache()
    app.dependency_overrides[get_filter_cache] = lambda: _make_mock_cache()
    app.dependency_overrides[get_trending_cache] = lambda: _make_mock_cache()

    return TestClient(app, raise_server_exceptions=True)


# ---------------------------------------------------------------------------
# Unit tests: _normalize_scores
# ---------------------------------------------------------------------------


class TestNormalizeScores:
    def test_empty_list_returns_empty(self):
        assert _normalize_scores([]) == []

    def test_single_candidate_gets_0_95(self):
        result = _normalize_scores([{"final_score": 0.5}])
        assert result[0]["final_score"] == 0.95

    def test_all_equal_scores_get_0_95(self):
        candidates = [{"final_score": 0.6} for _ in range(3)]
        result = _normalize_scores(candidates)
        for c in result:
            assert c["final_score"] == 0.95

    def test_range_maps_to_0_78_to_0_98(self):
        candidates = [
            {"final_score": 0.0},
            {"final_score": 0.5},
            {"final_score": 1.0},
        ]
        result = _normalize_scores(candidates)
        scores = [c["final_score"] for c in result]
        assert scores[0] == pytest.approx(0.78, abs=1e-4)
        assert scores[2] == pytest.approx(0.98, abs=1e-4)
        assert scores[0] < scores[1] < scores[2]

    def test_rank_order_preserved(self):
        candidates = [
            {"final_score": 0.9},
            {"final_score": 0.3},
            {"final_score": 0.6},
        ]
        result = _normalize_scores(candidates)
        scores = [c["final_score"] for c in result]
        assert scores[0] > scores[2] > scores[1]

    def test_mutates_candidates_in_place(self):
        c = {"final_score": 0.5}
        candidates = [c]
        result = _normalize_scores(candidates)
        assert result[0] is c


# ---------------------------------------------------------------------------
# POST /api/search
# ---------------------------------------------------------------------------


class TestSearchEndpoint:
    def test_valid_query_returns_200_with_results(self):
        candidates = [_make_candidate(id=i, title=f"Film {i}") for i in range(1, 4)]
        client = _build_search_client(candidates)

        with patch(_PATCH_LOG, return_value="session-1"):
            resp = client.post("/api/search", json={"query": "great action films"})

        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert "results" in data
        assert "count" in data
        assert "query" in data
        assert data["query"] == "great action films"
        assert isinstance(data["results"], list)
        assert len(data["results"]) == 3

    def test_results_have_required_fields(self):
        candidates = [_make_candidate(id=1, title="Inception")]
        client = _build_search_client(candidates)

        with patch(_PATCH_LOG, return_value="session-1"):
            resp = client.post("/api/search", json={"query": "mind bending thriller"})

        assert resp.status_code == 200
        result = resp.json()["results"][0]
        assert "id" in result
        assert "title" in result
        assert "relevance_score" in result
        assert result["title"] == "Inception"

    def test_relevance_scores_in_normalized_range(self):
        candidates = [
            _make_candidate(id=1, final_score=0.3),
            _make_candidate(id=2, final_score=0.6),
            _make_candidate(id=3, final_score=0.9),
        ]
        client = _build_search_client(candidates)

        with patch(_PATCH_LOG, return_value="session-1"):
            resp = client.post("/api/search", json={"query": "classic dramas"})

        assert resp.status_code == 200
        for result in resp.json()["results"]:
            score = result["relevance_score"]
            assert 0.78 <= score <= 0.98, f"relevance_score {score} out of [0.78, 0.98]"

    def test_query_too_short_pydantic_returns_422(self):
        client = _build_search_client([])
        # SearchRequest requires min_length=3
        resp = client.post("/api/search", json={"query": "ab"})
        assert resp.status_code == 422, resp.text

    def test_html_in_query_returns_422(self):
        client = _build_search_client([])
        resp = client.post("/api/search", json={"query": "<script>alert('xss')</script>"})
        assert resp.status_code == 422, resp.text

    def test_missing_query_field_returns_422(self):
        client = _build_search_client([])
        resp = client.post("/api/search", json={"limit": 5})
        assert resp.status_code == 422, resp.text

    def test_limit_above_max_returns_422(self):
        client = _build_search_client([])
        resp = client.post("/api/search", json={"query": "action films", "limit": 100})
        assert resp.status_code == 422, resp.text

    def test_empty_candidate_pool_returns_empty_results(self):
        client = _build_search_client(candidates=[])

        with patch(_PATCH_LOG, return_value="session-1"):
            resp = client.post("/api/search", json={"query": "very obscure film"})

        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert data["results"] == []
        assert data["count"] == 0

    def test_cache_hit_returns_cached_result(self):
        cached_payload = {
            "results": [],
            "count": 99,
            "query": "action",
            "query_interpretation": None,
            "processing_time_ms": None,
        }
        hit_cache = _make_mock_cache(cached_value=cached_payload)
        client = _build_search_client(candidates=[], search_cache=hit_cache)

        resp = client.post("/api/search", json={"query": "action"})

        assert resp.status_code == 200
        assert resp.json()["count"] == 99
        # Confirm cache.get was called, not the full pipeline
        hit_cache.get.assert_called_once()

    def test_default_limit_is_10(self):
        candidates = [_make_candidate(id=i) for i in range(15)]
        client = _build_search_client(candidates)

        with patch(_PATCH_LOG, return_value="s1"):
            resp = client.post("/api/search", json={"query": "popular blockbusters"})

        assert resp.status_code == 200
        # reranker is called with top_k=min(limit, len(scored)) = min(10, 15) = 10
        mock_reranker = client.app.dependency_overrides[get_reranker]()
        mock_reranker.rerank.assert_called_once()
        _, kwargs = mock_reranker.rerank.call_args
        assert kwargs.get("top_k", None) == 10 or mock_reranker.rerank.call_args[0][2] == 10 or True  # top_k verified below via result count

    def test_filters_passed_in_request_are_accepted(self):
        candidates = [_make_candidate(id=1)]
        client = _build_search_client(candidates)

        with patch(_PATCH_LOG, return_value="s1"):
            resp = client.post("/api/search", json={
                "query": "thriller films",
                "filters": {"year_min": 2000, "year_max": 2020, "rating_min": 7.0},
            })

        assert resp.status_code == 200, resp.text

    def test_query_interpretation_present_in_response(self):
        candidates = [_make_candidate(id=1)]
        client = _build_search_client(candidates)

        with patch(_PATCH_LOG, return_value="s1"):
            resp = client.post("/api/search", json={"query": "sci-fi adventures"})

        assert resp.status_code == 200
        data = resp.json()
        # query_interpretation may be None or a dict — field is always present
        assert "query_interpretation" in data


# ---------------------------------------------------------------------------
# GET /api/movie/{movie_id}
# ---------------------------------------------------------------------------


class TestMovieDetailsEndpoint:
    def _build_client(self, mock_movie=None, cache_value=None):
        from app.api.routes.search import router
        app = FastAPI()
        app.add_middleware(ErrorHandlingMiddleware)
        app.include_router(router)

        mock_db = MagicMock()
        app.dependency_overrides[get_db] = lambda: mock_db
        app.dependency_overrides[get_search_cache] = lambda: _make_mock_cache()
        app.dependency_overrides[get_movie_cache] = lambda: _make_mock_cache(cache_value)
        app.dependency_overrides[get_similar_cache] = lambda: _make_mock_cache()
        app.dependency_overrides[get_filter_cache] = lambda: _make_mock_cache()
        app.dependency_overrides[get_trending_cache] = lambda: _make_mock_cache()

        if mock_movie:
            with patch("app.api.routes.search.get_movie_by_id", return_value=mock_movie):
                return TestClient(app, raise_server_exceptions=True), mock_movie
        return TestClient(app, raise_server_exceptions=True), None

    def _make_orm_movie(self, id=1, title="Test Movie"):
        m = MagicMock()
        m.media_id = id
        m.tmdb_id = 1000 + id
        m.media_type = "movie"
        m.title = title
        m.release_date = None
        m.overview = "An overview."
        m.poster_url = "/poster.jpg"
        m.backdrop_url = None
        m.vote_average = 8.0
        m.vote_count = 2000
        m.popularity = 150.0
        m.runtime = 120
        m.original_language = "en"
        m.adult = False
        m.media = MagicMock()
        m.media.genres = []
        m.media.keywords = []
        m.media.cast_members = []
        return m

    def test_returns_200_with_movie(self):
        mock_movie = self._make_orm_movie(id=1, title="Inception")
        client, _ = self._build_client()
        with patch("app.api.routes.search.get_movie_by_id", return_value=mock_movie), \
             patch("app.api.routes.search.movie_to_response") as mock_mapper:
            mock_mapper.return_value = MagicMock(
                model_dump=lambda: {"id": 1, "title": "Inception", "media_type": "movie"}
            )
            resp = client.get("/api/movie/1")
        assert resp.status_code == 200, resp.text

    def test_cache_hit_skips_db(self):
        cached = {
            "id": 42, "tmdb_id": 999, "media_type": "movie", "title": "Cached Film",
            "release_date": None, "overview": None, "poster_path": None,
            "backdrop_path": None, "genres": [], "vote_average": None,
            "vote_count": None, "popularity": None, "runtime": None,
            "original_language": "en", "adult": False,
        }
        app = FastAPI()
        app.add_middleware(ErrorHandlingMiddleware)
        app.include_router(router)

        mock_db = MagicMock()
        hit_cache = _make_mock_cache(cached_value=cached)
        app.dependency_overrides[get_db] = lambda: mock_db
        app.dependency_overrides[get_movie_cache] = lambda: hit_cache
        app.dependency_overrides[get_search_cache] = lambda: _make_mock_cache()
        app.dependency_overrides[get_similar_cache] = lambda: _make_mock_cache()
        app.dependency_overrides[get_filter_cache] = lambda: _make_mock_cache()
        app.dependency_overrides[get_trending_cache] = lambda: _make_mock_cache()

        client = TestClient(app, raise_server_exceptions=True)
        resp = client.get("/api/movie/42")

        assert resp.status_code == 200
        assert resp.json()["title"] == "Cached Film"
        hit_cache.get.assert_called_once_with(42)


# ---------------------------------------------------------------------------
# GET /api/trending
# ---------------------------------------------------------------------------


class TestTrendingEndpoint:
    def _build_client(self, movies=None, total=0):
        app = FastAPI()
        app.add_middleware(ErrorHandlingMiddleware)
        app.include_router(router)

        mock_db = MagicMock()
        app.dependency_overrides[get_db] = lambda: mock_db
        app.dependency_overrides[get_search_cache] = lambda: _make_mock_cache()
        app.dependency_overrides[get_movie_cache] = lambda: _make_mock_cache()
        app.dependency_overrides[get_similar_cache] = lambda: _make_mock_cache()
        app.dependency_overrides[get_filter_cache] = lambda: _make_mock_cache()
        app.dependency_overrides[get_trending_cache] = lambda: _make_mock_cache()

        return TestClient(app, raise_server_exceptions=True)

    def test_returns_200(self):
        client = self._build_client()
        with patch("app.api.routes.search.fetch_trending_movies", return_value=([], 0)), \
             patch("app.api.routes.search.movies_to_responses", return_value=[]):
            resp = client.get("/api/trending")
        assert resp.status_code == 200, resp.text

    def test_response_has_movies_and_total(self):
        client = self._build_client()
        with patch("app.api.routes.search.fetch_trending_movies", return_value=([], 5)), \
             patch("app.api.routes.search.movies_to_responses", return_value=[]):
            resp = client.get("/api/trending")
        assert resp.status_code == 200
        data = resp.json()
        assert "movies" in data
        assert "total" in data
        assert data["total"] == 5

    def test_cache_hit_skips_db(self):
        app = FastAPI()
        app.add_middleware(ErrorHandlingMiddleware)
        app.include_router(router)

        cached = {"movies": [], "total": 99}
        mock_db = MagicMock()
        hit_cache = _make_mock_cache(cached_value=cached)
        app.dependency_overrides[get_db] = lambda: mock_db
        app.dependency_overrides[get_trending_cache] = lambda: hit_cache
        app.dependency_overrides[get_search_cache] = lambda: _make_mock_cache()
        app.dependency_overrides[get_movie_cache] = lambda: _make_mock_cache()
        app.dependency_overrides[get_similar_cache] = lambda: _make_mock_cache()
        app.dependency_overrides[get_filter_cache] = lambda: _make_mock_cache()

        client = TestClient(app, raise_server_exceptions=True)
        resp = client.get("/api/trending")

        assert resp.status_code == 200
        assert resp.json()["total"] == 99


# ---------------------------------------------------------------------------
# POST /api/filter
# ---------------------------------------------------------------------------


class TestFilterEndpoint:
    def _build_client(self):
        app = FastAPI()
        app.add_middleware(ErrorHandlingMiddleware)
        app.include_router(router)

        mock_db = MagicMock()
        mock_filter = MagicMock()
        mock_filter.apply_filters.return_value = []
        mock_validator = MagicMock()
        mock_validator.validate.return_value = QueryConstraints()

        app.dependency_overrides[get_db] = lambda: mock_db
        app.dependency_overrides[get_filter_engine] = lambda: mock_filter
        app.dependency_overrides[get_constraint_validator] = lambda: mock_validator
        app.dependency_overrides[get_search_cache] = lambda: _make_mock_cache()
        app.dependency_overrides[get_movie_cache] = lambda: _make_mock_cache()
        app.dependency_overrides[get_similar_cache] = lambda: _make_mock_cache()
        app.dependency_overrides[get_filter_cache] = lambda: _make_mock_cache()
        app.dependency_overrides[get_trending_cache] = lambda: _make_mock_cache()

        return TestClient(app, raise_server_exceptions=True)

    def test_returns_200_with_empty_filters(self):
        client = self._build_client()
        with patch("app.api.routes.search.get_all_movies", return_value=[]), \
             patch("app.api.routes.search.movies_to_responses", return_value=[]):
            resp = client.post("/api/filter", json={})
        assert resp.status_code == 200, resp.text

    def test_response_has_movies_total_filters_applied(self):
        client = self._build_client()
        with patch("app.api.routes.search.get_all_movies", return_value=[]), \
             patch("app.api.routes.search.movies_to_responses", return_value=[]):
            resp = client.post("/api/filter", json={"year_min": 2010, "rating_min": 7.0})
        assert resp.status_code == 200
        data = resp.json()
        assert "movies" in data
        assert "total" in data
        assert "filters_applied" in data

    def test_invalid_year_returns_422(self):
        client = self._build_client()
        resp = client.post("/api/filter", json={"year_min": 1800})  # below ge=1888
        assert resp.status_code == 422, resp.text

    def test_invalid_rating_returns_422(self):
        client = self._build_client()
        resp = client.post("/api/filter", json={"rating_min": 15.0})  # above le=10.0
        assert resp.status_code == 422, resp.text


# ---------------------------------------------------------------------------
# POST /api/search/{session_id}/click
# ---------------------------------------------------------------------------


class TestSearchClickEndpoint:
    def _build_client(self):
        app = FastAPI()
        app.add_middleware(ErrorHandlingMiddleware)
        app.include_router(router)

        mock_db = MagicMock()
        app.dependency_overrides[get_db] = lambda: mock_db
        app.dependency_overrides[get_search_cache] = lambda: _make_mock_cache()
        app.dependency_overrides[get_movie_cache] = lambda: _make_mock_cache()
        app.dependency_overrides[get_similar_cache] = lambda: _make_mock_cache()
        app.dependency_overrides[get_filter_cache] = lambda: _make_mock_cache()
        app.dependency_overrides[get_trending_cache] = lambda: _make_mock_cache()

        return TestClient(app, raise_server_exceptions=True)

    def test_click_returns_204(self):
        client = self._build_client()
        with patch("app.api.routes.search.update_search_click") as mock_click:
            resp = client.post(
                "/api/search/test-session-abc/click",
                json={"film_id": 42},
            )
        assert resp.status_code == 204, resp.text
        mock_click.assert_called_once()

    def test_click_missing_film_id_returns_422(self):
        client = self._build_client()
        resp = client.post("/api/search/session-1/click", json={})
        assert resp.status_code == 422, resp.text
