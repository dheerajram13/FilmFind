"""
Integration tests for FastAPI routes using TestClient.

Tests:
- /health and /ping — always-public endpoints
- /health/detailed — no API key names leaked in response
- /cache/stats — requires admin auth
- POST /jobs/{id}/run — requires admin auth
- POST /api/search — schema validation (short/long/html queries)
- Admin endpoints (enrich/embed/analytics) — reject unauthenticated requests

Pattern follows tests/test_sixty.py: build a minimal FastAPI app per-router,
override dependencies via app.dependency_overrides, and use TestClient.
"""
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.api.dependencies import get_db
from app.api.routes import health, search, admin


# =============================================================================
# Health endpoints
# =============================================================================


def _build_health_client():
    app = FastAPI()
    app.include_router(health.router)
    mock_db = MagicMock()
    mock_db.execute.return_value = None
    mock_db.commit.return_value = None
    app.dependency_overrides[get_db] = lambda: mock_db
    return TestClient(app, raise_server_exceptions=True)


class TestHealthEndpoints:
    def test_health_returns_200(self):
        client = _build_health_client()
        resp = client.get("/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "healthy"

    def test_ping_returns_pong(self):
        client = _build_health_client()
        resp = client.get("/ping")
        assert resp.status_code == 200
        assert resp.json()["message"] == "pong"

    def test_root_returns_app_info(self):
        client = _build_health_client()
        resp = client.get("/")
        assert resp.status_code == 200
        assert "app" in resp.json()

    def test_detailed_health_no_key_names_leaked(self):
        """Response must not contain specific API key variable names."""
        client = _build_health_client()
        resp = client.get("/health/detailed")
        body = resp.text
        assert "TMDB_API_KEY" not in body
        assert "GROQ_API_KEY" not in body
        assert "GEMINI_API_KEY" not in body
        assert "SUPABASE_SERVICE_ROLE_KEY" not in body

    def test_detailed_health_returns_checks(self):
        client = _build_health_client()
        resp = client.get("/health/detailed")
        assert resp.status_code == 200
        data = resp.json()
        assert "checks" in data
        assert "database" in data["checks"]
        assert "configuration" in data["checks"]


# =============================================================================
# Admin-protected endpoints (cache/stats and jobs)
# =============================================================================


def _build_health_client_with_admin_secret(secret: str):
    """Build health client with a configured ADMIN_SECRET."""
    app = FastAPI()
    app.include_router(health.router)
    mock_db = MagicMock()
    mock_db.execute.return_value = None
    mock_db.commit.return_value = None
    app.dependency_overrides[get_db] = lambda: mock_db

    with patch("app.core.config.settings.ADMIN_SECRET", secret):
        # Return pre-built client; patching must stay active during test
        return TestClient(app, raise_server_exceptions=False), secret


class TestAdminProtectedEndpoints:
    def test_cache_stats_unauthenticated_blocked(self):
        client = _build_health_client()
        resp = client.get("/cache/stats")
        # 401 (wrong token), 503 (no ADMIN_SECRET set), or 422 — all block access
        assert resp.status_code in (401, 403, 422, 503)

    def test_jobs_trigger_unauthenticated_blocked(self):
        client = _build_health_client()
        resp = client.post("/jobs/test-job/run")
        assert resp.status_code in (401, 403, 422, 503)

    def test_cache_stats_with_valid_token_allowed(self):
        """Correct Bearer token for configured ADMIN_SECRET must return 200."""
        app = FastAPI()
        app.include_router(health.router)
        mock_db = MagicMock()
        app.dependency_overrides[get_db] = lambda: mock_db

        with patch("app.api.dependencies.settings") as mock_settings, \
             patch("app.api.routes.health.settings") as hs:
            mock_settings.ADMIN_SECRET = "test-admin-secret"
            hs.CACHE_ENABLED = False
            # Also mock get_cache_manager
            with patch("app.api.routes.health.get_cache_manager") as mock_cm:
                mock_cm.return_value.get_stats.return_value = {"hits": 0, "misses": 0}
                client = TestClient(app, raise_server_exceptions=True)
                resp = client.get(
                    "/cache/stats",
                    headers={"Authorization": "Bearer test-admin-secret"},
                )
        assert resp.status_code == 200


# =============================================================================
# Admin route auth (enrich/embed/analytics)
# =============================================================================


def _build_admin_client():
    app = FastAPI()
    app.include_router(admin.router)
    mock_db = MagicMock()
    app.dependency_overrides[get_db] = lambda: mock_db
    return TestClient(app, raise_server_exceptions=False)


class TestAdminRouteAuth:
    def test_enrich_unauthenticated_blocked(self):
        client = _build_admin_client()
        resp = client.post("/admin/enrich/1")
        assert resp.status_code in (401, 403, 503)

    def test_embed_unauthenticated_blocked(self):
        client = _build_admin_client()
        resp = client.post("/admin/embed/1")
        assert resp.status_code in (401, 403, 503)

    def test_analytics_searches_unauthenticated_blocked(self):
        client = _build_admin_client()
        resp = client.get("/admin/analytics/searches")
        assert resp.status_code in (401, 403, 503)

    def test_analytics_sixty_unauthenticated_blocked(self):
        client = _build_admin_client()
        resp = client.get("/admin/analytics/sixty")
        assert resp.status_code in (401, 403, 503)


# =============================================================================
# Search endpoint schema validation
# =============================================================================


def _build_search_client():
    """Build search router client with rate limiter bypassed."""
    from app.api.routes.search import router as search_router

    app = FastAPI()
    app.include_router(search_router)

    mock_db = MagicMock()
    app.dependency_overrides[get_db] = lambda: mock_db

    # Bypass Redis-based rate limiter so schema tests don't need Redis
    from app.api import dependencies as dep_module
    with patch.object(dep_module, "get_cache_manager") as mock_cm:
        mock_redis = MagicMock()
        pipe = MagicMock()
        pipe.execute.return_value = [None, None, 1, None]
        mock_redis.pipeline.return_value = pipe
        mock_cm.return_value._redis = mock_redis
        return TestClient(app, raise_server_exceptions=False)


class TestSearchSchemaValidation:
    def test_query_too_short_returns_422(self):
        client = _build_search_client()
        resp = client.post("/api/search", json={"query": "hi"})
        assert resp.status_code == 422

    def test_query_one_char_returns_422(self):
        client = _build_search_client()
        resp = client.post("/api/search", json={"query": "a"})
        assert resp.status_code == 422

    def test_query_too_long_returns_422(self):
        client = _build_search_client()
        resp = client.post("/api/search", json={"query": "x" * 501})
        assert resp.status_code == 422

    def test_html_in_query_returns_422(self):
        client = _build_search_client()
        resp = client.post("/api/search", json={"query": "<script>alert(1)</script>"})
        assert resp.status_code == 422

    def test_limit_above_20_returns_422(self):
        client = _build_search_client()
        resp = client.post("/api/search", json={"query": "action movie", "limit": 50})
        assert resp.status_code == 422

    def test_missing_query_returns_422(self):
        client = _build_search_client()
        resp = client.post("/api/search", json={"limit": 5})
        assert resp.status_code == 422
