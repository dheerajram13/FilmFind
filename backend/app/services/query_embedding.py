"""
Query Embedding Service - Convert user queries to semantic embeddings.

This module handles the conversion of natural language queries into
vector embeddings for semantic search:
- Combines query intent, themes, and reference titles
- Generates rich query representations
- Optimizes for semantic similarity search

Design Patterns:
- Service Pattern: Stateless query-to-embedding operations
- Strategy Pattern: Different embedding strategies for different query types
"""

import logging
from typing import Any

import numpy as np

from app.schemas.query import ParsedQuery
from app.services.embedding_service import EmbeddingService
from app.services.exceptions import EmbeddingGenerationError


logger = logging.getLogger(__name__)


class QueryEmbeddingService:
    """
    Service for converting parsed queries into semantic embeddings.

    This service takes a ParsedQuery (with themes, tones, reference titles, etc.)
    and generates a rich embedding that captures the semantic intent.

    Example:
        ```python
        service = QueryEmbeddingService()
        parsed_query = ParsedQuery(
            raw_query="dark sci-fi like Interstellar",
            intent=QueryIntent(
                themes=["space", "time travel"],
                tones=["dark", "serious"],
                reference_titles=["Interstellar"]
            )
        )
        embedding = service.generate_query_embedding(parsed_query)
        # Returns: np.ndarray with shape (768,)
        ```
    """

    def __init__(self, embedding_service: EmbeddingService | None = None):
        """
        Initialize query embedding service.

        Args:
            embedding_service: Service for generating embeddings
        """
        self._embedding_service = embedding_service

    @property
    def embedding_service(self) -> EmbeddingService:
        """Lazy-load embedding service."""
        if self._embedding_service is None:
            self._embedding_service = EmbeddingService()
        return self._embedding_service

    def generate_query_embedding(
        self, parsed_query: ParsedQuery, normalize: bool = True
    ) -> np.ndarray:
        """
        Generate semantic embedding for a parsed query.

        This method constructs a rich text representation from the parsed query
        and generates an embedding that captures the semantic intent.

        Strategy:
        1. Start with raw query text
        2. Enhance with extracted themes and tones
        3. Boost signal with reference titles (if any)
        4. Generate embedding from combined text

        Args:
            parsed_query: Parsed query with intent and constraints
            normalize: Whether to L2-normalize the embedding (default: True)

        Returns:
            768-dimensional query embedding

        Raises:
            EmbeddingGenerationError: If embedding generation fails
        """
        try:
            # Build rich query text
            query_text = self._build_query_text(parsed_query)

            logger.debug(f"Query text for embedding: {query_text[:200]}...")

            # Generate embedding
            embedding = self.embedding_service.generate_embedding(
                text=query_text, normalize=normalize
            )

            logger.debug(
                f"Generated query embedding: shape={embedding.shape}, "
                f"norm={np.linalg.norm(embedding):.4f}"
            )

            return embedding

        except Exception as e:
            logger.error(f"Query embedding generation failed: {e}", exc_info=True)
            raise EmbeddingGenerationError(
                f"Failed to generate query embedding: {e}"
            ) from e

    def _build_query_text(self, parsed_query: ParsedQuery) -> str:
        """
        Build rich query text from parsed query components.

        Combines multiple signals:
        - Raw query (user's original text)
        - Themes (extracted concepts)
        - Tones (mood/atmosphere)
        - Emotions (emotional dimensions)
        - Reference titles (similar movie names)
        - Genres (if specified)

        This creates a comprehensive semantic representation that
        captures the user's intent from multiple angles.

        Args:
            parsed_query: Parsed query with extracted intent

        Returns:
            Rich query text optimized for embedding generation
        """
        parts = []

        # 1. Start with original query (primary signal)
        if parsed_query.intent.raw_query:
            parts.append(parsed_query.intent.raw_query)

        intent = parsed_query.intent

        # 2. Add reference titles (strong signal for similarity)
        if intent.reference_titles:
            # Reference titles are very important - add them prominently
            titles_text = " ".join(intent.reference_titles)
            parts.append(f"Similar to: {titles_text}")

        # 3. Add themes (core concepts)
        if intent.themes:
            themes_text = ", ".join(intent.themes)
            parts.append(f"Themes: {themes_text}")

        # 4. Add tones (mood/atmosphere)
        if intent.tones:
            # Tones are already strings due to use_enum_values=True
            tones_text = ", ".join([str(tone) for tone in intent.tones])
            parts.append(f"Tone: {tones_text}")

        # 5. Add emotions (emotional dimensions)
        if intent.emotions:
            # Emotions are already strings due to use_enum_values=True
            emotions_text = ", ".join([str(emotion) for emotion in intent.emotions])
            parts.append(f"Emotions: {emotions_text}")

        # 6. Add genres (if specified)
        if parsed_query.constraints and parsed_query.constraints.genres:
            genres_text = ", ".join(parsed_query.constraints.genres)
            parts.append(f"Genres: {genres_text}")

        # 7. Add undesired elements as negative context
        # Note: This helps differentiate, but semantic search may not fully exclude them
        undesired_parts = []
        if intent.undesired_themes:
            undesired_parts.append(f"less {', '.join(intent.undesired_themes)}")
        if intent.undesired_tones:
            undesired_tones_text = ", ".join(
                [tone.value for tone in intent.undesired_tones]
            )
            undesired_parts.append(f"not {undesired_tones_text}")

        if undesired_parts:
            parts.append(f"Avoid: {' and '.join(undesired_parts)}")

        # Combine all parts
        query_text = ". ".join(parts)

        return query_text

    def generate_batch_embeddings(
        self, parsed_queries: list[ParsedQuery], normalize: bool = True
    ) -> list[np.ndarray]:
        """
        Generate embeddings for multiple queries in batch.

        More efficient than calling generate_query_embedding multiple times
        when processing many queries at once.

        Args:
            parsed_queries: List of parsed queries
            normalize: Whether to L2-normalize embeddings

        Returns:
            List of query embeddings

        Raises:
            EmbeddingGenerationError: If batch embedding generation fails
        """
        try:
            # Build query texts
            query_texts = [self._build_query_text(pq) for pq in parsed_queries]

            # Generate embeddings in batch
            embeddings = self.embedding_service.generate_embeddings(
                texts=query_texts, normalize=normalize
            )

            logger.debug(f"Generated {len(embeddings)} query embeddings in batch")

            return embeddings

        except Exception as e:
            logger.error(f"Batch query embedding generation failed: {e}", exc_info=True)
            raise EmbeddingGenerationError(
                f"Failed to generate batch query embeddings: {e}"
            ) from e

    def generate_reference_based_embedding(
        self,
        reference_titles: list[str],
        movie_embeddings: dict[str, np.ndarray],
        normalize: bool = True,
    ) -> np.ndarray | None:
        """
        Generate query embedding based on reference movie embeddings.

        When the user provides reference titles (e.g., "movies like Interstellar"),
        we can use the embeddings of those reference movies directly or
        create a composite embedding.

        This is more accurate than text-based embedding when we have
        the actual movie embeddings available.

        Args:
            reference_titles: List of reference movie titles
            movie_embeddings: Dict mapping movie titles to their embeddings
            normalize: Whether to normalize the result

        Returns:
            Composite embedding from reference movies, or None if no matches found

        Example:
            ```python
            # Get embeddings for "Interstellar" and "Inception"
            movie_embeds = {
                "Interstellar": np.array([...]),
                "Inception": np.array([...])
            }
            embedding = service.generate_reference_based_embedding(
                reference_titles=["Interstellar", "Inception"],
                movie_embeddings=movie_embeds
            )
            ```
        """
        if not reference_titles:
            return None

        # Find matching embeddings
        matched_embeddings = []
        for title in reference_titles:
            # Case-insensitive lookup
            title_lower = title.lower()
            for movie_title, embedding in movie_embeddings.items():
                if title_lower in movie_title.lower():
                    matched_embeddings.append(embedding)
                    break

        if not matched_embeddings:
            logger.warning(
                f"No embedding matches found for reference titles: {reference_titles}"
            )
            return None

        # Average the reference embeddings
        composite_embedding = np.mean(matched_embeddings, axis=0)

        # Normalize if requested
        if normalize:
            norm = np.linalg.norm(composite_embedding)
            if norm > 0:
                composite_embedding = composite_embedding / norm

        logger.info(
            f"Generated reference-based embedding from {len(matched_embeddings)} movies"
        )

        return composite_embedding
