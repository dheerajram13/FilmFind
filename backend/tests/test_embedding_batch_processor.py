"""Tests for EmbeddingBatchProcessor."""

from unittest.mock import MagicMock, patch

import numpy as np
import pytest

from app.models.movie import Genre, Movie
from app.repositories.movie_repository import MovieRepository
from app.services.embedding_batch_processor import EmbeddingBatchProcessor


@pytest.fixture()
def mock_db_session():
    """Create mock database session."""
    return MagicMock()


@pytest.fixture()
def sample_movies():
    """Create sample movies for testing."""
    movies = []
    for i in range(5):
        movie = Movie(
            id=i + 1,
            tmdb_id=1000 + i,
            title=f"Movie {i}",
            overview=f"Overview for movie {i}",
            original_language="en",
            popularity=50.0 + i,
        )
        movie.genres = [Genre(id=1, name="Action")]
        movies.append(movie)

    return movies


@pytest.fixture()
def processor(mock_db_session):
    """Create batch processor instance."""
    return EmbeddingBatchProcessor(
        db=mock_db_session,
        embedding_batch_size=2,
        db_batch_size=3,
    )


class TestBatchProcessorInit:
    """Tests for EmbeddingBatchProcessor initialization."""

    def test_init_default_params(self, mock_db_session):
        """Test initialization with default parameters."""
        processor = EmbeddingBatchProcessor(db=mock_db_session)

        assert processor.db == mock_db_session
        assert processor.embedding_batch_size == 32
        assert processor.db_batch_size == 100

    def test_init_custom_params(self, mock_db_session):
        """Test initialization with custom parameters."""
        processor = EmbeddingBatchProcessor(
            db=mock_db_session,
            embedding_batch_size=64,
            db_batch_size=200,
        )

        assert processor.embedding_batch_size == 64
        assert processor.db_batch_size == 200

    def test_init_creates_dependencies(self, mock_db_session):
        """Test that initialization creates required dependencies."""
        processor = EmbeddingBatchProcessor(db=mock_db_session)

        assert isinstance(processor.movie_repo, MovieRepository)
        assert processor.embedding_service is not None
        assert processor.text_preprocessor is not None


class TestProcessBatch:
    """Tests for _process_batch method."""

    def test_process_batch_success(self, processor, sample_movies):
        """Test successful batch processing."""
        with patch.object(processor.text_preprocessor, "batch_preprocess") as mock_preprocess:
            with patch.object(
                processor.embedding_service, "generate_embeddings_batch"
            ) as mock_generate:
                with patch.object(processor, "_store_embedding") as mock_store:
                    # Mock preprocessed text
                    mock_preprocess.return_value = [
                        (1, "Movie 1 text"),
                        (2, "Movie 2 text"),
                    ]

                    # Mock embeddings
                    mock_generate.return_value = np.random.rand(2, 768)

                    stats = processor._process_batch(sample_movies[:2])

                    assert stats["processed"] == 2
                    assert stats["skipped"] == 0
                    assert stats["failed"] == 0

                    # Check methods were called
                    mock_preprocess.assert_called_once()
                    mock_generate.assert_called_once()
                    assert mock_store.call_count == 2
                    processor.db.commit.assert_called_once()

    def test_process_batch_skips_invalid(self, processor, sample_movies):
        """Test that invalid movies are skipped."""
        with patch.object(processor.text_preprocessor, "batch_preprocess") as mock_preprocess:
            # Only 1 movie passes validation (out of 3)
            mock_preprocess.return_value = [(1, "Movie 1 text")]

            with patch.object(
                processor.embedding_service, "generate_embeddings_batch"
            ) as mock_generate:
                mock_generate.return_value = np.random.rand(1, 768)

                with patch.object(processor, "_store_embedding"):
                    stats = processor._process_batch(sample_movies[:3])

                    assert stats["processed"] == 1
                    assert stats["skipped"] == 2  # 2 movies skipped
                    assert stats["failed"] == 0

    def test_process_batch_handles_embedding_error(self, processor, sample_movies):
        """Test handling of embedding generation errors."""
        with patch.object(processor.text_preprocessor, "batch_preprocess") as mock_preprocess:
            mock_preprocess.return_value = [(1, "Movie 1 text")]

            with patch.object(
                processor.embedding_service, "generate_embeddings_batch"
            ) as mock_generate:
                # Simulate embedding error
                mock_generate.side_effect = Exception("Embedding failed")

                stats = processor._process_batch(sample_movies[:1])

                assert stats["processed"] == 0
                assert stats["failed"] == 1
                processor.db.rollback.assert_called_once()

    def test_process_batch_handles_storage_error(self, processor, sample_movies):
        """Test handling of storage errors."""
        with patch.object(processor.text_preprocessor, "batch_preprocess") as mock_preprocess:
            mock_preprocess.return_value = [(1, "Movie 1 text"), (2, "Movie 2 text")]

            with patch.object(
                processor.embedding_service, "generate_embeddings_batch"
            ) as mock_generate:
                mock_generate.return_value = np.random.rand(2, 768)

                with patch.object(processor, "_store_embedding") as mock_store:
                    # First succeeds, second fails
                    mock_store.side_effect = [None, Exception("Storage failed")]

                    stats = processor._process_batch(sample_movies[:2])

                    assert stats["processed"] == 1
                    assert stats["failed"] == 1


