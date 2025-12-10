"""Tests for EmbeddingService."""

import numpy as np
import pytest

from app.services.embedding_service import EmbeddingService, get_embedding_service


@pytest.fixture()
def embedding_service():
    """Create embedding service instance."""
    return EmbeddingService()


class TestEmbeddingServiceInit:
    """Tests for EmbeddingService initialization."""

    def test_init_default_model(self):
        """Test initialization with default model."""
        service = EmbeddingService()
        assert service.model_name == "sentence-transformers/all-mpnet-base-v2"
        assert service._model is None  # Lazy loading

    def test_init_custom_model(self):
        """Test initialization with custom model name."""
        service = EmbeddingService(model_name="custom/model")
        assert service.model_name == "custom/model"

    def test_model_lazy_loading(self, embedding_service):
        """Test that model is only loaded when accessed."""
        assert embedding_service._model is None

        # Access model property
        model = embedding_service.model

        # Now should be loaded
        assert embedding_service._model is not None
        assert model == embedding_service._model


class TestGenerateEmbedding:
    """Tests for generate_embedding method."""

    def test_generate_single_embedding(self, embedding_service):
        """Test generating embedding for single text."""
        text = "A science fiction thriller about dreams"
        embedding = embedding_service.generate_embedding(text)

        # Check shape
        assert isinstance(embedding, np.ndarray)
        assert embedding.shape == (768,)

        # Check normalized (L2 norm should be ~1.0)
        norm = np.linalg.norm(embedding)
        assert abs(norm - 1.0) < 0.01

    def test_generate_embedding_not_normalized(self, embedding_service):
        """Test generating embedding without normalization."""
        text = "Action movie"
        embedding = embedding_service.generate_embedding(text, normalize=False)

        # Should still be 768-dimensional
        assert embedding.shape == (768,)

        # But not normalized
        norm = np.linalg.norm(embedding)
        assert norm > 1.0  # Un-normalized embeddings have larger norms

    def test_generate_embedding_different_texts(self, embedding_service):
        """Test that different texts produce different embeddings."""
        text1 = "Action movie with explosions"
        text2 = "Romantic comedy with humor"

        emb1 = embedding_service.generate_embedding(text1)
        emb2 = embedding_service.generate_embedding(text2)

        # Embeddings should be different
        assert not np.array_equal(emb1, emb2)

        # But same shape
        assert emb1.shape == emb2.shape == (768,)

    def test_generate_embedding_similar_texts(self, embedding_service):
        """Test that similar texts produce similar embeddings."""
        text1 = "Science fiction movie about space"
        text2 = "Sci-fi film set in outer space"

        emb1 = embedding_service.generate_embedding(text1)
        emb2 = embedding_service.generate_embedding(text2)

        # Compute similarity (cosine for normalized vectors)
        similarity = np.dot(emb1, emb2)

        # Should be quite similar (> 0.7)
        assert similarity > 0.7


class TestGenerateEmbeddingsBatch:
    """Tests for generate_embeddings_batch method."""

    def test_batch_generate_multiple_texts(self, embedding_service):
        """Test batch generation for multiple texts."""
        texts = [
            "Action movie",
            "Romantic comedy",
            "Horror film",
            "Science fiction",
        ]

        embeddings = embedding_service.generate_embeddings_batch(texts, show_progress=False)

        # Check shape
        assert embeddings.shape == (4, 768)

        # Check all are normalized
        for embedding in embeddings:
            norm = np.linalg.norm(embedding)
            assert abs(norm - 1.0) < 0.01

    def test_batch_generate_single_text(self, embedding_service):
        """Test batch generation with single text."""
        texts = ["Single movie"]

        embeddings = embedding_service.generate_embeddings_batch(texts, show_progress=False)

        assert embeddings.shape == (1, 768)

    def test_batch_generate_custom_batch_size(self, embedding_service):
        """Test batch generation with custom batch size."""
        texts = [f"Movie {i}" for i in range(10)]

        embeddings = embedding_service.generate_embeddings_batch(
            texts, batch_size=2, show_progress=False
        )

        assert embeddings.shape == (10, 768)

    def test_batch_generate_consistency(self, embedding_service):
        """Test that batch and single generation produce same results."""
        text = "Consistent test text"

        # Generate individually
        single_emb = embedding_service.generate_embedding(text)

        # Generate in batch
        batch_emb = embedding_service.generate_embeddings_batch([text], show_progress=False)[0]

        # Should be very close (allowing for tiny numerical differences)
        np.testing.assert_array_almost_equal(single_emb, batch_emb, decimal=6)


class TestComputeSimilarity:
    """Tests for compute_similarity method."""

    def test_compute_similarity_identical(self, embedding_service):
        """Test similarity of identical embeddings."""
        text = "Test movie"
        emb = embedding_service.generate_embedding(text)

        similarity = embedding_service.compute_similarity(emb, emb)

        # Should be 1.0 (identical)
        assert abs(similarity - 1.0) < 0.01

    def test_compute_similarity_different(self, embedding_service):
        """Test similarity of different embeddings."""
        emb1 = embedding_service.generate_embedding("Action movie")
        emb2 = embedding_service.generate_embedding("Romantic comedy")

        similarity = embedding_service.compute_similarity(emb1, emb2)

        # Should be less than 1.0
        assert similarity < 1.0
        assert similarity > -1.0  # Should be in valid range

    def test_compute_similarity_range(self, embedding_service):
        """Test that similarity is in [-1, 1] range."""
        texts = ["Movie A", "Movie B", "Movie C"]
        embeddings = embedding_service.generate_embeddings_batch(texts, show_progress=False)

        for i in range(len(embeddings)):
            for j in range(len(embeddings)):
                similarity = embedding_service.compute_similarity(embeddings[i], embeddings[j])
                assert -1.0 <= similarity <= 1.0


class TestGetModelInfo:
    """Tests for get_model_info method."""

    def test_get_model_info(self, embedding_service):
        """Test getting model information."""
        info = embedding_service.get_model_info()

        assert "model_name" in info
        assert "embedding_dim" in info
        assert "device" in info
        assert "max_seq_length" in info

        assert info["model_name"] == "sentence-transformers/all-mpnet-base-v2"
        assert info["embedding_dim"] == 768
        assert isinstance(info["max_seq_length"], int)


class TestContextManager:
    """Tests for context manager protocol."""

    def test_context_manager_usage(self):
        """Test using service as context manager."""
        with EmbeddingService() as service:
            # Model should be loaded
            assert service._model is not None

            # Should be able to generate embeddings
            embedding = service.generate_embedding("Test")
            assert embedding.shape == (768,)


class TestSingleton:
    """Tests for get_embedding_service singleton."""

    def test_singleton_returns_same_instance(self):
        """Test that singleton returns same instance."""
        service1 = get_embedding_service()
        service2 = get_embedding_service()

        assert service1 is service2

    def test_singleton_model_loaded_once(self):
        """Test that model is only loaded once across calls."""
        service1 = get_embedding_service()
        _ = service1.model  # Load the model

        service2 = get_embedding_service()

        # Should be same instance with model already loaded
        assert service2._model is not None
