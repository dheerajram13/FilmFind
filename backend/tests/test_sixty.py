"""
Integration tests for the 60-Second Mode endpoint.

Uses FastAPI TestClient with mocked DB, mocked why-reasons generator,
and mocked session logging so no external calls are made.
"""
import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).parent.parent))

# Pre-import mocks are not needed here because Docker has psycopg2 available.
# We just need to mock the external service calls at the right patch targets.

from app.api.dependencies import get_db
from app.api.routes.sixty import router
from app.core.scoring import CONTEXT_MAX_DARKNESS


# ---------------------------------------------------------------------------
# Film factory
# ---------------------------------------------------------------------------


def _make_media(
    *,
    id=1,
    title="Test Film",
    overview="A great test film.",
    media_type="movie",
    darkness_score=4,
    complexity_score=6,
    energy_score=7,
    mood_scores=None,
    context_scores=None,
    craving_scores=None,
    genres=None,
    poster_path="/poster.jpg",
    vote_average=7.5,
    popularity=100.0,
    tmdb_id=12345,
    original_language="en",
    adult=False,
):
    m = MagicMock()
    m.id = id
    m.title = title
    m.overview = overview
    m.media_type = media_type
    m.darkness_score = darkness_score
    m.complexity_score = complexity_score
    m.energy_score = energy_score
    m.mood_scores = mood_scores or {
        "happy": 0.6, "sad": 0.3, "charged": 0.8, "chill": 0.5,
        "adventurous": 0.7, "romantic": 0.4,
    }
    m.context_scores = context_scores or {
        "family": 0.3, "date-night": 0.7, "solo-night": 0.9,
        "friends": 0.8, "movie-night": 0.8, "background": 0.3,
    }
    m.craving_scores = craving_scores or {
        "laugh": 0.3, "cry": 0.4, "mind-blown": 0.8, "thrilled": 0.7,
        "inspired": 0.6, "scared": 0.3, "comforted": 0.4, "wowed": 0.7,
    }
    m.genres = genres or []
    m.poster_path = poster_path
    m.vote_average = vote_average
    m.vote_count = 500
    m.popularity = popularity
    m.tmdb_id = tmdb_id
    m.original_language = original_language
    m.adult = adult
    m.release_date = None
    m.tagline = None
    m.original_title = title
    m.backdrop_path = None
    m.runtime = 120
    m.streaming_providers = None
    m.keywords = []
    m.cast_members = []
    m.narrative_dna = "A thrilling test narrative."
    m.tone_tags = ["tense", "exciting"]
    return m


# ---------------------------------------------------------------------------
# App builder — mock DB + patch external calls
# ---------------------------------------------------------------------------

_WHY_REASONS = ["Great energy", "Perfect mood match", "You will love it"]


def _build_client(mock_films):
    """Build a TestClient with mocked DB returning mock_films.

    The router already defines prefix="/sixty" internally,
    so we mount it without an extra prefix.
    """
    from app.api.routes.sixty import _sixty_rate_limit

    app = FastAPI()
    app.include_router(router)  # router has prefix="/sixty" built-in

    mock_db = MagicMock()
    mock_query = MagicMock()
    mock_query.filter.return_value = mock_query
    mock_query.all.return_value = mock_films
    mock_db.query.return_value = mock_query

    app.dependency_overrides[get_db] = lambda: mock_db
    # Bypass Redis rate limiter so tests don't hit real Redis
    app.dependency_overrides[_sixty_rate_limit] = lambda: None
    return TestClient(app, raise_server_exceptions=True)


