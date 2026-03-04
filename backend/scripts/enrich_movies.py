#!/usr/bin/env python
"""
Enrich existing movies with genres, keywords, and cast from TMDB.

Runs against movies that have no genre associations — fetches full details
from TMDB and populates the media_genres, media_cast, media_keywords tables.

Usage:
    python scripts/enrich_movies.py
"""
import sys
from pathlib import Path

from loguru import logger
from sqlalchemy.exc import IntegrityError
from tqdm import tqdm

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.database import SessionLocal
from app.models.media import Cast, Genre, Keyword, Movie, media_genres
from app.services.TMDB.tmdb_service import TMDBService


def enrich_movies():
    tmdb = TMDBService()
    db = SessionLocal()
    enriched, skipped, failed = 0, 0, 0

    try:
        # Find movies with no genre associations
        movies_without_genres = (
            db.query(Movie)
            .filter(~Movie.genres.any())
            .order_by(Movie.popularity.desc())
            .all()
        )

        logger.info(f"Found {len(movies_without_genres)} movies missing genre/cast/keyword data")

        for movie in tqdm(movies_without_genres, desc="Enriching movies"):
            try:
                full_data = tmdb.client.get_movie(movie.tmdb_id)
                if not full_data:
                    logger.warning(f"No TMDB data for {movie.title} (tmdb_id={movie.tmdb_id})")
                    skipped += 1
                    continue

                cleaned = tmdb.validator.clean_movie_data(full_data)

                # Add genres
                for genre_name in cleaned.get("genres", []):
                    genre = db.query(Genre).filter(Genre.name == genre_name).first()
                    if not genre:
                        genre = Genre(name=genre_name)
                        db.add(genre)
                        db.flush()
                    if genre not in movie.genres:
                        movie.genres.append(genre)

                # Add keywords
                for kw in cleaned.get("keywords", []):
                    keyword = db.query(Keyword).filter(Keyword.name == kw["name"]).first()
                    if not keyword:
                        keyword = Keyword(name=kw["name"])
                        db.add(keyword)
                        db.flush()
                    if keyword not in movie.keywords:
                        movie.keywords.append(keyword)

                # Add cast
                added_cast_ids = set()
                for cast_data in cleaned.get("cast", []):
                    cast_tmdb_id = cast_data.get("tmdb_id") or cast_data.get("id")
                    if not cast_tmdb_id or cast_tmdb_id in added_cast_ids:
                        continue
                    cast = db.query(Cast).filter(Cast.tmdb_id == cast_tmdb_id).first()
                    if not cast:
                        cast = Cast(
                            tmdb_id=cast_tmdb_id,
                            name=cast_data["name"],
                            profile_path=cast_data.get("profile_path"),
                        )
                        db.add(cast)
                        db.flush()
                    if cast not in movie.cast_members:
                        movie.cast_members.append(cast)
                    added_cast_ids.add(cast_tmdb_id)

                db.commit()
                enriched += 1
                logger.debug(
                    f"Enriched: {movie.title} — "
                    f"{len(movie.genres)} genres, {len(movie.cast_members)} cast"
                )

            except (IntegrityError, Exception) as e:
                logger.warning(f"Failed to enrich {movie.title}: {e}")
                db.rollback()
                failed += 1

        logger.success(f"Done — Enriched={enriched}, Skipped={skipped}, Failed={failed}")

    finally:
        db.close()


if __name__ == "__main__":
    enrich_movies()
