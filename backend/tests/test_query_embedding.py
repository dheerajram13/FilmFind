"""
Tests for Query Embedding Service.

Tests the conversion of parsed queries into semantic embeddings,
including theme/tone enrichment and reference-based embeddings.
"""

import numpy as np
import pytest

from app.schemas.query import (
    EmotionType,
    ParsedQuery,
    QueryConstraints,
    QueryIntent,
    ToneType,
)
from app.services.embedding_service import EmbeddingService
from app.services.query_embedding import QueryEmbeddingService


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def embedding_service():
    """Create embedding service instance."""
    return EmbeddingService()


@pytest.fixture
def query_embedding_service(embedding_service):
    """Create query embedding service with mocked embedding service."""
    return QueryEmbeddingService(embedding_service=embedding_service)


@pytest.fixture
def simple_parsed_query():
    """Simple parsed query without extras."""
    return ParsedQuery(
        raw_query="sci-fi movies",
        intent=QueryIntent(
            raw_query="sci-fi movies",
            themes=["space", "technology"],
            tones=[ToneType.SERIOUS],
            emotions=[EmotionType.AWE],
            reference_titles=[],
        ),
        confidence="high",
        source="llm",
    )


@pytest.fixture
def complex_parsed_query():
    """Complex parsed query with reference titles and constraints."""
    return ParsedQuery(
        raw_query="dark sci-fi movies like Interstellar with less romance",
        intent=QueryIntent(
            raw_query="dark sci-fi movies like Interstellar with less romance",
            themes=["space", "time travel", "exploration"],
            tones=[ToneType.DARK, ToneType.SERIOUS],
            emotions=[EmotionType.AWE, EmotionType.THRILL],
            reference_titles=["Interstellar"],
            undesired_themes=["romance"],
            undesired_tones=[ToneType.LIGHT],
            constraints=QueryConstraints(
                genres=["Science Fiction"],
                media_type="movie",
            ),
        ),
        confidence="high",
        source="llm",
    )


# =============================================================================
# Query Text Building Tests
# =============================================================================


class TestQueryTextBuilding:
    """Test building rich query text from parsed queries."""

    def test_build_query_text_simple(self, query_embedding_service, simple_parsed_query):
        """Test building query text for simple query."""
        query_text = query_embedding_service._build_query_text(simple_parsed_query)

        # Should include raw query
        assert "sci-fi movies" in query_text

        # Should include themes
        assert "space" in query_text or "technology" in query_text

        # Should include tones
        assert "serious" in query_text.lower()

    def test_build_query_text_with_reference(
        self, query_embedding_service, complex_parsed_query
    ):
        """Test building query text with reference titles."""
        query_text = query_embedding_service._build_query_text(complex_parsed_query)

        # Should include reference title
        assert "Interstellar" in query_text
        assert "Similar to" in query_text or "similar to" in query_text

    def test_build_query_text_with_themes(
        self, query_embedding_service, complex_parsed_query
    ):
        """Test query text includes themes."""
        query_text = query_embedding_service._build_query_text(complex_parsed_query)

        # Should include some themes
        assert any(
            theme in query_text
            for theme in ["space", "time travel", "exploration"]
        )

    def test_build_query_text_with_undesired(
        self, query_embedding_service, complex_parsed_query
    ):
        """Test query text includes undesired elements."""
        query_text = query_embedding_service._build_query_text(complex_parsed_query)

        # Should mention avoiding romance
        assert "romance" in query_text.lower()
        assert "avoid" in query_text.lower() or "less" in query_text.lower()

    def test_build_query_text_with_genres(self, query_embedding_service):
        """Test query text includes genres from constraints."""
        parsed_query = ParsedQuery(
            raw_query="action thriller",
            intent=QueryIntent(
                raw_query="action thriller",
                themes=["action"],
                constraints=QueryConstraints(genres=["Action", "Thriller"]),
            ),
            confidence="high",
            source="llm",
        )

        query_text = query_embedding_service._build_query_text(parsed_query)
        assert "Action" in query_text or "Thriller" in query_text

    def test_build_query_text_empty_intent(self, query_embedding_service):
        """Test building query text with minimal intent."""
        parsed_query = ParsedQuery(
            raw_query="movies",
            intent=QueryIntent(raw_query="movies"),
            confidence="low",
            source="rule_based",
        )

        query_text = query_embedding_service._build_query_text(parsed_query)
        # Should at least have the raw query
        assert "movies" in query_text


# =============================================================================
# Embedding Generation Tests
# =============================================================================


