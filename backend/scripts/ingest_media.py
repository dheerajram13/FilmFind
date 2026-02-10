#!/usr/bin/env python
"""
Unified media ingestion script for Movies and TV Shows.

Uses the new polymorphic schema (Media → Movie/TVShow).

Usage:
    # Ingest both movies and TV shows (recommended)
    python scripts/ingest_media.py --movies 10 --tv 5

    # Ingest only movies
    python scripts/ingest_media.py --movies 10

    # Ingest only TV shows
    python scripts/ingest_media.py --tv 5
"""
import argparse
import sys
from pathlib import Path

from loguru import logger
from sqlalchemy.exc import IntegrityError
from tqdm import tqdm

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.database import SessionLocal
from app.models.media import Media, Movie, TVShow, Genre, Keyword, Cast
from app.services.TMDB.tmdb_service import TMDBService


def ingest_movies(max_pages: int = 10):
    """Ingest movies using new Movie model."""
    logger.info(f"🎬 Starting movie ingestion ({max_pages} pages)")

    tmdb = TMDBService()
    db = SessionLocal()
    saved, skipped = 0, 0

    try:
        for page in range(1, max_pages + 1):
            logger.info(f"Fetching movie page {page}/{max_pages}")
            response = tmdb.client.get_popular_movies(page=page)

            if not response or "results" not in response:
                logger.warning(f"Failed to fetch page {page}")
                break

            for item in tqdm(response["results"], desc=f"Page {page}"):
                try:
                    # Fetch full details
                    full_data = tmdb.client.get_movie(item["id"])
                    if not full_data or not tmdb.validator.validate_movie(full_data):
                        continue

                    cleaned = tmdb.validator.clean_movie_data(full_data)

                    # Check if exists
                    existing = db.query(Movie).filter(
                        Movie.tmdb_id == cleaned["tmdb_id"]
                    ).first()

                    if existing:
                        skipped += 1
                        continue

                    # Create Movie object
                    movie = Movie(
                        tmdb_id=cleaned["tmdb_id"],
                        media_type="movie",
                        title=cleaned["title"],
                        original_title=cleaned.get("original_title"),
                        overview=cleaned.get("overview"),
                        tagline=cleaned.get("tagline"),
                        release_date=cleaned.get("release_date"),
                        runtime=cleaned.get("runtime"),
                        budget=cleaned.get("budget", 0),
                        revenue=cleaned.get("revenue", 0),
                        adult=cleaned.get("adult", False),
                        popularity=cleaned.get("popularity"),
                        vote_average=cleaned.get("vote_average"),
                        vote_count=cleaned.get("vote_count"),
                        original_language=cleaned.get("original_language"),
                        poster_path=cleaned.get("poster_path"),
                        backdrop_path=cleaned.get("backdrop_path"),
                        status=cleaned.get("status"),
                        imdb_id=cleaned.get("imdb_id"),
                    )

                    # Add genres
                    for genre_name in cleaned.get("genres", []):
                        genre = db.query(Genre).filter(Genre.name == genre_name).first()
                        if not genre:
                            genre = Genre(name=genre_name)
                            db.add(genre)
                        movie.genres.append(genre)

                    # Add keywords
                    for kw in cleaned.get("keywords", []):
                        keyword = db.query(Keyword).filter(Keyword.name == kw["name"]).first()
                        if not keyword:
                            keyword = Keyword(name=kw["name"])
                            db.add(keyword)
                        movie.keywords.append(keyword)

                    # Add cast (deduplicate by tmdb_id)
                    added_cast_ids = set()
                    for cast_data in cleaned.get("cast", []):
                        cast_tmdb_id = cast_data.get("tmdb_id") or cast_data.get("id")

                        # Skip if already added to this movie
                        if cast_tmdb_id in added_cast_ids:
                            continue

                        cast = db.query(Cast).filter(Cast.tmdb_id == cast_tmdb_id).first()
                        if not cast:
                            cast = Cast(
                                tmdb_id=cast_tmdb_id,
                                name=cast_data["name"],
                                profile_path=cast_data.get("profile_path"),
                            )
                            db.add(cast)
                        movie.cast_members.append(cast)
                        added_cast_ids.add(cast_tmdb_id)

                    db.add(movie)
                    db.commit()
                    saved += 1

                except (IntegrityError, Exception) as e:
                    logger.warning(f"Error saving movie {cleaned.get('title', 'unknown')}: {e}")
                    db.rollback()
                    skipped += 1

        logger.success(f"✓ Movies: Saved={saved}, Skipped={skipped}")

    finally:
        db.close()


