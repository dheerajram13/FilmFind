"""
Embedding generation service using sentence-transformers.

This module handles semantic embedding generation for movie text:
- Generates 768-dimensional embeddings using all-mpnet-base-v2
- Supports batch processing for efficiency
- GPU acceleration when available
- L2 normalization for cosine similarity

Design Patterns:
- Singleton Pattern: Single model instance shared across app
- Context Manager: Proper resource cleanup
- Service Pattern: Stateless embedding operations
"""

import logging
import threading
from typing import Any

import numpy as np
from sentence_transformers import SentenceTransformer

from app.core.config import settings


logger = logging.getLogger(__name__)


class EmbeddingService:
    """
    Service for generating semantic embeddings from text.

    Uses the all-mpnet-base-v2 model which produces 768-dimensional
    embeddings optimized for semantic similarity tasks.

    Example:
        ```python
        service = EmbeddingService()
        embedding = service.generate_embedding("Movie text here")
        # Returns: np.ndarray with shape (768,)
        ```
    """

    # Model configuration (from config)
    MODEL_NAME = settings.VECTOR_MODEL
    EMBEDDING_DIM = settings.EMBEDDING_DIMENSION

    def __init__(self, model_name: str | None = None) -> None:
        """
        Initialize embedding service.

        Args:
            model_name: Optional custom model name. Defaults to config VECTOR_MODEL
        """
        self.model_name = model_name or settings.VECTOR_MODEL
        self._model: SentenceTransformer | None = None

    @property
    def model(self) -> SentenceTransformer:
        """
        Lazy-load the sentence transformer model.

        The model is only loaded when first accessed to save memory
        and startup time.

        Returns:
            Loaded SentenceTransformer model
        """
        if self._model is None:
            try:
                logger.info(f"Loading embedding model: {self.model_name}")
                self._model = SentenceTransformer(self.model_name)

                # Log device information
                device = self._model.device
                logger.info(f"Embedding model loaded successfully on device: {device}")

            except Exception as e:
                logger.error(f"Failed to load embedding model '{self.model_name}': {e}")
                raise RuntimeError(
                    f"Could not load embedding model '{self.model_name}'. "
                    f"Please ensure the model is available and you have sufficient "
                    f"disk space and memory. Error: {e}"
                ) from e

        return self._model

    def generate_embedding(self, text: str, normalize: bool = True) -> np.ndarray:
        """
        Generate embedding for a single text.

        Args:
            text: Input text to embed
            normalize: Whether to L2-normalize the embedding (default: True)
                      Normalization enables cosine similarity via dot product

        Returns:
            768-dimensional embedding as numpy array

        Raises:
            ValueError: If text is empty or None

        Example:
            ```python
            service = EmbeddingService()
            text = "A sci-fi thriller about dreams"
            embedding = service.generate_embedding(text)
            print(embedding.shape)  # (768,)
            ```
        """
        if not text or not text.strip():
            raise ValueError("Cannot generate embedding for empty text")

        return self.model.encode(text, convert_to_numpy=True, normalize_embeddings=normalize)

    def generate_embeddings_batch(
        self,
        texts: list[str],
        batch_size: int = 32,
        normalize: bool = True,
        show_progress: bool = True,
    ) -> np.ndarray:
        """
        Generate embeddings for multiple texts in batches.

        Batch processing is more efficient than individual encoding
        for large datasets.

        Args:
            texts: List of texts to embed
            batch_size: Number of texts to process per batch (default: 32)
            normalize: Whether to L2-normalize embeddings (default: True)
            show_progress: Show progress bar (default: True)

        Returns:
            numpy array of shape (len(texts), 768)

        Example:
            ```python
            service = EmbeddingService()
            texts = ["Movie 1 text", "Movie 2 text", "Movie 3 text"]
            embeddings = service.generate_embeddings_batch(texts)
            print(embeddings.shape)  # (3, 768)
            ```
        """
        # Handle empty list
        if not texts:
            return np.array([]).reshape(0, self.EMBEDDING_DIM)

        return self.model.encode(
            texts,
            batch_size=batch_size,
            convert_to_numpy=True,
            normalize_embeddings=normalize,
            show_progress_bar=show_progress,
        )

    def compute_similarity(self, embedding1: np.ndarray, embedding2: np.ndarray) -> float:
        """
        Compute cosine similarity between two embeddings.

        If embeddings are L2-normalized, this is equivalent to dot product.

        Args:
            embedding1: First embedding vector
            embedding2: Second embedding vector

        Returns:
            Similarity score in range [-1, 1]
            1.0 = identical, 0.0 = orthogonal, -1.0 = opposite

        Example:
            ```python
            service = EmbeddingService()
            emb1 = service.generate_embedding("Action movie")
            emb2 = service.generate_embedding("Thriller film")
            similarity = service.compute_similarity(emb1, emb2)
            print(f"Similarity: {similarity:.3f}")
            ```
        """
        # For normalized vectors, cosine similarity = dot product
        similarity = np.dot(embedding1, embedding2)
        return float(similarity)

    def get_model_info(self) -> dict:
        """
        Get information about the loaded model.

        Returns:
            Dictionary with model metadata

        Example:
            ```python
            service = EmbeddingService()
            info = service.get_model_info()
            print(info['model_name'])  # "sentence-transformers/all-mpnet-base-v2"
            print(info['embedding_dim'])  # 768
            ```
        """
        return {
            "model_name": self.model_name,
            "embedding_dim": self.EMBEDDING_DIM,
            "device": str(self.model.device),
            "max_seq_length": self.model.max_seq_length,
        }

    def __enter__(self) -> "EmbeddingService":
        """Context manager entry - ensure model is loaded."""
        _ = self.model  # Trigger lazy loading
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Context manager exit - cleanup if needed."""
        # Model cleanup handled by garbage collection


# Singleton instance for app-wide use
_embedding_service_instance: EmbeddingService | None = None
_embedding_service_lock = threading.Lock()


def get_embedding_service() -> EmbeddingService:
    """
    Get the singleton embedding service instance (thread-safe).

    This ensures only one model is loaded in memory across the application,
    even in multi-threaded environments.

    Returns:
        Shared EmbeddingService instance

    Example:
        ```python
        # In different parts of your application
        service = get_embedding_service()
        embedding = service.generate_embedding("text")
        ```
    """
    global _embedding_service_instance

    # Double-check locking pattern for thread-safety
    if _embedding_service_instance is None:
        with _embedding_service_lock:
            # Check again inside the lock
            if _embedding_service_instance is None:
                _embedding_service_instance = EmbeddingService()

    return _embedding_service_instance
