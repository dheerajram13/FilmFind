"""
TMDB Data Validator
"""
from datetime import datetime
from typing import Any, Optional

from loguru import logger


class TMDBDataValidator:
    """
    Validates and cleans TMDB data (SRP)
    """

    @staticmethod
    def validate_movie(movie_data: dict[str, Any]) -> bool:
        """
        Validate that movie data has required fields

        Args:
            movie_data: Raw movie data from TMDB

        Returns:
            True if valid, False otherwise
        """

        required_fields = ["id", "title"]

        return all(field in movie_data and movie_data[field] for field in required_fields)

    @staticmethod
    def clean_movie_data(movie_data: dict[str, Any]) -> dict[str, Any]:
        """
        Clean and normalize movie data

        Args:
            movie_data: Raw movie data from TMDB

        Returns:
            Cleaned movie data
        """

        cleaned = {
            "tmdb_id": movie_data.get("id"),
            "media_type": "movie",
            "title": movie_data.get("title", "").strip(),
            "original_title": movie_data.get("original_title", "").strip(),
            "overview": movie_data.get("overview", "").strip(),
            "tagline": movie_data.get("tagline", "").strip(),
            "release_date": TMDBDataValidator._parse_date(movie_data.get("release_date")),
            "runtime": movie_data.get("runtime"),
            "adult": movie_data.get("adult", False),
            "popularity": movie_data.get("popularity", 0.0),
            "vote_average": movie_data.get("vote_average", 0.0),
            "vote_count": movie_data.get("vote_count", 0),
            "original_language": movie_data.get("original_language", ""),
            "poster_path": movie_data.get("poster_path"),
            "backdrop_path": movie_data.get("backdrop_path"),
            "status": movie_data.get("status"),
            "budget": movie_data.get("budget", 0),
            "revenue": movie_data.get("revenue", 0),
            "imdb_id": movie_data.get("imdb_id"),
            "genres": [g["name"] for g in movie_data.get("genres", [])],
            "genre_ids": [g["id"] for g in movie_data.get("genres", [])],
        }

        # Extract keywords if available
        if "keywords" in movie_data:
            cleaned["keywords"] = [
                {"id": kw["id"], "name": kw["name"]}
                for kw in movie_data["keywords"].get("keywords", [])
            ]

        # Extract cast if available
        if "credits" in movie_data:
            cleaned["cast"] = [
                {
                    "id": cast["id"],
                    "name": cast["name"],
                    "character": cast.get("character", ""),
                    "order": cast.get("order", 999),
                    "profile_path": cast.get("profile_path"),
                }
                for cast in movie_data["credits"].get("cast", [])[:10]  # Top 10 cast
            ]

        return cleaned

    @staticmethod
    def validate_tv_show(tv_data: dict[str, Any]) -> bool:
        """
        Validate that TV show data has required fields

        Args:
            tv_data: Raw TV show data from TMDB

        Returns:
            True if valid, False otherwise
        """

        required_fields = ["id", "name"]

        return all(field in tv_data and tv_data[field] for field in required_fields)

    @staticmethod
    def clean_tv_show_data(tv_data: dict[str, Any]) -> dict[str, Any]:
        """
        Clean and normalize TV show data (converts to movie-compatible format)

        Args:
            tv_data: Raw TV show data from TMDB

        Returns:
            Cleaned TV show data (in movie-compatible format)
        """

        cleaned = {
            "tmdb_id": tv_data.get("id"),
            "media_type": "tv",
            "title": tv_data.get("name", "").strip(),  # TV uses 'name' instead of 'title'
            "original_title": tv_data.get("original_name", "").strip(),
            "overview": tv_data.get("overview", "").strip(),
            "tagline": tv_data.get("tagline", "").strip(),
            "release_date": TMDBDataValidator._parse_date(tv_data.get("first_air_date")),  # TV uses 'first_air_date'
            "runtime": tv_data.get("episode_run_time", [None])[0] if tv_data.get("episode_run_time") else None,  # Average episode runtime
            "adult": tv_data.get("adult", False),
            "popularity": tv_data.get("popularity", 0.0),
            "vote_average": tv_data.get("vote_average", 0.0),
            "vote_count": tv_data.get("vote_count", 0),
            "original_language": tv_data.get("original_language", ""),
            "poster_path": tv_data.get("poster_path"),
            "backdrop_path": tv_data.get("backdrop_path"),
            "status": tv_data.get("status"),
            "budget": 0,  # TV shows don't have budget
            "revenue": 0,  # TV shows don't have revenue
            "imdb_id": tv_data.get("external_ids", {}).get("imdb_id") if "external_ids" in tv_data else None,
            "genres": [g["name"] for g in tv_data.get("genres", [])],
            "genre_ids": [g["id"] for g in tv_data.get("genres", [])],
        }

        # Extract keywords if available (TV uses 'results' instead of 'keywords')
        if "keywords" in tv_data:
            cleaned["keywords"] = [
                {"id": kw["id"], "name": kw["name"]}
                for kw in tv_data["keywords"].get("results", [])
            ]

        # Extract cast if available
        if "credits" in tv_data:
            cleaned["cast"] = [
                {
                    "tmdb_id": cast["id"],  # TMDB ID of cast member
                    "name": cast["name"],
                    "character": cast.get("character", ""),
                    "order": cast.get("order", 999),
                    "profile_path": cast.get("profile_path"),
                }
                for cast in tv_data["credits"].get("cast", [])[:10]  # Top 10 cast
            ]

        return cleaned

    @staticmethod
    def _parse_date(date_str: Optional[str]) -> Optional[datetime]:
        """Parse date string to datetime"""

        if not date_str:
            return None
        try:
            return datetime.strptime(date_str, "%Y-%m-%d")
        except ValueError:
            logger.warning(f"Invalid date format: {date_str}")
            return None
