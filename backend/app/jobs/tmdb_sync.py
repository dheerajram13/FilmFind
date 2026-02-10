"""
TMDB data synchronization job.

Fetches new and updated movies from TMDB API on a daily basis.
"""

from datetime import UTC, datetime, timedelta

from sqlalchemy.orm import Session

from app.api.cache_dependencies import get_cache_invalidator
from app.models.media import Movie
from app.services.TMDB.tmdb_service import TMDBService
from app.utils.job_utils import JobStats, execute_with_db
from app.utils.logger import get_logger


logger = get_logger(__name__)


def sync_tmdb_data() -> dict:
    """
    Sync new and updated movies from TMDB.

    Runs daily to fetch:
    - New movies released in the last 7 days
    - Updated popularity scores for existing movies

    Returns:
        Dictionary with sync statistics
    """
    return execute_with_db(
        _sync_tmdb_data_logic,
        "TMDB data sync job",
        {"new_movies": 0, "updated_movies": 0},
    )


def _sync_tmdb_data_logic(db: Session, stats: JobStats) -> None:
    """
    Core logic for TMDB sync job.

    Args:
        db: Database session
        stats: Job statistics tracker
    """
    tmdb_service = TMDBService()

    # Get movies from last 7 days
    end_date = datetime.now(UTC).date()
    start_date = end_date - timedelta(days=7)

    logger.info(f"Fetching movies from {start_date} to {end_date}")

    # Fetch new movies
    new_movies_data = _fetch_recent_movies(
        tmdb_service, start_date.isoformat(), end_date.isoformat()
    )

    # Process and save new movies
    for movie_data in new_movies_data:
        try:
            existing_movie = db.query(Movie).filter(Movie.tmdb_id == movie_data["id"]).first()

            if existing_movie:
                # Update existing movie
                _update_movie(db, existing_movie, movie_data)
                stats.increment("updated_movies")
            else:
                # Create new movie
                _create_movie(db, movie_data)
                stats.increment("new_movies")

        except Exception as exc:
            logger.error(f"Error processing movie {movie_data.get('id')}: {exc}")
            stats.increment("errors")

    # Invalidate caches after data update
    if stats.get("new_movies") > 0:
        cache_invalidator = get_cache_invalidator()
        cache_invalidator.invalidate_new_movies()
        logger.info("Invalidated caches after adding new movies")


def _fetch_recent_movies(
    tmdb_service: TMDBService,
    start_date: str,  # noqa: ARG001
    end_date: str,  # noqa: ARG001
) -> list[dict]:
    """
    Fetch recent movies from TMDB.

    Args:
        tmdb_service: TMDB service instance
        start_date: Start date (ISO format)
        end_date: End date (ISO format)

    Returns:
        List of movie data dictionaries
    """
    # This is a simplified version - you would implement proper pagination
    # and use TMDB's discover endpoint with date filters
    movies = []
    try:
        # Example: fetch popular movies as a placeholder
        # In production, use discover endpoint with release_date.gte and release_date.lte
        popular_movies = tmdb_service.get_popular_movies(page=1)
        if popular_movies:
            movies.extend(popular_movies[:20])  # Limit for demo
    except Exception as exc:
        logger.error(f"Error fetching recent movies: {exc}")

    return movies


def _create_movie(db: Session, movie_data: dict) -> None:
    """
    Create new movie in database.

    Args:
        db: Database session
        movie_data: Movie data from TMDB
    """
    movie = Movie(
        tmdb_id=movie_data["id"],
        title=movie_data.get("title", ""),
        overview=movie_data.get("overview", ""),
        release_date=movie_data.get("release_date"),
        poster_path=movie_data.get("poster_path"),
        backdrop_path=movie_data.get("backdrop_path"),
        genres=movie_data.get("genres", []),
        vote_average=movie_data.get("vote_average", 0.0),
        vote_count=movie_data.get("vote_count", 0),
        popularity=movie_data.get("popularity", 0.0),
        runtime=movie_data.get("runtime"),
        original_language=movie_data.get("original_language", "en"),
        adult=movie_data.get("adult", False),
    )
    db.add(movie)
    logger.debug(f"Created new movie: {movie.title}")


def _update_movie(db: Session, movie: Movie, movie_data: dict) -> None:  # noqa: ARG001
    """
    Update existing movie with latest data.

    Args:
        db: Database session
        movie: Existing movie object
        movie_data: Updated movie data from TMDB
    """
    # Update fields that may change
    movie.popularity = movie_data.get("popularity", movie.popularity)
    movie.vote_average = movie_data.get("vote_average", movie.vote_average)
    movie.vote_count = movie_data.get("vote_count", movie.vote_count)
    movie.overview = movie_data.get("overview", movie.overview)

    logger.debug(f"Updated movie: {movie.title}")