def ingest_tv_shows(max_pages: int = 5):
    """Ingest TV shows using new TVShow model."""
    logger.info(f"📺 Starting TV show ingestion ({max_pages} pages)")

    tmdb = TMDBService()
    db = SessionLocal()
    saved, skipped = 0, 0

    try:
        for page in range(1, max_pages + 1):
            logger.info(f"Fetching TV page {page}/{max_pages}")
            response = tmdb.client.get_popular_tv_shows(page=page)

            if not response or "results" not in response:
                logger.warning(f"Failed to fetch page {page}")
                break

            for item in tqdm(response["results"], desc=f"Page {page}"):
                try:
                    # Fetch full details
                    full_data = tmdb.client.get_tv_show(item["id"])
                    if not full_data or not tmdb.validator.validate_tv_show(full_data):
                        continue

                    cleaned = tmdb.validator.clean_tv_show_data(full_data)

                    # Check if exists
                    existing = db.query(TVShow).filter(
                        TVShow.tmdb_id == cleaned["tmdb_id"]
                    ).first()

                    if existing:
                        skipped += 1
                        continue

                    # Create TVShow object
                    tv_show = TVShow(
                        tmdb_id=cleaned["tmdb_id"],
                        media_type="tv",
                        title=cleaned["title"],
                        original_title=cleaned.get("original_title"),
                        overview=cleaned.get("overview"),
                        tagline=cleaned.get("tagline"),
                        release_date=cleaned.get("release_date"),
                        adult=cleaned.get("adult", False),
                        popularity=cleaned.get("popularity"),
                        vote_average=cleaned.get("vote_average"),
                        vote_count=cleaned.get("vote_count"),
                        original_language=cleaned.get("original_language"),
                        poster_path=cleaned.get("poster_path"),
                        backdrop_path=cleaned.get("backdrop_path"),
                        status=cleaned.get("status"),
                        imdb_id=cleaned.get("imdb_id"),
                        number_of_seasons=full_data.get("number_of_seasons"),
                        number_of_episodes=full_data.get("number_of_episodes"),
                        episode_run_time=full_data.get("episode_run_time"),
                        first_air_date=cleaned.get("release_date"),
                        last_air_date=tmdb.validator._parse_date(full_data.get("last_air_date")),
                        in_production=full_data.get("in_production", False),
                    )

                    # Add genres, keywords, cast (same as movies)
                    for genre_name in cleaned.get("genres", []):
                        genre = db.query(Genre).filter(Genre.name == genre_name).first()
                        if not genre:
                            genre = Genre(name=genre_name)
                            db.add(genre)
                        tv_show.genres.append(genre)

                    for kw in cleaned.get("keywords", []):
                        keyword = db.query(Keyword).filter(Keyword.name == kw["name"]).first()
                        if not keyword:
                            keyword = Keyword(name=kw["name"])
                            db.add(keyword)
                        tv_show.keywords.append(keyword)

                    # Add cast (deduplicate by tmdb_id)
                    added_cast_ids = set()
                    for cast_data in cleaned.get("cast", []):
                        cast_tmdb_id = cast_data.get("tmdb_id") or cast_data.get("id")

                        # Skip if already added to this TV show
                        if cast_tmdb_id in added_cast_ids:
                            continue

                        cast = db.query(Cast).filter(Cast.tmdb_id == cast_tmdb_id).first()
                        if not cast:
                            cast = Cast(
                                tmdb_id=cast_tmdb_id,
                                name=cast_data["name"],
                                profile_path=cast_data.get("profile_path"),
                            )
                            db.add(cast)
                        tv_show.cast_members.append(cast)
                        added_cast_ids.add(cast_tmdb_id)

                    db.add(tv_show)
                    db.commit()
                    saved += 1

                except (IntegrityError, Exception) as e:
                    logger.warning(f"Error saving TV show {cleaned.get('title', 'unknown')}: {e}")
                    db.rollback()
                    skipped += 1

        logger.success(f"✓ TV Shows: Saved={saved}, Skipped={skipped}")

    finally:
        db.close()


def main():
    parser = argparse.ArgumentParser(description="Ingest movies and TV shows")
    parser.add_argument("--movies", type=int, default=0, help="Number of movie pages (default: 0)")
    parser.add_argument("--tv", type=int, default=0, help="Number of TV pages (default: 0)")

    args = parser.parse_args()

    logger.info("=" * 60)
    logger.info("FilmFind Media Ingestion (Polymorphic Schema)")
    logger.info("=" * 60)

    if args.movies > 0:
        ingest_movies(max_pages=args.movies)

    if args.tv > 0:
        ingest_tv_shows(max_pages=args.tv)

    if args.movies == 0 and args.tv == 0:
        logger.warning("No pages specified. Use --movies N and/or --tv N")


if __name__ == "__main__":
    main()