class TestStoreEmbedding:
    """Tests for _store_embedding method."""

    def test_store_embedding(self, processor):
        """Test storing embedding for a movie."""
        with patch.object(processor.movie_repo, "update") as mock_update:
            embedding = np.random.rand(768)

            processor._store_embedding(movie_id=1, embedding=embedding)

            # Check update was called with correct data
            mock_update.assert_called_once()
            call_args = mock_update.call_args[0]

            assert call_args[0] == 1  # movie_id
            assert "embedding" in call_args[1]
            assert "has_embedding" in call_args[1]
            assert call_args[1]["has_embedding"] is True
            assert len(call_args[1]["embedding"]) == 768


class TestGetProgress:
    """Tests for get_progress method."""

    def test_get_progress(self, processor):
        """Test getting progress statistics."""
        with patch.object(processor.movie_repo, "count") as mock_count:
            with patch.object(processor.movie_repo, "count_movies_with_embeddings") as mock_with:
                with patch.object(
                    processor.movie_repo, "count_movies_without_embeddings"
                ) as mock_without:
                    mock_count.return_value = 1000
                    mock_with.return_value = 600
                    mock_without.return_value = 400

                    progress = processor.get_progress()

                    assert progress["total"] == 1000
                    assert progress["completed"] == 600
                    assert progress["remaining"] == 400
                    assert progress["percentage"] == 60.0

    def test_get_progress_empty_database(self, processor):
        """Test progress with empty database."""
        with patch.object(processor.movie_repo, "count") as mock_count:
            with patch.object(processor.movie_repo, "count_movies_with_embeddings") as mock_with:
                with patch.object(
                    processor.movie_repo, "count_movies_without_embeddings"
                ) as mock_without:
                    mock_count.return_value = 0
                    mock_with.return_value = 0
                    mock_without.return_value = 0

                    progress = processor.get_progress()

                    assert progress["total"] == 0
                    assert progress["completed"] == 0
                    assert progress["remaining"] == 0
                    assert progress["percentage"] == 0.0


class TestValidateEmbeddings:
    """Tests for validate_embeddings method."""

    def test_validate_embeddings_all_valid(self, processor):
        """Test validation when all embeddings are valid."""
        # Create movies with valid embeddings
        movies = []
        for i in range(5):
            movie = Movie(id=i + 1, tmdb_id=1000 + i, title=f"Movie {i}")
            movie.embedding_vector = np.random.rand(768).tolist()
            movies.append(movie)

        with patch.object(processor.movie_repo, "get_movies_with_embeddings") as mock_get:
            mock_get.return_value = movies

            results = processor.validate_embeddings(sample_size=5)

            assert results["checked"] == 5
            assert results["valid"] == 5
            assert results["invalid"] == 0
            assert len(results["errors"]) == 0

    def test_validate_embeddings_wrong_dimensions(self, processor):
        """Test validation detects wrong dimensions."""
        movie = Movie(id=1, tmdb_id=1000, title="Movie 1")
        movie.embedding_vector = np.random.rand(512).tolist()  # Wrong dimension

        with patch.object(processor.movie_repo, "get_movies_with_embeddings") as mock_get:
            mock_get.return_value = [movie]

            results = processor.validate_embeddings(sample_size=1)

            assert results["checked"] == 1
            assert results["valid"] == 0
            assert results["invalid"] == 1
            assert "768" in results["errors"][0]

    def test_validate_embeddings_not_list(self, processor):
        """Test validation detects non-list embeddings."""
        movie = Movie(id=1, tmdb_id=1000, title="Movie 1")
        movie.embedding_vector = "not a list"

        with patch.object(processor.movie_repo, "get_movies_with_embeddings") as mock_get:
            mock_get.return_value = [movie]

            results = processor.validate_embeddings(sample_size=1)

            assert results["checked"] == 1
            assert results["valid"] == 0
            assert results["invalid"] == 1
            assert "not a list" in results["errors"][0]

    def test_validate_embeddings_non_numeric(self, processor):
        """Test validation detects non-numeric values."""
        movie = Movie(id=1, tmdb_id=1000, title="Movie 1")
        embedding = [0.5] * 767 + ["not a number"]
        movie.embedding_vector = embedding

        with patch.object(processor.movie_repo, "get_movies_with_embeddings") as mock_get:
            mock_get.return_value = [movie]

            results = processor.validate_embeddings(sample_size=1)

            assert results["checked"] == 1
            assert results["valid"] == 0
            assert results["invalid"] == 1
            assert "non-numeric" in results["errors"][0]
