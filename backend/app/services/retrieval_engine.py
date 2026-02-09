"""
Semantic Retrieval Engine - Main orchestrator for movie search.

This module coordinates the complete semantic retrieval pipeline:
1. Convert user query to embedding
2. Search vector DB for top candidates
3. Fetch full metadata from database
4. Apply filters and constraints
5. Return ranked candidates

Design Patterns:
- Facade Pattern: Simple interface to complex retrieval pipeline
- Dependency Injection: Services injected for testability
- Strategy Pattern: Configurable retrieval strategies
"""

import logging
from typing import Any

from app.repositories.movie_repository import MovieRepository
from app.schemas.query import ParsedQuery, QueryConstraints
from app.services.embedding_service import EmbeddingService
from app.services.exceptions import FilmFindServiceError, SearchError
from app.services.query_embedding import QueryEmbeddingService
from app.services.vector_search import VectorSearchService


logger = logging.getLogger(__name__)


class RetrievalConfig:
    """Configuration for retrieval behavior."""

    def __init__(
        self,
        top_k: int = 100,
        min_similarity: float = 0.0,
        apply_filters: bool = True,
        include_adult: bool = False,
        max_results: int = 50,
    ):
        """
        Initialize retrieval configuration.

        Args:
            top_k: Number of candidates to retrieve from vector search (default: 100)
            min_similarity: Minimum similarity score threshold (0.0-1.0)
            apply_filters: Whether to apply constraint filters (default: True)
            include_adult: Whether to include adult content (default: False)
            max_results: Maximum number of results to return (default: 50)
        """
        self.top_k = top_k
        self.min_similarity = min_similarity
        self.apply_filters = apply_filters
        self.include_adult = include_adult
        self.max_results = max_results


