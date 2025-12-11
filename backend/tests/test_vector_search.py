"""
Tests for FAISS vector search service - Module 1.4

Tests cover:
- Index building and management
- Similarity search
- Index persistence (save/load)
- Error handling
- Performance characteristics
- Singleton pattern for get_vector_search_service()
"""

from pathlib import Path
import tempfile

import numpy as np
import pytest

from app.services.exceptions import (
    IndexBuildError,
    IndexNotFoundError,
    IndexNotInitializedError,
    IndexValidationError,
)
from app.services.vector_search import VectorSearchService, get_vector_search_service


@pytest.fixture()
def temp_paths():
    """Create temporary paths for test index files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir_path = Path(tmpdir)
        yield {
            "index_path": str(tmpdir_path / "test_index.bin"),
            "metadata_path": str(tmpdir_path / "test_metadata.pkl"),
        }


@pytest.fixture()
def sample_embeddings():
    """Create sample embeddings for testing."""
    np.random.seed(42)
    # 100 vectors of dimension 768
    embeddings = np.random.randn(100, 768).astype(np.float32)
    # Normalize for cosine similarity
    norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
    embeddings = embeddings / norms
    # Ensure C-contiguous array for FAISS
    embeddings = np.ascontiguousarray(embeddings)
    movie_ids = list(range(1, 101))  # Movie IDs 1-100
    return embeddings, movie_ids


@pytest.fixture()
def vector_service(temp_paths):
    """Create VectorSearchService with temporary paths."""
    return VectorSearchService(
        dimension=768,
        index_path=temp_paths["index_path"],
        metadata_path=temp_paths["metadata_path"],
    )


class TestVectorSearchServiceInitialization:
    """Test service initialization and properties."""

    def test_initialization(self, temp_paths):
        """Test service initialization with custom paths."""
        service = VectorSearchService(
            dimension=768,
            index_path=temp_paths["index_path"],
            metadata_path=temp_paths["metadata_path"],
        )

        assert service.dimension == 768
        assert service.index_path == Path(temp_paths["index_path"])
        assert service.metadata_path == Path(temp_paths["metadata_path"])
        assert service.size == 0
        assert not service.is_trained

    def test_default_initialization(self):
        """Test service initialization with default config paths."""
        service = VectorSearchService()

        assert service.dimension == 768  # From config
        assert service.size == 0
        assert not service.is_trained

    def test_index_access_before_build_raises_error(self, vector_service):
        """Test that accessing index before building raises error."""
        with pytest.raises(IndexNotInitializedError, match="Index not initialized"):
            _ = vector_service.index


class TestIndexBuilding:
    """Test FAISS index building functionality."""

    def test_build_index_basic(self, vector_service, sample_embeddings):
        """Test basic index building."""
        embeddings, movie_ids = sample_embeddings

        vector_service.build_index(embeddings, movie_ids)

        assert vector_service.is_trained
        assert vector_service.size == 100
        assert len(vector_service._id_map) == 100

    def test_build_index_with_custom_params(self, vector_service, sample_embeddings):
        """Test index building with custom HNSW parameters."""
        embeddings, movie_ids = sample_embeddings

        vector_service.build_index(embeddings, movie_ids, m=64, ef_construction=400)

        assert vector_service.is_trained
        assert vector_service.size == 100

    def test_build_index_mismatched_lengths_raises_error(self, vector_service):
        """Test that mismatched embeddings and IDs raise error."""
        embeddings = np.random.randn(100, 768).astype(np.float32)
        movie_ids = list(range(1, 51))  # Only 50 IDs for 100 embeddings

        with pytest.raises(IndexValidationError, match="must match"):
            vector_service.build_index(embeddings, movie_ids)

    def test_build_index_wrong_dimension_raises_error(self, vector_service):
        """Test that wrong embedding dimension raises error."""
        embeddings = np.random.randn(100, 512).astype(np.float32)  # Wrong dimension
        movie_ids = list(range(1, 101))

        with pytest.raises(IndexValidationError, match="dimension"):
            vector_service.build_index(embeddings, movie_ids)

    def test_build_index_empty_raises_error(self, vector_service):
        """Test that empty embeddings list raises error."""
        embeddings = np.array([]).reshape(0, 768).astype(np.float32)
        movie_ids = []

        with pytest.raises(Exception):  # FAISS may raise different errors
            vector_service.build_index(embeddings, movie_ids)


class TestSimilaritySearch:
    """Test vector similarity search functionality."""

    def test_search_basic(self, vector_service, sample_embeddings):
        """Test basic similarity search."""
        embeddings, movie_ids = sample_embeddings
        vector_service.build_index(embeddings, movie_ids)

        # Search with first embedding
        query = embeddings[0]
        results = vector_service.search(query, k=5)

        assert len(results) == 5
        assert all(isinstance(r, tuple) and len(r) == 2 for r in results)
        # First result should be the query itself (ID 1)
        assert results[0][0] == 1
        # Similarity should be very high (cosine similarity ~1.0 for same vector)
        assert results[0][1] > 0.99

    def test_search_returns_correct_ids(self, vector_service, sample_embeddings):
        """Test that search returns correct movie IDs."""
        embeddings, movie_ids = sample_embeddings
        vector_service.build_index(embeddings, movie_ids)

        query = embeddings[50]  # Movie ID 51
        results = vector_service.search(query, k=3)

        # All returned IDs should be in our movie_ids list
        for movie_id, _ in results:
            assert movie_id in movie_ids

    def test_search_similarity_scores_descending(self, vector_service, sample_embeddings):
        """Test that results are sorted by similarity (descending)."""
        embeddings, movie_ids = sample_embeddings
        vector_service.build_index(embeddings, movie_ids)

        query = embeddings[25]
        results = vector_service.search(query, k=10)

        # Check that similarities are in descending order
        similarities = [score for _, score in results]
        assert similarities == sorted(similarities, reverse=True)

    def test_search_with_different_k_values(self, vector_service, sample_embeddings):
        """Test search with different k values."""
        embeddings, movie_ids = sample_embeddings
        vector_service.build_index(embeddings, movie_ids)

        query = embeddings[10]

        # Test different k values
        for k in [1, 5, 10, 20, 50]:
            results = vector_service.search(query, k=k)
            assert len(results) == k

    def test_search_k_larger_than_index_size(self, vector_service, sample_embeddings):
        """Test that k larger than index size returns all vectors."""
        embeddings, movie_ids = sample_embeddings
        vector_service.build_index(embeddings, movie_ids)

        query = embeddings[0]
        results = vector_service.search(query, k=200)  # Larger than index size (100)

        # Should return all 100 vectors
        assert len(results) == 100

    def test_search_wrong_dimension_raises_error(self, vector_service, sample_embeddings):
        """Test that query with wrong dimension raises error."""
        embeddings, movie_ids = sample_embeddings
        vector_service.build_index(embeddings, movie_ids)

        wrong_query = np.random.randn(512).astype(np.float32)  # Wrong dimension

        with pytest.raises(IndexValidationError, match="dimension"):
            vector_service.search(wrong_query, k=5)

    def test_search_without_index_raises_error(self, vector_service):
        """Test that search without building index raises error."""
        query = np.random.randn(768).astype(np.float32)

        with pytest.raises(IndexNotInitializedError, match="Index not initialized"):
            vector_service.search(query, k=5)

    def test_search_with_different_ef_search(self, vector_service, sample_embeddings):
        """Test search with different ef_search parameters."""
        embeddings, movie_ids = sample_embeddings
        vector_service.build_index(embeddings, movie_ids)

        query = embeddings[10]

        # Test different ef_search values
        for ef_search in [10, 50, 100, 200]:
            results = vector_service.search(query, k=5, ef_search=ef_search)
            assert len(results) == 5
            # Results should be consistent (top result is query itself)
            assert results[0][0] == 11  # Movie ID 11 (index 10 + 1)


class TestIndexPersistence:
    """Test index save and load functionality."""

    def test_save_index(self, vector_service, sample_embeddings):
        """Test saving index to disk."""
        embeddings, movie_ids = sample_embeddings
        vector_service.build_index(embeddings, movie_ids)

        vector_service.save_index()

        # Check that files were created
        assert vector_service.index_path.exists()
        assert vector_service.metadata_path.exists()

    def test_save_without_building_raises_error(self, vector_service):
        """Test that saving without building index raises error."""
        with pytest.raises(IndexBuildError, match="Cannot save"):
            vector_service.save_index()

    def test_load_index(self, vector_service, sample_embeddings):
        """Test loading index from disk."""
        embeddings, movie_ids = sample_embeddings

        # Build and save
        vector_service.build_index(embeddings, movie_ids)
        vector_service.save_index()

        # Create new service and load
        new_service = VectorSearchService(
            dimension=768,
            index_path=str(vector_service.index_path),
            metadata_path=str(vector_service.metadata_path),
        )
        new_service.load_index()

        # Check that index was loaded correctly
        assert new_service.is_trained
        assert new_service.size == 100
        assert len(new_service._id_map) == 100

    def test_load_nonexistent_index_raises_error(self, vector_service):
        """Test that loading nonexistent index raises error."""
        with pytest.raises(IndexNotFoundError):
            vector_service.load_index()

    def test_save_and_load_preserves_search_results(self, vector_service, sample_embeddings):
        """Test that saved/loaded index produces same search results."""
        embeddings, movie_ids = sample_embeddings

        # Build index and search
        vector_service.build_index(embeddings, movie_ids)
        query = embeddings[20]
        original_results = vector_service.search(query, k=10)

        # Save and load
        vector_service.save_index()
        new_service = VectorSearchService(
            dimension=768,
            index_path=str(vector_service.index_path),
            metadata_path=str(vector_service.metadata_path),
        )
        new_service.load_index()

        # Search again
        loaded_results = new_service.search(query, k=10)

        # Results should be identical
        assert len(original_results) == len(loaded_results)
        for (id1, score1), (id2, score2) in zip(original_results, loaded_results, strict=True):
            assert id1 == id2
            assert abs(score1 - score2) < 1e-5  # Float comparison tolerance


class TestIndexInfo:
    """Test index information methods."""

    def test_get_index_info_before_build(self, vector_service):
        """Test get_index_info before building index."""
        info = vector_service.get_index_info()

        assert info["is_trained"] is False
        assert info["size"] == 0
        assert info["dimension"] == 768
        assert info["index_type"] is None

    def test_get_index_info_after_build(self, vector_service, sample_embeddings):
        """Test get_index_info after building index."""
        embeddings, movie_ids = sample_embeddings
        vector_service.build_index(embeddings, movie_ids)

        info = vector_service.get_index_info()

        assert info["is_trained"] is True
        assert info["size"] == 100
        assert info["dimension"] == 768
        assert info["index_type"] == "IndexHNSWFlat"

    def test_clear_index(self, vector_service, sample_embeddings):
        """Test clearing index from memory."""
        embeddings, movie_ids = sample_embeddings
        vector_service.build_index(embeddings, movie_ids)

        # Clear index
        vector_service.clear_index()

        # Check that index is cleared
        assert vector_service.size == 0
        assert not vector_service.is_trained
        assert len(vector_service._id_map) == 0

        # Should not be able to search after clearing
        query = embeddings[0]
        with pytest.raises(IndexNotInitializedError):
            vector_service.search(query, k=5)


class TestPerformance:
    """Test performance characteristics."""

    def test_search_performance_reasonable(self, vector_service, sample_embeddings):
        """Test that search performance is reasonable."""
        import time

        embeddings, movie_ids = sample_embeddings
        vector_service.build_index(embeddings, movie_ids)

        query = embeddings[50]

        # Measure search time
        start = time.time()
        for _ in range(100):
            vector_service.search(query, k=10)
        elapsed = time.time() - start

        avg_time_ms = (elapsed / 100) * 1000

        # Average search should be under 10ms for 100 vectors
        # (This is a very conservative threshold)
        assert avg_time_ms < 10.0, f"Search too slow: {avg_time_ms:.2f}ms"

    def test_build_index_performance(self, vector_service, sample_embeddings):
        """Test that index building completes in reasonable time."""
        import time

        embeddings, movie_ids = sample_embeddings

        start = time.time()
        vector_service.build_index(embeddings, movie_ids)
        elapsed = time.time() - start

        # Building index for 100 vectors should be fast (<1 second)
        assert elapsed < 1.0, f"Index building too slow: {elapsed:.2f}s"


class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_single_vector_index(self, vector_service):
        """Test index with only one vector."""
        embeddings = np.random.randn(1, 768).astype(np.float32)
        movie_ids = [1]

        vector_service.build_index(embeddings, movie_ids)

        query = embeddings[0]
        results = vector_service.search(query, k=1)

        assert len(results) == 1
        assert results[0][0] == 1

    def test_large_k_value(self, vector_service, sample_embeddings):
        """Test search with very large k value."""
        embeddings, movie_ids = sample_embeddings
        vector_service.build_index(embeddings, movie_ids)

        query = embeddings[0]
        results = vector_service.search(query, k=10000)  # Much larger than index

        # Should return all vectors in index
        assert len(results) == 100

    def test_zero_vector_query(self, vector_service, sample_embeddings):
        """Test search with zero vector."""
        embeddings, movie_ids = sample_embeddings
        vector_service.build_index(embeddings, movie_ids)

        query = np.zeros(768, dtype=np.float32)
        results = vector_service.search(query, k=5)

        # Should still return results (though they may not be meaningful)
        assert len(results) == 5


class TestSingletonPattern:
    """Test the singleton pattern for get_vector_search_service()."""

    def test_get_vector_search_service_returns_instance(self):
        """Test that get_vector_search_service returns a VectorSearchService instance."""
        import app.services.vector_search as vs_module

        # Reset singleton for clean test
        vs_module._vector_search_instance = None

        service = get_vector_search_service()

        assert isinstance(service, VectorSearchService)
        assert service.dimension == 768  # Default from config

    def test_get_vector_search_service_singleton(self):
        """Test that get_vector_search_service returns the same instance."""
        import app.services.vector_search as vs_module

        # Reset singleton for clean test
        vs_module._vector_search_instance = None

        service1 = get_vector_search_service()
        service2 = get_vector_search_service()

        # Should return the exact same instance
        assert service1 is service2

    def test_singleton_persists_across_calls(self):
        """Test that singleton instance persists state across multiple calls."""
        import app.services.vector_search as vs_module

        # Reset singleton for clean test
        vs_module._vector_search_instance = None

        service1 = get_vector_search_service()
        original_dimension = service1.dimension

        # Get service again
        service2 = get_vector_search_service()

        # Should have same dimension (same instance)
        assert service2.dimension == original_dimension
        assert service1 is service2

    def test_singleton_multiple_calls_efficiency(self):
        """Test that singleton doesn't create new instances on repeated calls."""
        import app.services.vector_search as vs_module

        # Reset singleton for clean test
        vs_module._vector_search_instance = None

        # Get service multiple times
        services = [get_vector_search_service() for _ in range(10)]

        # All should be the same instance
        first_service = services[0]
        for service in services[1:]:
            assert service is first_service

    def test_singleton_reset_cleanup(self):
        """Test cleanup: Reset singleton after test to avoid side effects."""
        import app.services.vector_search as vs_module

        # This test ensures we can reset the singleton for testing purposes
        vs_module._vector_search_instance = None

        service1 = get_vector_search_service()
        assert service1 is not None

        # Reset
        vs_module._vector_search_instance = None

        # New call should create a new instance
        service2 = get_vector_search_service()
        assert service2 is not None

        # Note: In actual usage, these would be the same instance
        # This test just verifies we can reset for testing purposes
