"""
Popularity score update job.

Updates popularity scores for all movies from TMDB daily.
"""

from sqlalchemy.orm import Session

from app.models.media import Movie
from app.services.TMDB.tmdb_service import TMDBService
from app.utils.job_utils import JobStats, batch_process, execute_with_db
from app.utils.logger import get_logger


logger = get_logger(__name__)


def update_popularity_scores() -> dict:
    """
    Update popularity scores for all movies.

    Fetches latest popularity data from TMDB and updates database.

    Returns:
        Dictionary with update statistics
    """
    return execute_with_db(
        _update_popularity_logic,
        "Popularity score update job",
        {"movies_updated": 0, "movies_skipped": 0},
    )


def _update_popularity_logic(db: Session, stats: JobStats) -> None:
    """
    Core logic for popularity update job.

    Args:
        db: Database session
        stats: Job statistics tracker
    """
    tmdb_service = TMDBService()

    # Get all movies from database
    movies = db.query(Movie).all()
    logger.info(f"Updating popularity for {len(movies)} movies")

    # Process movies in batches
    batch_process(
        items=movies,
        process_func=lambda movie, db, stats: _update_movie_popularity(  # noqa: ARG005
            movie, tmdb_service, stats
        ),
        db=db,
        stats=stats,
        batch_size=100,
        batch_stat_key="movies_updated",
    )


def _update_movie_popularity(movie: Movie, tmdb_service: TMDBService, stats: JobStats) -> None:
    """
    Update popularity for a single movie.

    Args:
        movie: Movie to update
        tmdb_service: TMDB service instance
        stats: Job statistics tracker
    """
    # Fetch latest movie data from TMDB
    movie_data = tmdb_service.get_movie_details(movie.tmdb_id)

    if movie_data:
        # Update popularity score
        old_popularity = movie.popularity
        movie.popularity = movie_data.get("popularity", movie.popularity)

        # Also update vote average and count
        movie.vote_average = movie_data.get("vote_average", movie.vote_average)
        movie.vote_count = movie_data.get("vote_count", movie.vote_count)

        if abs((movie.popularity or 0) - (old_popularity or 0)) > 10:
            logger.debug(
                f"Significant popularity change for '{movie.title}': "
                f"{old_popularity} → {movie.popularity}"
            )
    else:
        stats.increment("movies_skipped")
