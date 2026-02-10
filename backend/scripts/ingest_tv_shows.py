#!/usr/bin/env python
"""
TMDB TV shows ingestion script for FilmFind.

This script fetches TV show data from TMDB API and stores it in the database.

Usage:
    # Ingest popular TV shows (10 pages = ~200 shows)
    python scripts/ingest_tv_shows.py --max-pages 10

    # Ingest top-rated TV shows
    python scripts/ingest_tv_shows.py --max-pages 5
"""
import argparse
import sys
from pathlib import Path

from loguru import logger
from sqlalchemy.exc import IntegrityError
from tqdm import tqdm

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.database import SessionLocal
from app.models.media import Movie, Genre, Keyword, Cast
from app.services.TMDB.tmdb_service import TMDBService


def ingest_tv_shows_to_db(max_pages: int = 10):
    """
    Ingest TV shows directly to database

    Args:
        max_pages: Maximum pages to fetch
    """
    logger.info(f"Starting TV show ingestion (max {max_pages} pages)")

    tmdb_service = TMDBService()
    db = SessionLocal()

    try:
        # Fetch popular TV shows
        logger.info("Fetching popular TV shows from TMDB...")
        tv_shows = []

        for page in range(1, max_pages + 1):
            logger.info(f"Fetching page {page}/{max_pages}")
            response = tmdb_service.client.get_popular_tv_shows(page=page)

            if not response or "results" not in response:
                logger.warning(f"Failed to fetch page {page}")
                break

            # Process each TV show
            for tv_show in tqdm(response["results"], desc=f"Processing page {page}"):
                # Fetch full details for each show
                full_tv_show = tmdb_service.client.get_tv_show(tv_show["id"])

                if not full_tv_show:
                    logger.warning(f"Failed to fetch TV show {tv_show['id']}")
                    continue

                if not tmdb_service.validator.validate_tv_show(full_tv_show):
                    logger.warning(f"Invalid TV show data for {tv_show['id']}")
                    continue

                cleaned_data = tmdb_service.validator.clean_tv_show_data(full_tv_show)
                tv_shows.append(cleaned_data)

        logger.info(f"Fetched {len(tv_shows)} TV shows, saving to database...")

        # Save to database
        saved_count = 0
        skipped_count = 0

        for tv_show_data in tqdm(tv_shows, desc="Saving to database"):
            try:
                # Check if already exists
                existing = (
                    db.query(Movie)
                    .filter(Movie.tmdb_id == tv_show_data["tmdb_id"])
                    .first()
                )

                if existing:
                    logger.debug(f"TV show {tv_show_data['title']} already exists, skipping")
                    skipped_count += 1
                    continue

                # Create Movie (TV show) object
                movie = Movie(
                    tmdb_id=tv_show_data["tmdb_id"],
                    media_type="tv",
                    title=tv_show_data["title"],
                    original_title=tv_show_data.get("original_title"),
                    overview=tv_show_data.get("overview"),
                    tagline=tv_show_data.get("tagline"),
                    release_date=tv_show_data.get("release_date"),
                    runtime=tv_show_data.get("runtime"),
                    adult=tv_show_data.get("adult", False),
                    popularity=tv_show_data.get("popularity"),
                    vote_average=tv_show_data.get("vote_average"),
                    vote_count=tv_show_data.get("vote_count"),
                    original_language=tv_show_data.get("original_language"),
                    poster_path=tv_show_data.get("poster_path"),
                    backdrop_path=tv_show_data.get("backdrop_path"),
                    status=tv_show_data.get("status"),
                    budget=0,
                    revenue=0,
                    imdb_id=tv_show_data.get("imdb_id"),
                )

                # Add genres
                for genre_name in tv_show_data.get("genres", []):
                    genre = db.query(Genre).filter(Genre.name == genre_name).first()
                    if not genre:
                        genre = Genre(name=genre_name)
                        db.add(genre)
                    movie.genres.append(genre)

                # Add keywords
                for keyword_data in tv_show_data.get("keywords", []):
                    keyword = (
                        db.query(Keyword)
                        .filter(Keyword.name == keyword_data["name"])
                        .first()
                    )
                    if not keyword:
                        keyword = Keyword(name=keyword_data["name"])
                        db.add(keyword)
                    movie.keywords.append(keyword)

                # Add cast
                for cast_data in tv_show_data.get("cast", []):
                    cast = db.query(Cast).filter(Cast.tmdb_id == cast_data["tmdb_id"]).first()
                    if not cast:
                        cast = Cast(
                            tmdb_id=cast_data["tmdb_id"],
                            name=cast_data["name"],
                            profile_path=cast_data.get("profile_path"),
                        )
                        db.add(cast)
                    movie.cast_members.append(cast)

                db.add(movie)
                db.commit()
                saved_count += 1

            except IntegrityError as e:
                logger.warning(f"Integrity error for {tv_show_data['title']}: {e}")
                db.rollback()
                skipped_count += 1
            except Exception as e:
                logger.error(f"Error saving {tv_show_data.get('title', 'unknown')}: {e}")
                db.rollback()
                skipped_count += 1

        logger.success(
            f"✓ Ingestion completed! Saved: {saved_count}, Skipped: {skipped_count}"
        )

    finally:
        db.close()


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description="Ingest TV shows from TMDB API to database"
    )
    parser.add_argument(
        "--max-pages",
        type=int,
        default=10,
        help="Maximum pages to fetch (default: 10, ~200 TV shows)",
    )

    args = parser.parse_args()

    logger.info("=" * 60)
    logger.info("TMDB TV Shows Ingestion Script")
    logger.info("=" * 60)

    ingest_tv_shows_to_db(max_pages=args.max_pages)


if __name__ == "__main__":
    main()
