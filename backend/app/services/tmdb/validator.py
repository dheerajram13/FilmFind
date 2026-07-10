"""TMDB response validator and normaliser."""
from datetime import datetime
from typing import Optional


class TMDBValidator:
    """Validates and normalises raw TMDB API responses into DB-ready dicts."""

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------

    def validate_movie(self, data: dict) -> bool:
        return bool(data and data.get("id") and data.get("title"))

    def validate_tv_show(self, data: dict) -> bool:
        return bool(data and data.get("id") and data.get("name"))

    # ------------------------------------------------------------------
    # Cleaning
    # ------------------------------------------------------------------

    def clean_movie_data(self, data: dict) -> dict:
        return {
            "tmdb_id": data["id"],
            "imdb_id": data.get("imdb_id"),
            "title": data["title"],
            "original_title": data.get("original_title"),
            "overview": data.get("overview") or "",
            "tagline": data.get("tagline") or None,
            "release_date": self._parse_date(data.get("release_date")),
            "status": data.get("status"),
            "adult": bool(data.get("adult", False)),
            "popularity": data.get("popularity"),
            "vote_average": data.get("vote_average"),
            "vote_count": data.get("vote_count"),
            "original_language": data.get("original_language"),
            "runtime": data.get("runtime"),
            "budget": data.get("budget") or 0,
            "revenue": data.get("revenue") or 0,
            "belongs_to_collection": data.get("belongs_to_collection"),
            "production_countries": [
                c["iso_3166_1"] for c in data.get("production_countries", []) if "iso_3166_1" in c
            ],
            "spoken_languages": [
                l["iso_639_1"] for l in data.get("spoken_languages", []) if "iso_639_1" in l
            ],
            "origin_country": data.get("origin_country") or [],
            "production_companies": data.get("production_companies") or [],
            "streaming_providers": self._extract_streaming(data),
            "poster_path": data.get("poster_path"),
            "backdrop_path": data.get("backdrop_path"),
            # Relational fields — linked separately after upsert
            "genres": [g["name"] for g in data.get("genres", []) if g.get("name")],
            "keywords": [
                {"name": k["name"]}
                for k in data.get("keywords", {}).get("keywords", [])
                if k.get("name")
            ],
            "cast": self._extract_cast(data),
        }

    def clean_tv_show_data(self, data: dict) -> dict:
        return {
            "tmdb_id": data["id"],
            # imdb_id comes from external_ids sub-response (appended)
            "imdb_id": data.get("external_ids", {}).get("imdb_id"),
            "title": data["name"],
            "original_title": data.get("original_name"),
            "overview": data.get("overview") or "",
            "tagline": data.get("tagline") or None,
            "release_date": self._parse_date(data.get("first_air_date")),
            "status": data.get("status"),
            "adult": bool(data.get("adult", False)),
            "popularity": data.get("popularity"),
            "vote_average": data.get("vote_average"),
            "vote_count": data.get("vote_count"),
            "original_language": data.get("original_language"),
            "number_of_seasons": data.get("number_of_seasons"),
            "number_of_episodes": data.get("number_of_episodes"),
            "episode_run_time": data.get("episode_run_time") or [],
            "last_air_date": self._parse_date(data.get("last_air_date")),
            "in_production": bool(data.get("in_production", False)),
            "networks": data.get("networks") or [],
            "created_by": data.get("created_by") or [],
            "show_type": data.get("type"),
            "production_countries": [
                c["iso_3166_1"] for c in data.get("production_countries", []) if "iso_3166_1" in c
            ],
            "spoken_languages": [
                l["iso_639_1"] for l in data.get("spoken_languages", []) if "iso_639_1" in l
            ],
            "origin_country": data.get("origin_country") or [],
            "production_companies": data.get("production_companies") or [],
            "streaming_providers": self._extract_streaming(data),
            "poster_path": data.get("poster_path"),
            "backdrop_path": data.get("backdrop_path"),
            # Relational fields — TV keywords use "results" key, not "keywords"
            "genres": [g["name"] for g in data.get("genres", []) if g.get("name")],
            "keywords": [
                {"name": k["name"]}
                for k in data.get("keywords", {}).get("results", [])
                if k.get("name")
            ],
            "cast": self._extract_cast(data),
        }

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _parse_date(self, s: Optional[str]) -> Optional[datetime]:
        if not s:
            return None
        for fmt in ("%Y-%m-%d", "%Y-%m", "%Y"):
            try:
                return datetime.strptime(s, fmt)
            except ValueError:
                continue
        return None

    def _extract_streaming(self, data: dict) -> Optional[dict]:
        """Return the raw watch/providers results dict keyed by country code, or None."""
        providers = data.get("watch/providers", {}).get("results")
        return providers if providers else None

    def _extract_cast(self, data: dict) -> list[dict]:
        """Return top 15 cast members (TMDB order) with normalised field names."""
        cast_raw = data.get("credits", {}).get("cast", [])
        return [
            {
                "tmdb_id": c["id"],
                "name": c["name"],
                "profile_path": c.get("profile_path"),
                "character": c.get("character"),
                "popularity": c.get("popularity"),
            }
            for c in cast_raw[:15]
            if c.get("id") and c.get("name")
        ]
