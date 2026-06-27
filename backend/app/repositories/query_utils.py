"""
Movie repository utilities — common single-query helpers.
"""

from sqlalchemy.orm import Session

from app.api.exceptions import NotFoundException
from app.models.media import Media, Movie, TVShow


def get_movie_by_id(db: Session, movie_id: int) -> Movie:
    """
    Get a Movie by its media_id (public-facing ID) or raise NotFoundException.
    """
    movie = db.query(Movie).filter(Movie.media_id == movie_id).first()
    if not movie:
        raise NotFoundException(
            f"Movie with ID {movie_id} not found",
            resource_type="movie",
        )
    return movie


def get_all_movies(db: Session) -> list[Movie]:
    return db.query(Movie).all()


def get_trending_movies(db: Session, skip: int = 0, limit: int = 20) -> tuple[list[Movie | TVShow], int]:
    """
    Get trending content (movies + TV shows) sorted by popularity.

    Returns a tuple of (items, total_count).
    """
    movies = (
        db.query(Movie)
        .filter(Movie.popularity.is_not(None))
        .order_by(Movie.popularity.desc())
        .all()
    )
    shows = (
        db.query(TVShow)
        .filter(TVShow.popularity.is_not(None))
        .order_by(TVShow.popularity.desc())
        .all()
    )

    all_items = sorted(movies + shows, key=lambda x: x.popularity or 0, reverse=True)
    total = len(all_items)
    return all_items[skip: skip + limit], total
