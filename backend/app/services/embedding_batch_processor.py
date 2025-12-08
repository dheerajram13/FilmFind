"""
Batch processor for generating embeddings for large movie datasets.

This module handles efficient batch processing of movie embeddings:
- Processes movies in configurable batch sizes
- Updates database with generated embeddings
- Tracks progress and supports resume functionality
- Error handling and logging

Design Patterns:
- Batch Processing: Process data in chunks for efficiency
- Repository Pattern: Clean separation from database
- Single Responsibility: Only handles batch embedding generation
"""

import logging
from typing import Any

import numpy as np
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.movie import Movie
from app.repositories.movie_repository import MovieRepository
from app.services.embedding_service import get_embedding_service
from app.services.text_preprocessor import TextPreprocessor


logger = logging.getLogger(__name__)


class EmbeddingBatchProcessor:
    """
    Batch processor for generating and storing movie embeddings.

    This service orchestrates the entire embedding generation pipeline:
    1. Fetch movies without embeddings
    2. Preprocess movie text
    3. Generate embeddings in batches
    4. Store embeddings in database

    Example:
        ```python
        processor = EmbeddingBatchProcessor(db_session)
        stats = processor.process_all_movies(batch_size=100)
        print(f"Processed {stats['processed']} movies")
        ```
    """

    def __init__(
        self,
        db: Session,
        embedding_batch_size: int = settings.DEFAULT_EMBEDDING_BATCH_SIZE,
        db_batch_size: int = settings.DEFAULT_DB_BATCH_SIZE,
    ) -> None:
        """
        Initialize batch processor.

        Args:
            db: Database session
            embedding_batch_size: Batch size for embedding generation (default from config)
                                 Smaller batches for GPU memory constraints
            db_batch_size: Batch size for database fetching (default from config)
                          Can be larger since we're just reading
        """
        if embedding_batch_size <= 0:
            raise ValueError("embedding_batch_size must be positive")
        if db_batch_size <= 0:
            raise ValueError("db_batch_size must be positive")

        self.db = db
        self.embedding_batch_size = embedding_batch_size
        self.db_batch_size = db_batch_size
        self.movie_repo = MovieRepository(db)
        self.embedding_service = get_embedding_service()
        self.text_preprocessor = TextPreprocessor()

    def process_all_movies(
        self,
        limit: int | None = None,
        skip_existing: bool = True,
    ) -> dict[str, Any]:
        """
        Process all movies and generate embeddings.

        Args:
            limit: Optional limit on number of movies to process
            skip_existing: Skip movies that already have embeddings (default: True)

        Returns:
            Statistics dictionary with processing results

        Example:
            ```python
            processor = EmbeddingBatchProcessor(db_session)

            # Process all movies without embeddings
            stats = processor.process_all_movies()

            # Process only 1000 movies
            stats = processor.process_all_movies(limit=1000)

            # Regenerate all embeddings (including existing)
            stats = processor.process_all_movies(skip_existing=False)
            ```
        """
        logger.info("Starting batch embedding generation...")

        stats = {
            "total_movies": 0,
            "processed": 0,
            "skipped": 0,
            "failed": 0,
            "batches": 0,
        }

        # Get total count for progress tracking
        if skip_existing:
            total_count = self.movie_repo.count_movies_without_embeddings()
            logger.info(f"Found {total_count} movies without embeddings")
        else:
            total_count = self.movie_repo.count()
            logger.info(f"Found {total_count} total movies")

        stats["total_movies"] = total_count

        # Apply limit if specified
        if limit:
            total_count = min(total_count, limit)
            logger.info(f"Processing limited to {total_count} movies")

        # Process in database batches
        offset = 0
        while offset < total_count:
            batch_limit = min(self.db_batch_size, total_count - offset)

            # Fetch batch of movies
            if skip_existing:
                movies = self.movie_repo.get_movies_without_embeddings(
                    limit=batch_limit, offset=offset
                )
            else:
                movies = self.movie_repo.get_all(skip=offset, limit=batch_limit)

            if not movies:
                break

            # Process this batch
            batch_stats = self._process_batch(movies)
            stats["processed"] += batch_stats["processed"]
            stats["skipped"] += batch_stats["skipped"]
            stats["failed"] += batch_stats["failed"]
            stats["batches"] += 1

            logger.info(
                f"Batch {stats['batches']}: Processed {batch_stats['processed']}, "
                f"Skipped {batch_stats['skipped']}, Failed {batch_stats['failed']} "
                f"({offset + len(movies)}/{total_count})"
            )

            offset += len(movies)

        logger.info(f"Batch processing complete: {stats}")
        return stats

    def _process_batch(self, movies: list[Movie]) -> dict:
        """
        Process a single batch of movies.

        Args:
            movies: List of Movie entities to process

        Returns:
            Batch statistics dictionary
        """
        stats = {"processed": 0, "skipped": 0, "failed": 0}

        # Preprocess all movies in batch
        preprocessed = self.text_preprocessor.batch_preprocess(movies)

        if not preprocessed:
            logger.warning(f"No valid text from {len(movies)} movies")
            stats["skipped"] = len(movies)
            return stats

        # Extract movie IDs and texts
        movie_ids = [item[0] for item in preprocessed]
        texts = [item[1] for item in preprocessed]

        # Track which movies were skipped during preprocessing
        skipped_count = len(movies) - len(preprocessed)
        stats["skipped"] = skipped_count

        try:
            # Generate embeddings for all texts in batch
            embeddings = self.embedding_service.generate_embeddings_batch(
                texts,
                batch_size=self.embedding_batch_size,
                normalize=True,
                show_progress=False,  # Disable tqdm for cleaner logging
            )

            # Store embeddings in database
            for movie_id, embedding in zip(movie_ids, embeddings):
                try:
                    self._store_embedding(movie_id, embedding)
                    stats["processed"] += 1
                except Exception as e:
                    logger.error(f"Failed to store embedding for movie {movie_id}: {e}")
                    stats["failed"] += 1

            # Commit all updates in this batch
            self.db.commit()

        except Exception as e:
            logger.error(f"Batch embedding generation failed: {e}")
            stats["failed"] = len(preprocessed)
            self.db.rollback()

        return stats

    def _store_embedding(self, movie_id: int, embedding: np.ndarray) -> None:
        """
        Store embedding for a single movie.

        Args:
            movie_id: Movie ID
            embedding: 768-dimensional embedding vector
        """
        # Convert numpy array to list for JSON storage
        embedding_list = embedding.tolist()

        # Update movie with embedding and metadata
        self.movie_repo.update_embedding(
            movie_id=movie_id,
            embedding=embedding_list,
            model_name=self.embedding_service.model_name,
        )

    def get_progress(self) -> dict:
        """
        Get current progress of embedding generation.

        Returns:
            Progress statistics

        Example:
            ```python
            processor = EmbeddingBatchProcessor(db_session)
            progress = processor.get_progress()
            print(f"{progress['completed']}/{progress['total']} movies embedded")
            print(f"Progress: {progress['percentage']:.1f}%")
            ```
        """
        total = self.movie_repo.count()
        with_embeddings = self.movie_repo.count_movies_with_embeddings()
        without_embeddings = self.movie_repo.count_movies_without_embeddings()

        return {
            "total": total,
            "completed": with_embeddings,
            "remaining": without_embeddings,
            "percentage": (with_embeddings / total * 100) if total > 0 else 0.0,
        }

    def reprocess_failed(self) -> dict:
        """
        Reprocess movies that may have failed in previous runs.

        This is useful for recovering from interruptions or errors.

        Returns:
            Processing statistics

        Example:
            ```python
            processor = EmbeddingBatchProcessor(db_session)
            stats = processor.reprocess_failed()
            print(f"Reprocessed {stats['processed']} failed movies")
            ```
        """
        logger.info("Reprocessing movies without embeddings...")
        return self.process_all_movies(skip_existing=True)

    def validate_embeddings(self, sample_size: int = 100) -> dict:
        """
        Validate that stored embeddings are correct.

        Args:
            sample_size: Number of random movies to validate

        Returns:
            Validation results

        Example:
            ```python
            processor = EmbeddingBatchProcessor(db_session)
            results = processor.validate_embeddings(sample_size=50)
            print(f"Valid: {results['valid']}/{results['checked']}")
            ```
        """
        logger.info(f"Validating {sample_size} random embeddings...")

        # Get sample of movies with embeddings
        movies = self.movie_repo.get_movies_with_embeddings(limit=sample_size)

        results = {"checked": 0, "valid": 0, "invalid": 0, "errors": []}

        for movie in movies:
            results["checked"] += 1

            try:
                # Validate embedding structure
                if not isinstance(movie.embedding_vector, list):
                    results["invalid"] += 1
                    results["errors"].append(f"Movie {movie.id}: embedding_vector is not a list")
                    continue

                if len(movie.embedding_vector) != settings.EXPECTED_EMBEDDING_DIM:
                    results["invalid"] += 1
                    results["errors"].append(
                        f"Movie {movie.id}: embedding has "
                        f"{len(movie.embedding_vector)} dimensions "
                        f"(expected {settings.EXPECTED_EMBEDDING_DIM})"
                    )
                    continue

                # Validate all values are floats
                if not all(isinstance(x, (int, float)) for x in movie.embedding_vector):
                    results["invalid"] += 1
                    results["errors"].append(
                        f"Movie {movie.id}: embedding contains non-numeric values"
                    )
                    continue

                results["valid"] += 1

            except Exception as e:
                results["invalid"] += 1
                results["errors"].append(f"Movie {movie.id}: validation error - {e}")

        logger.info(f"Validation complete: {results['valid']}/{results['checked']} valid")

        return results
