"""
Vector operation utilities for FAISS and numpy arrays.

This module provides utilities for vector normalization, validation, and
preprocessing operations commonly needed for FAISS-based similarity search.

Design Pattern: Utility/Helper Pattern
- Static methods for stateless operations
- Centralized vector operations
- DRY principle - eliminates code duplication
"""

import faiss
import numpy as np


class VectorNormalizer:
    """
    Utilities for vector normalization and preprocessing.

    All methods are static as they perform pure transformations without state.
    Optimized for FAISS compatibility (float32, C-contiguous arrays).
    """

    @staticmethod
    def normalize_l2(vectors: np.ndarray) -> np.ndarray:
        """
        L2-normalize vectors for cosine similarity.

        Converts to float32 C-contiguous array and normalizes using FAISS.
        After normalization, dot product equals cosine similarity.

        Args:
            vectors: Array of shape (n, d) or (d,)
                    Will be converted to float32 and C-contiguous

        Returns:
            L2-normalized vectors as float32 C-contiguous array
            (may be a copy if input needs conversion)

        Example:
            ```python
            vectors = np.random.randn(100, 768)
            normalized = VectorNormalizer.normalize_l2(vectors)
            # Verify: all norms should be ~1.0
            norms = np.linalg.norm(normalized, axis=1)
            assert np.allclose(norms, 1.0)
            ```
        """
        # Ensure float32 and C-contiguous for FAISS
        vectors_f32 = VectorNormalizer.ensure_contiguous_f32(vectors)

        # Handle 1D vectors by reshaping
        original_shape = vectors_f32.shape
        if vectors_f32.ndim == 1:
            vectors_f32 = vectors_f32.reshape(1, -1)

        # Use FAISS for efficient normalization
        faiss.normalize_L2(vectors_f32)

        # Restore original shape if needed
        if len(original_shape) == 1:
            vectors_f32 = vectors_f32.reshape(-1)

        return vectors_f32

    @staticmethod
    def ensure_contiguous_f32(vectors: np.ndarray) -> np.ndarray:
        """
        Ensure array is C-contiguous float32.

        FAISS requires C-contiguous float32 arrays for optimal performance.
        This method efficiently converts arrays to the required format.

        Args:
            vectors: Input array of any dtype and memory layout

        Returns:
            C-contiguous float32 array

        Example:
            ```python
            vectors = np.random.randn(100, 768).astype(np.float64)
            vectors_f32 = VectorNormalizer.ensure_contiguous_f32(vectors)
            assert vectors_f32.dtype == np.float32
            assert vectors_f32.flags['C_CONTIGUOUS']
            ```
        """
        return np.ascontiguousarray(vectors.astype(np.float32))

    @staticmethod
    def compute_cosine_similarity(vec1: np.ndarray, vec2: np.ndarray) -> float:
        """
        Compute cosine similarity between two vectors.

        For normalized vectors, this is equivalent to dot product.

        Args:
            vec1: First vector (1D array)
            vec2: Second vector (1D array)

        Returns:
            Cosine similarity in range [-1, 1]
            1.0 = identical, 0.0 = orthogonal, -1.0 = opposite

        Example:
            ```python
            vec1 = np.array([1.0, 0.0, 0.0])
            vec2 = np.array([1.0, 0.0, 0.0])
            sim = VectorNormalizer.compute_cosine_similarity(vec1, vec2)
            assert sim == 1.0
            ```
        """
        # Normalize if not already normalized
        norm1 = np.linalg.norm(vec1)
        norm2 = np.linalg.norm(vec2)

        if norm1 == 0 or norm2 == 0:
            return 0.0

        return float(np.dot(vec1, vec2) / (norm1 * norm2))

    @staticmethod
    def validate_embedding_shape(embedding: np.ndarray, expected_dim: int) -> None:
        """
        Validate embedding shape and raise descriptive error if invalid.

        Args:
            embedding: Embedding vector to validate
            expected_dim: Expected dimension

        Raises:
            ValueError: If shape is invalid

        Example:
            ```python
            embedding = np.random.randn(768)
            VectorNormalizer.validate_embedding_shape(embedding, 768)  # OK
            VectorNormalizer.validate_embedding_shape(embedding, 512)  # Raises
            ```
        """
        if embedding.ndim == 0:
            msg = "Embedding must be at least 1-dimensional"
            raise ValueError(msg)

        if embedding.ndim > 2:
            msg = f"Embedding must be 1D or 2D, got {embedding.ndim}D"
            raise ValueError(msg)

        actual_dim = embedding.shape[-1]
        if actual_dim != expected_dim:
            msg = (
                f"Embedding dimension ({actual_dim}) doesn't match "
                f"expected dimension ({expected_dim})"
            )
            raise ValueError(msg)

    @staticmethod
    def batch_normalize(embeddings: np.ndarray, batch_size: int = 1000) -> np.ndarray:
        """
        Normalize embeddings in batches for memory efficiency.

        Useful for very large embedding matrices that might not fit in memory.
        Creates a float32 C-contiguous copy and normalizes it in batches.

        Args:
            embeddings: Array of shape (n, d)
            batch_size: Number of vectors to normalize at once

        Returns:
            L2-normalized embeddings as float32 C-contiguous array
            (may be a copy if input needs conversion)

        Example:
            ```python
            large_embeddings = np.random.randn(1000000, 768)
            normalized = VectorNormalizer.batch_normalize(large_embeddings, batch_size=10000)
            ```
        """
        n_vectors = len(embeddings)
        embeddings_f32 = VectorNormalizer.ensure_contiguous_f32(embeddings)

        # Process in batches
        for start_idx in range(0, n_vectors, batch_size):
            end_idx = min(start_idx + batch_size, n_vectors)
            batch = embeddings_f32[start_idx:end_idx]
            faiss.normalize_L2(batch)

        return embeddings_f32