class TestEmbeddingGeneration:
    """Test generating embeddings from parsed queries."""

    def test_generate_query_embedding_simple(
        self, query_embedding_service, simple_parsed_query
    ):
        """Test generating embedding for simple query."""
        embedding = query_embedding_service.generate_query_embedding(
            simple_parsed_query
        )

        # Should return numpy array
        assert isinstance(embedding, np.ndarray)

        # Should have correct dimension (768 for all-mpnet-base-v2)
        assert embedding.shape == (768,)

        # Should be normalized (L2 norm ≈ 1.0)
        norm = np.linalg.norm(embedding)
        assert abs(norm - 1.0) < 0.01

    def test_generate_query_embedding_complex(
        self, query_embedding_service, complex_parsed_query
    ):
        """Test generating embedding for complex query."""
        embedding = query_embedding_service.generate_query_embedding(
            complex_parsed_query
        )

        assert isinstance(embedding, np.ndarray)
        assert embedding.shape == (768,)

        # Should be normalized
        norm = np.linalg.norm(embedding)
        assert abs(norm - 1.0) < 0.01

    def test_generate_query_embedding_without_normalization(
        self, query_embedding_service, simple_parsed_query
    ):
        """Test generating unnormalized embedding."""
        embedding = query_embedding_service.generate_query_embedding(
            simple_parsed_query, normalize=False
        )

        # Should still be valid
        assert isinstance(embedding, np.ndarray)
        assert embedding.shape == (768,)

        # Norm may not be 1.0
        # (depends on model output, but should be non-zero)
        norm = np.linalg.norm(embedding)
        assert norm > 0

    def test_embeddings_are_different_for_different_queries(
        self, query_embedding_service
    ):
        """Test that different queries produce different embeddings."""
        query1 = ParsedQuery(
            raw_query="sci-fi movies",
            intent=QueryIntent(
                raw_query="sci-fi movies",
                themes=["space", "technology"],
            ),
            confidence="high",
            source="llm",
        )

        query2 = ParsedQuery(
            raw_query="romantic comedies",
            intent=QueryIntent(
                raw_query="romantic comedies",
                themes=["romance", "comedy"],
            ),
            confidence="high",
            source="llm",
        )

        embedding1 = query_embedding_service.generate_query_embedding(query1)
        embedding2 = query_embedding_service.generate_query_embedding(query2)

        # Embeddings should be different
        similarity = np.dot(embedding1, embedding2)
        assert similarity < 0.99  # Not identical

    def test_similar_queries_produce_similar_embeddings(
        self, query_embedding_service
    ):
        """Test that similar queries produce similar embeddings."""
        query1 = ParsedQuery(
            raw_query="sci-fi movies about space",
            intent=QueryIntent(
                raw_query="sci-fi movies about space",
                themes=["space", "exploration"],
            ),
            confidence="high",
            source="llm",
        )

        query2 = ParsedQuery(
            raw_query="space exploration films",
            intent=QueryIntent(
                raw_query="space exploration films",
                themes=["space", "exploration"],
            ),
            confidence="high",
            source="llm",
        )

        embedding1 = query_embedding_service.generate_query_embedding(query1)
        embedding2 = query_embedding_service.generate_query_embedding(query2)

        # Embeddings should be similar (high cosine similarity)
        similarity = np.dot(embedding1, embedding2)
        assert similarity > 0.7  # High similarity


# =============================================================================
# Batch Embedding Tests
# =============================================================================


class TestBatchEmbeddings:
    """Test batch embedding generation."""

    def test_generate_batch_embeddings(self, query_embedding_service):
        """Test generating embeddings for multiple queries."""
        queries = [
            ParsedQuery(
                raw_query="sci-fi movies",
                intent=QueryIntent(raw_query="sci-fi movies", themes=["space"]),
                confidence="high",
                source="llm",
            ),
            ParsedQuery(
                raw_query="action thrillers",
                intent=QueryIntent(raw_query="action thrillers", themes=["action"]),
                confidence="high",
                source="llm",
            ),
            ParsedQuery(
                raw_query="romantic dramas",
                intent=QueryIntent(raw_query="romantic dramas", themes=["romance"]),
                confidence="high",
                source="llm",
            ),
        ]

        embeddings = query_embedding_service.generate_batch_embeddings(queries)

        # Should return list of embeddings
        assert isinstance(embeddings, list)
        assert len(embeddings) == 3

        # All should be valid embeddings
        for embedding in embeddings:
            assert isinstance(embedding, np.ndarray)
            assert embedding.shape == (768,)

    def test_batch_embeddings_empty_list(self, query_embedding_service):
        """Test batch generation with empty list."""
        embeddings = query_embedding_service.generate_batch_embeddings([])

        assert isinstance(embeddings, list)
        assert len(embeddings) == 0


