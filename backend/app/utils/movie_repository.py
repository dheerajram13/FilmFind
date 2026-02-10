"""
Movie repository utilities.

Provides DRY utilities for common movie/media database queries.
"""

from sqlalchemy.orm import Session

from app.api.exceptions import NotFoundException
from app.models.media import Media, Movie


def get_movie_by_id(db: Session, movie_id: int) -> Movie:
    """
    Get movie by ID or raise NotFoundException.

    Args:
        db: Database session
        movie_id: Database ID of the movie

    Returns:
        Movie model instance

    Raises:
        NotFoundException: If movie not found
    """
    movie = db.query(Movie).filter(Movie.id == movie_id).first()

    if not movie:
        msg = f"Movie with ID {movie_id} not found"
        raise NotFoundException(
            msg,
            resource_type="movie",
        )

    return movie


def get_all_movies(db: Session) -> list[Movie]:
    """
    Get all movies from database.

    Args:
        db: Database session

    Returns:
        List of all Movie model instances
    """
    return db.query(Movie).all()


def get_trending_movies(db: Session, skip: int = 0, limit: int = 20) -> tuple[list[Media], int]:
    """
    Get trending media (movies and TV shows) sorted by popularity.

    Args:
        db: Database session
        skip: Number of records to skip
        limit: Maximum number of records to return

    Returns:
        Tuple of (list of media items, total count)
    """
    media = (
        db.query(Media)
        .filter(Media.popularity.is_not(None))
        .order_by(Media.popularity.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )

    total = db.query(Media).filter(Media.popularity.is_not(None)).count()

    return media, total
