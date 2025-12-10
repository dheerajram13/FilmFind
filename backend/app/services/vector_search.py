"""
FAISS-based vector search service for semantic movie search.

This module provides high-performance vector similarity search using FAISS:
- HNSW (Hierarchical Navigable Small World) index for fast ANN search
- Persistence and loading of indices
- Top-k similarity search with filtering
- Metadata management for result enrichment

Design Patterns:
- Singleton Pattern: Single index instance shared across app
- Repository Pattern: Abstraction over vector storage
- Builder Pattern: Flexible index construction
"""

import logging
from pathlib import Path
import pickle
from typing import Any

import faiss
import numpy as np

from app.core.config import settings


logger = logging.getLogger(__name__)


class VectorSearchService:
    """
    FAISS-based vector search service for finding similar movies.

    Uses HNSW (Hierarchical Navigable Small World) algorithm for efficient
    approximate nearest neighbor (ANN) search. HNSW provides excellent
    recall with sub-linear search time.

    Index Types Used:
    - IndexHNSWFlat: HNSW with exact inner product (for normalized vectors)
    - Supports L2 normalization for cosine similarity via dot product

    Example:
        ```python
        # Build index
        service = VectorSearchService()
        service.build_index(embeddings, movie_ids)
        service.save_index()

        # Search
        query_embedding = embedding_service.generate_embedding("sci-fi thriller")
        results = service.search(query_embedding, k=10)
        # Returns: [(movie_id, similarity_score), ...]
        ```
    """

    def __init__(
        self,
        dimension: int | None = None,
        index_path: str | None = None,
        metadata_path: str | None = None,
    ) -> None:
        """
        Initialize vector search service.

        Args:
            dimension: Embedding dimension (default: from config)
            index_path: Path to save/load FAISS index (default: from config)
            metadata_path: Path to save/load metadata (default: from config)
        """
        self.dimension = dimension or settings.EMBEDDING_DIMENSION
        self.index_path = Path(index_path or settings.FAISS_INDEX_PATH)
        self.metadata_path = Path(metadata_path or settings.FAISS_METADATA_PATH)

        # FAISS index (lazy-loaded)
        self._index: faiss.Index | None = None

        # Metadata: Maps index position -> movie_id
        self._id_map: list[int] = []

        # Stats
        self._index_size = 0

    @property
    def index(self) -> faiss.Index:
        """
        Get the FAISS index (lazy-loaded).

        Returns:
            FAISS index instance

        Raises:
            RuntimeError: If index not built or loaded
        """
        if self._index is None:
            msg = "Index not initialized. Please build a new index using build_index() or load an existing index using load_index()."
            raise RuntimeError(msg)
        return self._index

    @property
    def is_trained(self) -> bool:
        """Check if index is trained and ready for search."""
        return self._index is not None and self._index.is_trained

    @property
    def size(self) -> int:
        """Get number of vectors in the index."""
        return self._index_size

    def build_index(
        self,
        embeddings: np.ndarray,
        movie_ids: list[int],
        m: int = 32,
        ef_construction: int = 200,
    ) -> None:
        """
        Build FAISS HNSW index from embeddings.

        HNSW Parameters:
        - m: Number of connections per layer (default: 32)
          Higher = better recall but more memory
        - ef_construction: Size of dynamic candidate list during construction (default: 200)
          Higher = better quality but slower build

        Args:
            embeddings: numpy array of shape (n_movies, dimension)
            movie_ids: List of movie IDs corresponding to embeddings
            m: HNSW graph connectivity (typical: 16-64)
            ef_construction: Search depth during construction (typical: 100-500)

        Raises:
            ValueError: If embeddings and movie_ids don't match
            RuntimeError: If index construction fails

        Example:
            ```python
            embeddings = np.array([[0.1, 0.2, ...], [0.3, 0.4, ...]])  # (1000, 768)
            movie_ids = [1, 2, 3, ..., 1000]
            service.build_index(embeddings, movie_ids, m=32, ef_construction=200)
            ```
        """
        if len(embeddings) != len(movie_ids):
            msg = f"Embeddings count ({len(embeddings)}) must match movie_ids count ({len(movie_ids)})"
            raise ValueError(msg)

        if embeddings.shape[1] != self.dimension:
            msg = f"Embedding dimension ({embeddings.shape[1]}) must match configured dimension ({self.dimension})"
            raise ValueError(msg)

        try:
            logger.info(
                f"Building FAISS HNSW index with {len(embeddings)} vectors "
                f"(dim={self.dimension}, M={m}, ef_construction={ef_construction})"
            )

            # Create HNSW index
            # IndexHNSWFlat uses inner product (IP) distance
            # For normalized vectors, IP = cosine similarity
            index = faiss.IndexHNSWFlat(self.dimension, m)

            # Set construction parameters
            index.hnsw.efConstruction = ef_construction

            # Add vectors to index
            # FAISS expects float32 and C-contiguous arrays
            embeddings_f32 = np.ascontiguousarray(embeddings.astype(np.float32))

            # Normalize embeddings for cosine similarity
            faiss.normalize_L2(embeddings_f32)

            # Add to index
            index.add(embeddings_f32)

            # Store index and metadata
            self._index = index
            self._id_map = list(movie_ids)
            self._index_size = len(movie_ids)

            logger.info(f"FAISS index built successfully with {self._index_size} vectors")

        except Exception as e:
            logger.error(f"Failed to build FAISS index: {e}")
            msg = f"FAISS index construction failed: {e}"
            raise RuntimeError(msg) from e

    def search(
        self,
        query_embedding: np.ndarray,
        k: int = 10,
        ef_search: int = 100,
    ) -> list[tuple[int, float]]:
        """
        Search for k most similar vectors.

        Args:
            query_embedding: Query vector of shape (dimension,)
            k: Number of results to return (default: 10)
            ef_search: Search depth (default: 100, typical: 50-500)
                      Higher = better recall but slower search

        Returns:
            List of (movie_id, similarity_score) tuples sorted by similarity (descending)
            Similarity scores are in range [-1, 1] for cosine similarity

        Raises:
            RuntimeError: If index not initialized
            ValueError: If query embedding has wrong dimension

        Example:
            ```python
            query = np.array([0.1, 0.2, ...])  # (768,)
            results = service.search(query, k=10, ef_search=100)
            # [(123, 0.95), (456, 0.89), ...]
            ```
        """
        if query_embedding.shape[0] != self.dimension:
            msg = f"Query embedding dimension ({query_embedding.shape[0]}) must match index dimension ({self.dimension})"
            raise ValueError(msg)

        # Ensure index is loaded
        index = self.index

        # Adjust k if necessary
        actual_k = min(k, self._index_size)
        if actual_k < k:
            logger.warning(f"Requested k={k} but index only has {self._index_size} vectors")

        try:
            # Set search parameters
            if isinstance(index, faiss.IndexHNSWFlat):
                index.hnsw.efSearch = ef_search

            # Prepare query (reshape to 2D, convert to float32, normalize)
            # Ensure C-contiguous for FAISS
            query_f32 = np.ascontiguousarray(query_embedding.astype(np.float32).reshape(1, -1))
            faiss.normalize_L2(query_f32)

            # Search
            distances, indices = index.search(query_f32, actual_k)

            # Convert to results: FAISS returns squared L2 distance for IP
            # For normalized vectors, distance = inner product (cosine similarity)
            results = []
            for dist, idx in zip(distances[0], indices[0]):
                if idx == -1:  # FAISS returns -1 for empty slots
                    continue

                movie_id = self._id_map[idx]
                similarity = float(dist)  # Inner product = cosine similarity for normalized vectors
                results.append((movie_id, similarity))

            logger.debug(f"Found {len(results)} similar movies for query")
            return results

        except Exception as e:
            logger.error(f"Search failed: {e}")
            msg = f"Vector search failed: {e}"
            raise RuntimeError(msg) from e

    def save_index(self) -> None:
        """
        Save FAISS index and metadata to disk.

        Raises:
            RuntimeError: If index not built or save fails

        Example:
            ```python
            service.build_index(embeddings, movie_ids)
            service.save_index()  # Saves to configured paths
            ```
        """
        if self._index is None:
            msg = "Cannot save: index not built"
            raise RuntimeError(msg)

        try:
            # Create directory if needed
            self.index_path.parent.mkdir(parents=True, exist_ok=True)
            self.metadata_path.parent.mkdir(parents=True, exist_ok=True)

            # Save FAISS index
            logger.info(f"Saving FAISS index to {self.index_path}")
            faiss.write_index(self._index, str(self.index_path))

            # Save metadata (ID mapping)
            logger.info(f"Saving metadata to {self.metadata_path}")
            metadata = {
                "id_map": self._id_map,
                "index_size": self._index_size,
                "dimension": self.dimension,
            }
            with open(self.metadata_path, "wb") as f:
                pickle.dump(metadata, f)

            logger.info(f"Successfully saved index with {self._index_size} vectors")

        except Exception as e:
            logger.error(f"Failed to save index: {e}")
            msg = f"Index save failed: {e}"
            raise RuntimeError(msg) from e

    def load_index(self) -> None:
        """
        Load FAISS index and metadata from disk.

        Raises:
            FileNotFoundError: If index files don't exist
            RuntimeError: If load fails

        Example:
            ```python
            service = VectorSearchService()
            service.load_index()  # Loads from configured paths
            results = service.search(query_embedding, k=10)
            ```
        """
        if not self.index_path.exists():
            msg = f"FAISS index not found at {self.index_path}. Please build an index first using build_index()."
            raise FileNotFoundError(msg)

        if not self.metadata_path.exists():
            msg = f"Metadata not found at {self.metadata_path}. Please build an index first using build_index()."
            raise FileNotFoundError(msg)

        try:
            # Load FAISS index
            logger.info(f"Loading FAISS index from {self.index_path}")
            self._index = faiss.read_index(str(self.index_path))

            # Load metadata
            logger.info(f"Loading metadata from {self.metadata_path}")
            with open(self.metadata_path, "rb") as f:
                metadata = pickle.load(f)

            self._id_map = metadata["id_map"]
            self._index_size = metadata["index_size"]

            # Validate
            if metadata["dimension"] != self.dimension:
                msg = f"Loaded index dimension ({metadata['dimension']}) doesn't match configured dimension ({self.dimension})"
                raise ValueError(msg)

            logger.info(f"Successfully loaded index with {self._index_size} vectors")

        except Exception as e:
            logger.error(f"Failed to load index: {e}")
            # Clean up partial state
            self._index = None
            self._id_map = []
            self._index_size = 0
            msg = f"Index load failed: {e}"
            raise RuntimeError(msg) from e

    def get_index_info(self) -> dict[str, Any]:
        """
        Get information about the current index.

        Returns:
            Dictionary with index metadata

        Example:
            ```python
            info = service.get_index_info()
            print(info['size'])  # 10000
            print(info['dimension'])  # 768
            ```
        """
        return {
            "is_trained": self.is_trained,
            "size": self._index_size,
            "dimension": self.dimension,
            "index_type": type(self._index).__name__ if self._index else None,
            "index_path": str(self.index_path),
            "metadata_path": str(self.metadata_path),
        }

    def clear_index(self) -> None:
        """
        Clear the in-memory index.

        This does not delete saved files, only clears memory.
        """
        self._index = None
        self._id_map = []
        self._index_size = 0
        logger.info("Index cleared from memory")


# Singleton instance for app-wide use
_vector_search_instance: VectorSearchService | None = None


def get_vector_search_service() -> VectorSearchService:
    """
    Get the singleton vector search service instance.

    Returns:
        Shared VectorSearchService instance

    Example:
        ```python
        # In different parts of your application
        service = get_vector_search_service()
        results = service.search(query_embedding, k=10)
        ```
    """
    global _vector_search_instance

    if _vector_search_instance is None:
        _vector_search_instance = VectorSearchService()

    return _vector_search_instance