class SemanticRetrievalEngine:
    """
    Main retrieval engine that orchestrates the semantic search pipeline.

    This is the core service that takes a parsed query and returns
    semantically relevant movie candidates with metadata.

    Example:
        ```python
        # Initialize services
        engine = SemanticRetrievalEngine(
            embedding_service=EmbeddingService(),
            vector_search=VectorSearchService(),
            movie_repo=MovieRepository(db_session)
        )

        # Perform search
        parsed_query = query_parser.parse("dark sci-fi like Interstellar")
        candidates = engine.retrieve(parsed_query, config=RetrievalConfig(top_k=50))

        # Returns: List of dicts with movie data and similarity scores
        ```
    """

    def __init__(
        self,
        embedding_service: EmbeddingService | None = None,
        vector_search: VectorSearchService | None = None,
        movie_repo: MovieRepository | None = None,
    ):
        """
        Initialize semantic retrieval engine.

        Args:
            embedding_service: Service for generating embeddings
            vector_search: Service for vector similarity search
            movie_repo: Repository for fetching movie metadata
        """
        # Services (with lazy initialization fallback)
        self._embedding_service = embedding_service
        self._vector_search = vector_search
        self._movie_repo = movie_repo

        # Initialize query embedding service
        self.query_embedding_service = QueryEmbeddingService(
            embedding_service=self.embedding_service
        )

    @property
    def embedding_service(self) -> EmbeddingService:
        """Lazy-load embedding service."""
        if self._embedding_service is None:
            self._embedding_service = EmbeddingService()
        return self._embedding_service

    @property
    def vector_search(self) -> VectorSearchService:
        """Lazy-load vector search service."""
        if self._vector_search is None:
            self._vector_search = VectorSearchService()
            # Attempt to load existing index
            try:
                self._vector_search.load_index()
                logger.info("Vector index loaded successfully")
            except Exception as e:
                logger.warning(f"Could not load vector index: {e}")
        return self._vector_search

    @property
    def movie_repo(self) -> MovieRepository:
        """Get movie repository (must be injected)."""
        if self._movie_repo is None:
            raise ValueError(
                "MovieRepository must be injected. "
                "Cannot lazy-load database-dependent services."
            )
        return self._movie_repo

    def retrieve(
        self,
        parsed_query: ParsedQuery,
        config: RetrievalConfig | None = None,
    ) -> list[dict[str, Any]]:
        """
        Retrieve semantically relevant movie candidates.

        This is the main entry point for the retrieval pipeline.

        Pipeline:
        1. Convert parsed query to embedding
        2. Search vector DB for top-k candidates
        3. Fetch full metadata from Postgres
        4. Apply constraint filters
        5. Return enriched candidates with scores

        Args:
            parsed_query: Parsed query with intent and constraints
            config: Retrieval configuration (default: RetrievalConfig())

        Returns:
            List of movie candidates with metadata and similarity scores:
            [
                {
                    "movie_id": 123,
                    "tmdb_id": 157336,
                    "title": "Interstellar",
                    "similarity_score": 0.89,
                    "overview": "...",
                    "genres": ["Sci-Fi", "Drama"],
                    "rating": 8.4,
                    "popularity": 142.5,
                    ...
                }
            ]

        Raises:
            SearchError: If retrieval fails
        """
        config = config or RetrievalConfig()

        try:
            logger.info(
                f"Starting retrieval for query: '{parsed_query.intent.raw_query}' "
                f"(top_k={config.top_k})"
            )

            # Step 1: Generate query embedding
            query_embedding = self.query_embedding_service.generate_query_embedding(
                parsed_query
            )

            # Step 2: Vector similarity search
            candidates = self._search_similar(
                query_embedding=query_embedding,
                top_k=config.top_k,
                min_similarity=config.min_similarity,
            )

            if not candidates:
                logger.info("No candidates found from vector search")
                return []

            # Step 3: Fetch full metadata
            enriched_candidates = self._enrich_metadata(candidates)

            # Step 4: Apply filters
            if config.apply_filters:
                filtered_candidates = self._apply_filters(
                    candidates=enriched_candidates,
                    constraints=parsed_query.constraints,
                    include_adult=config.include_adult,
                )
            else:
                filtered_candidates = enriched_candidates

            # Step 5: Limit results
            final_results = filtered_candidates[: config.max_results]

            logger.info(
                f"Retrieved {len(final_results)} candidates "
                f"(from {len(candidates)} vector matches, "
                f"{len(enriched_candidates)} enriched, "
                f"{len(filtered_candidates)} after filters)"
            )

            return final_results

        except FilmFindServiceError:
            # Re-raise our custom exceptions
            raise
        except Exception as e:
            logger.error(f"Retrieval failed: {e}", exc_info=True)
            raise SearchError(f"Failed to retrieve candidates: {e}") from e

    def _search_similar(
        self,
        query_embedding: Any,
        top_k: int,
        min_similarity: float,
    ) -> list[tuple[int, float]]:
        """
        Search for similar movies using vector search.

        Args:
            query_embedding: Query embedding vector
            top_k: Number of candidates to retrieve
            min_similarity: Minimum similarity threshold

        Returns:
            List of (movie_id, similarity_score) tuples
        """
        try:
            # Perform vector search
            results = self.vector_search.search(
                query_embedding=query_embedding,
                k=top_k,
            )

            # Filter by minimum similarity
            if min_similarity > 0:
                results = [
                    (movie_id, score)
                    for movie_id, score in results
                    if score >= min_similarity
                ]

            logger.debug(f"Vector search returned {len(results)} candidates")
            return results

        except Exception as e:
            logger.error(f"Vector search failed: {e}")
            raise SearchError(f"Vector search failed: {e}") from e

    def _enrich_metadata(
        self, candidates: list[tuple[int, float]]
    ) -> list[dict[str, Any]]:
        """
        Fetch full movie metadata for candidates.

        Args:
            candidates: List of (movie_id, similarity_score) tuples

        Returns:
            List of dicts with movie metadata and similarity scores
        """
        if not candidates:
            return []

        try:
            # Extract movie IDs
            movie_ids = [movie_id for movie_id, _ in candidates]

            # Create score lookup
            score_map = {movie_id: score for movie_id, score in candidates}

            # Fetch movies from database
            movies = self.movie_repo.find_by_ids(movie_ids)

            # Enrich with similarity scores
            enriched = []
            for movie in movies:
                movie_dict = {
                    "movie_id": movie.id,
                    "tmdb_id": movie.tmdb_id,
                    "title": movie.title,
                    "original_title": movie.original_title,
                    "overview": movie.overview,
                    "tagline": movie.tagline,
                    "release_date": movie.release_date.isoformat()
                    if movie.release_date
                    else None,
                    "year": movie.year,
                    "runtime": movie.runtime,
                    "rating": movie.vote_average,
                    "vote_count": movie.vote_count,
                    "popularity": movie.popularity,
                    "original_language": movie.original_language,
                    "adult": movie.adult,
                    "poster_url": movie.poster_url,
                    "backdrop_url": movie.backdrop_url,
                    # Add similarity score
                    "similarity_score": score_map.get(movie.id, 0.0),
                    # Genre names (from relationship)
                    "genres": [g.name for g in movie.genres] if movie.genres else [],
                    # Keywords (from relationship)
                    "keywords": [k.name for k in movie.keywords]
                    if movie.keywords
                    else [],
                    # Cast (from relationship) - top 5
                    "cast": [
                        {
                            "name": mc.cast_member.name,
                            "character": mc.character_name,
                            "order": mc.order_position,
                        }
                        for mc in (movie.cast_members[:5] if movie.cast_members else [])
                    ],
                }
                enriched.append(movie_dict)

            # Sort by similarity score (descending)
            enriched.sort(key=lambda x: x["similarity_score"], reverse=True)

            logger.debug(f"Enriched {len(enriched)} movies with metadata")
            return enriched

        except Exception as e:
            logger.error(f"Metadata enrichment failed: {e}")
            raise SearchError(f"Failed to enrich metadata: {e}") from e

    def _apply_filters(
        self,
        candidates: list[dict[str, Any]],
        constraints: QueryConstraints | None,
        include_adult: bool,
    ) -> list[dict[str, Any]]:
        """
        Apply constraint filters to candidates.

        Hard filters (must match):
        - Adult content filter
        - Language filter
        - Year range filter
        - Rating minimum filter

        Args:
            candidates: List of movie candidates with metadata
            constraints: Query constraints to apply
            include_adult: Whether to include adult content

        Returns:
            Filtered list of candidates
        """
        if not candidates:
            return []

        filtered = candidates

        # Filter: Adult content
        if not include_adult:
            filtered = [c for c in filtered if not c.get("adult", False)]
            logger.debug(
                f"After adult filter: {len(filtered)}/{len(candidates)} candidates"
            )

        if constraints is None:
            return filtered

        # Filter: Languages
        if constraints.languages:
            filtered = [
                c
                for c in filtered
                if c.get("original_language") in constraints.languages
            ]
            logger.debug(
                f"After language filter ({constraints.languages}): "
                f"{len(filtered)}/{len(candidates)} candidates"
            )

        # Filter: Year range
        if constraints.year_min is not None or constraints.year_max is not None:
            filtered = [
                c
                for c in filtered
                if self._matches_year_range(
                    c.get("year"), constraints.year_min, constraints.year_max
                )
            ]
            logger.debug(
                f"After year filter ({constraints.year_min}-{constraints.year_max}): "
                f"{len(filtered)}/{len(candidates)} candidates"
            )

        # Filter: Rating minimum
        if constraints.rating_min is not None:
            filtered = [
                c
                for c in filtered
                if (c.get("rating") or 0) >= constraints.rating_min
            ]
            logger.debug(
                f"After rating filter (>={constraints.rating_min}): "
                f"{len(filtered)}/{len(candidates)} candidates"
            )

        # Filter: Runtime range
        if constraints.runtime_min is not None or constraints.runtime_max is not None:
            filtered = [
                c
                for c in filtered
                if self._matches_runtime_range(
                    c.get("runtime"), constraints.runtime_min, constraints.runtime_max
                )
            ]
            logger.debug(
                f"After runtime filter "
                f"({constraints.runtime_min}-{constraints.runtime_max}): "
                f"{len(filtered)}/{len(candidates)} candidates"
            )

        # Note: Genre filtering is soft (handled by semantic similarity)
        # We don't hard filter by genre since semantic search already considers it

        return filtered

    @staticmethod
    def _matches_year_range(
        year: int | None, year_min: int | None, year_max: int | None
    ) -> bool:
        """Check if year falls within range."""
        if year is None:
            return False
        if year_min is not None and year < year_min:
            return False
        if year_max is not None and year > year_max:
            return False
        return True

    @staticmethod
    def _matches_runtime_range(
        runtime: int | None, runtime_min: int | None, runtime_max: int | None
    ) -> bool:
        """Check if runtime falls within range."""
        if runtime is None:
            return False
        if runtime_min is not None and runtime < runtime_min:
            return False
        if runtime_max is not None and runtime > runtime_max:
            return False
        return True
