"""TMDB API v3 client."""
import time
from typing import Any

import requests
from loguru import logger

from app.core.config import settings

_BASE = "https://api.themoviedb.org/3"
_RATE_DELAY = 0.3  # 40 req/10 s limit → safe at ~3 req/s


class TMDBClient:
    """Thin wrapper around the TMDB v3 REST API."""

    def __init__(self) -> None:
        self._session = requests.Session()
        # api_key and language are merged into every request automatically
        self._session.params.update({"api_key": settings.TMDB_API_KEY, "language": "en-US"})

    def _get(self, path: str, params: dict[str, Any] | None = None) -> dict | None:
        try:
            resp = self._session.get(f"{_BASE}{path}", params=params or {}, timeout=10)
            resp.raise_for_status()
            time.sleep(_RATE_DELAY)
            return resp.json()
        except requests.HTTPError as exc:
            logger.warning(f"TMDB HTTP {exc.response.status_code} — {path}")
        except Exception as exc:
            logger.warning(f"TMDB request failed {path}: {exc}")
        return None

    def get_movie(self, tmdb_id: int) -> dict | None:
        """Full movie details including credits, keywords, and streaming providers."""
        return self._get(
            f"/movie/{tmdb_id}",
            {"append_to_response": "credits,keywords,watch/providers"},
        )

    def get_tv_show(self, tmdb_id: int) -> dict | None:
        """Full TV show details including credits, keywords, external IDs, and streaming providers."""
        return self._get(
            f"/tv/{tmdb_id}",
            {"append_to_response": "credits,keywords,external_ids,watch/providers"},
        )

    def discover_movies(
        self,
        genre_id: int,
        page: int = 1,
        min_vote_count: int = 300,
        min_vote_average: float = 6.0,
    ) -> dict | None:
        """Discover movies by genre with quality floors, sorted by popularity."""
        return self._get("/discover/movie", {
            "with_genres": genre_id,
            "page": page,
            "sort_by": "popularity.desc",
            "vote_count.gte": min_vote_count,
            "vote_average.gte": min_vote_average,
            "include_adult": "false",
        })

    def discover_tv(
        self,
        genre_id: int,
        page: int = 1,
        min_vote_count: int = 100,
        min_vote_average: float = 6.0,
    ) -> dict | None:
        """Discover TV shows by genre with quality floors, sorted by popularity."""
        return self._get("/discover/tv", {
            "with_genres": genre_id,
            "page": page,
            "sort_by": "popularity.desc",
            "vote_count.gte": min_vote_count,
            "vote_average.gte": min_vote_average,
            "include_adult": "false",
        })