# =============================================================================
# Reference-Based Embedding Tests
# =============================================================================


class TestReferenceBased Embeddings:
    """Test generating embeddings from reference movie embeddings."""

    def test_generate_reference_based_embedding_single(
        self, query_embedding_service
    ):
        """Test generating embedding from single reference movie."""
        movie_embeddings = {
            "Interstellar": np.random.randn(768),
        }

        # Normalize it
        movie_embeddings["Interstellar"] /= np.linalg.norm(
            movie_embeddings["Interstellar"]
        )

        embedding = query_embedding_service.generate_reference_based_embedding(
            reference_titles=["Interstellar"],
            movie_embeddings=movie_embeddings,
        )

        # Should return the movie's embedding (since only one)
        assert embedding is not None
        assert isinstance(embedding, np.ndarray)
        assert embedding.shape == (768,)

        # Should be normalized
        norm = np.linalg.norm(embedding)
        assert abs(norm - 1.0) < 0.01

    def test_generate_reference_based_embedding_multiple(
        self, query_embedding_service
    ):
        """Test generating embedding from multiple reference movies."""
        movie_embeddings = {
            "Interstellar": np.random.randn(768),
            "Inception": np.random.randn(768),
        }

        # Normalize them
        for title in movie_embeddings:
            movie_embeddings[title] /= np.linalg.norm(movie_embeddings[title])

        embedding = query_embedding_service.generate_reference_based_embedding(
            reference_titles=["Interstellar", "Inception"],
            movie_embeddings=movie_embeddings,
        )

        # Should return averaged embedding
        assert embedding is not None
        assert isinstance(embedding, np.ndarray)
        assert embedding.shape == (768,)

        # Should be normalized
        norm = np.linalg.norm(embedding)
        assert abs(norm - 1.0) < 0.01

    def test_reference_based_embedding_case_insensitive(
        self, query_embedding_service
    ):
        """Test reference matching is case-insensitive."""
        movie_embeddings = {
            "Interstellar": np.random.randn(768),
        }
        movie_embeddings["Interstellar"] /= np.linalg.norm(
            movie_embeddings["Interstellar"]
        )

        # Query with different case
        embedding = query_embedding_service.generate_reference_based_embedding(
            reference_titles=["interstellar"],  # lowercase
            movie_embeddings=movie_embeddings,
        )

        assert embedding is not None

    def test_reference_based_embedding_no_matches(self, query_embedding_service):
        """Test handling when no reference titles match."""
        movie_embeddings = {
            "Interstellar": np.random.randn(768),
        }

        embedding = query_embedding_service.generate_reference_based_embedding(
            reference_titles=["NonexistentMovie"],
            movie_embeddings=movie_embeddings,
        )

        # Should return None when no matches
        assert embedding is None

    def test_reference_based_embedding_empty_titles(self, query_embedding_service):
        """Test handling empty reference titles list."""
        movie_embeddings = {
            "Interstellar": np.random.randn(768),
        }

        embedding = query_embedding_service.generate_reference_based_embedding(
            reference_titles=[],
            movie_embeddings=movie_embeddings,
        )

        # Should return None for empty list
        assert embedding is None


# =============================================================================
# Integration Tests
# =============================================================================


class TestIntegration:
    """Integration tests with real embedding service."""

    def test_end_to_end_query_embedding(self, query_embedding_service):
        """Test complete flow from query to embedding."""
        parsed_query = ParsedQuery(
            raw_query="dark sci-fi like Interstellar",
            intent=QueryIntent(
                raw_query="dark sci-fi like Interstellar",
                themes=["space", "time"],
                tones=[ToneType.DARK],
                emotions=[EmotionType.AWE],
                reference_titles=["Interstellar"],
            ),
            confidence="high",
            source="llm",
        )

        # Generate embedding
        embedding = query_embedding_service.generate_query_embedding(parsed_query)

        # Validate
        assert isinstance(embedding, np.ndarray)
        assert embedding.shape == (768,)
        assert abs(np.linalg.norm(embedding) - 1.0) < 0.01

    def test_service_reuses_embedding_service(self):
        """Test that service properly reuses embedding service instance."""
        service = QueryEmbeddingService()

        # Should lazy-load on first access
        embed_service = service.embedding_service
        assert embed_service is not None

        # Should return same instance
        assert service.embedding_service is embed_service
