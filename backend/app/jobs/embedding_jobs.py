"""
Embedding generation and index rebuild jobs.

Weekly jobs to regenerate embeddings and rebuild FAISS index.
"""

from sqlalchemy.orm import Session

from app.models.media import Movie
from app.services.embedding_service import EmbeddingService
from app.services.vector_search import VectorSearchService
from app.utils.job_utils import JobStats, batch_process, execute_with_db
from app.utils.logger import get_logger


logger = get_logger(__name__)


def regenerate_embeddings() -> dict:
    """
    Regenerate embeddings for all movies.

    Runs weekly to update embeddings for new movies and ensure consistency.

    Returns:
        Dictionary with regeneration statistics
    """
    return execute_with_db(
        _regenerate_embeddings_logic,
        "Embedding regeneration job",
        {"movies_processed": 0, "embeddings_generated": 0},
    )


def _regenerate_embeddings_logic(db: Session, stats: JobStats) -> None:
    """
    Core logic for embedding regeneration job.

    Args:
        db: Database session
        stats: Job statistics tracker
    """
    embedding_service = EmbeddingService()

    # Get all movies without embeddings
    movies_without_embeddings = db.query(Movie).filter(Movie.embedding.is_(None)).all()

    logger.info(f"Found {len(movies_without_embeddings)} movies without embeddings")

    # Generate embeddings in batches
    batch_process(
        items=movies_without_embeddings,
        process_func=lambda movie, db, stats: _generate_movie_embedding(  # noqa: ARG005
            movie, embedding_service, stats
        ),
        db=db,
        stats=stats,
        batch_size=32,
        batch_stat_key="movies_processed",
    )


def _generate_movie_embedding(
    movie: Movie, embedding_service: EmbeddingService, stats: JobStats
) -> None:
    """
    Generate embedding for a single movie.

    Args:
        movie: Movie to generate embedding for
        embedding_service: Embedding service instance
        stats: Job statistics tracker
    """
    if movie.overview:
        embedding = embedding_service.generate_embedding(movie.overview)
        movie.embedding = embedding
        stats.increment("embeddings_generated")


def rebuild_index() -> dict:
    """
    Rebuild FAISS vector index from database.

    Runs weekly after embedding regeneration to ensure index is up-to-date.

    Returns:
        Dictionary with rebuild statistics
    """
    return execute_with_db(
        _rebuild_index_logic,
        "Vector index rebuild job",
        {"total_movies": 0, "indexed_movies": 0},
    )


def _rebuild_index_logic(db: Session, stats: JobStats) -> None:
    """
    Core logic for index rebuild job.

    Args:
        db: Database session
        stats: Job statistics tracker
    """
    vector_search_service = VectorSearchService()

    # Get all movies with embeddings
    movies = db.query(Movie).filter(Movie.embedding.isnot(None)).all()
    stats.set("total_movies", len(movies))

    logger.info(f"Rebuilding index for {len(movies)} movies")

    # Rebuild the index
    vector_search_service.build_index(movies)
    stats.set("indexed_movies", len(movies))