# We patch at these two locations for every test:
#   app.api.routes.sixty.generate_why_reasons  — async LLM call
#   app.api.routes.sixty.log_sixty_session     — fire-and-forget DB write
_PATCH_WHY = "app.api.routes.sixty.generate_why_reasons"
_PATCH_LOG = "app.api.routes.sixty.log_sixty_session"


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestSixtyPick:
    def test_valid_request_returns_one_film(self):
        films = [_make_media(id=i, title=f"Film {i}") for i in range(5)]
        client = _build_client(films)

        with patch(_PATCH_WHY, new=AsyncMock(return_value=_WHY_REASONS)), \
             patch(_PATCH_LOG, return_value="session-123"):
            resp = client.post("/sixty/pick", json={
                "mood": "charged",
                "context": "solo-night",
                "craving": "mind-blown",
                "session_token": "test-token",
            })

        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert "film" in data
        assert "match_score" in data
        assert "why_reasons" in data
        assert "session_id" in data

    def test_why_reasons_has_exactly_3_strings(self):
        films = [_make_media()]
        client = _build_client(films)

        with patch(_PATCH_WHY, new=AsyncMock(return_value=["R1", "R2", "R3"])), \
             patch(_PATCH_LOG, return_value="s1"):
            resp = client.post("/sixty/pick", json={
                "mood": "happy",
                "context": "friends",
                "craving": "laugh",
                "session_token": "test",
            })

        assert resp.status_code == 200, resp.text
        reasons = resp.json()["why_reasons"]
        assert isinstance(reasons, list)
        assert len(reasons) == 3
        for r in reasons:
            assert isinstance(r, str) and len(r) > 0

    def test_match_score_in_range_87_to_99(self):
        films = [_make_media()]
        client = _build_client(films)

        with patch(_PATCH_WHY, new=AsyncMock(return_value=_WHY_REASONS)), \
             patch(_PATCH_LOG, return_value="s1"):
            resp = client.post("/sixty/pick", json={
                "mood": "chill",
                "context": "date-night",
                "craving": "comforted",
                "session_token": "test",
            })

        assert resp.status_code == 200, resp.text
        ms = resp.json()["match_score"]
        assert 87 <= ms <= 99, f"match_score {ms} not in [87, 99]"

    def test_family_context_never_picks_dark_film(self):
        """When clean and dark films both available, family context never picks dark ones."""
        clean = _make_media(id=1, title="Clean Film", darkness_score=1)
        dark = _make_media(id=2, title="Dark Film", darkness_score=9)
        client = _build_client([clean, dark])

        chosen_ids = set()
        with patch(_PATCH_WHY, new=AsyncMock(return_value=_WHY_REASONS)), \
             patch(_PATCH_LOG, return_value="s1"):
            for _ in range(30):
                resp = client.post("/sixty/pick", json={
                    "mood": "happy",
                    "context": "family",
                    "craving": "laugh",
                    "session_token": "test",
                })
                assert resp.status_code == 200, resp.text
                chosen_ids.add(resp.json()["film"]["id"])

        assert 2 not in chosen_ids, "Dark film (id=2) should never be chosen for family context"
        assert 1 in chosen_ids, "Clean film (id=1) should always be chosen for family context"

    def test_family_context_fallback_when_all_films_dark(self):
        """When only dark films available, endpoint still returns 200 (last-resort fallback)."""
        dark_films = [_make_media(id=i, darkness_score=8) for i in range(5)]
        client = _build_client(dark_films)

        with patch(_PATCH_WHY, new=AsyncMock(return_value=_WHY_REASONS)), \
             patch(_PATCH_LOG, return_value="s1"):
            resp = client.post("/sixty/pick", json={
                "mood": "happy",
                "context": "family",
                "craving": "laugh",
                "session_token": "test",
            })

        assert resp.status_code == 200, resp.text

    def test_context_darkness_constraint_all_contexts(self):
        """For every context, a film exceeding its max darkness scores 0 and is filtered out."""
        from app.core.scoring import score_film
        for context, max_dark in CONTEXT_MAX_DARKNESS.items():
            if max_dark >= 10:
                continue  # can't go over 10
            dark_film = _make_media(darkness_score=max_dark + 1)
            score = score_film(dark_film, "happy", context, "laugh")
            assert score == 0.0, (
                f"context={context} max_dark={max_dark}: "
                f"film with darkness={max_dark+1} should score 0, got {score}"
            )

    def test_invalid_mood_returns_422(self):
        client = _build_client([_make_media()])
        resp = client.post("/sixty/pick", json={
            "mood": "nonexistent_mood",
            "context": "solo-night",
            "craving": "laugh",
            "session_token": "test",
        })
        assert resp.status_code == 422, resp.text

    def test_invalid_context_returns_422(self):
        client = _build_client([_make_media()])
        resp = client.post("/sixty/pick", json={
            "mood": "happy",
            "context": "nonexistent_context",
            "craving": "laugh",
            "session_token": "test",
        })
        assert resp.status_code == 422, resp.text

    def test_invalid_craving_returns_422(self):
        client = _build_client([_make_media()])
        resp = client.post("/sixty/pick", json={
            "mood": "happy",
            "context": "solo-night",
            "craving": "nonexistent_craving",
            "session_token": "test",
        })
        assert resp.status_code == 422, resp.text

    def test_all_valid_enum_combos_return_200(self):
        """Spot-check one of each valid mood/context/craving."""
        from app.core.scoring import VALID_CONTEXTS, VALID_CRAVINGS, VALID_MOODS
        films = [_make_media(id=i) for i in range(3)]
        client = _build_client(films)

        moods = list(VALID_MOODS)[:2]
        contexts = list(VALID_CONTEXTS)[:2]
        cravings = list(VALID_CRAVINGS)[:2]

        with patch(_PATCH_WHY, new=AsyncMock(return_value=_WHY_REASONS)), \
             patch(_PATCH_LOG, return_value="s1"):
            for mood in moods:
                for context in contexts:
                    for craving in cravings:
                        resp = client.post("/sixty/pick", json={
                            "mood": mood,
                            "context": context,
                            "craving": craving,
                            "session_token": "test",
                        })
                        assert resp.status_code == 200, (
                            f"{mood}/{context}/{craving} → {resp.status_code}: {resp.text}"
                        )


class TestSixtyAction:
    def test_action_returns_204(self):
        """POST /sixty/{session_id}/action returns 204 No Content."""
        app = FastAPI()
        app.include_router(router)  # router has prefix="/sixty" built-in

        mock_db = MagicMock()
        app.dependency_overrides[get_db] = lambda: mock_db

        with patch("app.api.routes.sixty.update_sixty_action", new=AsyncMock(return_value=None)):
            client = TestClient(app)
            resp = client.post("/sixty/test-session-id/action", json={
                "watch_clicked": True,
                "share_clicked": False,
                "retry_clicked": False,
            })

        assert resp.status_code == 204, resp.text
