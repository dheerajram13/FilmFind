"""
Search and recommendation endpoints.

Provides endpoints for:
- Natural language movie search
- Similar movie recommendations
- Movie details
- Filter-based search
- Trending movies
"""

from fastapi import APIRouter, Depends, status

from app.api.constants import (
    MIN_QUERY_LENGTH,
    RERANK_MULTIPLIER,
    RETRIEVAL_MULTIPLIER,
    SIMILAR_MOVIES_BUFFER,
)
from app.api.dependencies import DatabaseSession, PaginationParams
from app.api.exceptions import ValidationException
from app.schemas.movie import MovieResponse
from app.schemas.query import QueryConstraints, QueryIntent
from app.schemas.search import SearchFilters, SearchRequest, SearchResponse
from app.services.constraint_validator import ConstraintValidator
from app.services.filter_engine import FilterEngine
from app.services.query_parser import QueryParser
from app.services.reranker import LLMReRanker
from app.services.retrieval_engine import SemanticRetrievalEngine
from app.services.scoring_engine import MultiSignalScoringEngine
from app.utils.logger import get_logger
from app.utils.movie_mapper import (
    movie_to_response,
    movies_to_responses,
    movies_to_search_results,
)
from app.utils.movie_repository import (
    get_all_movies,
    get_movie_by_id,
)
from app.utils.movie_repository import (
    get_trending_movies as fetch_trending_movies,
)
from app.utils.query_interpretation import (
    build_empty_query_interpretation,
    build_query_interpretation,
)


logger = get_logger(__name__)

router = APIRouter(prefix="/api", tags=["search"])


# =============================================================================
# Service Dependencies
# =============================================================================


def get_query_parser() -> QueryParser:
    """Dependency for query parser service."""
    return QueryParser()


def get_retrieval_engine(db: DatabaseSession) -> SemanticRetrievalEngine:
    """Dependency for semantic retrieval engine."""
    return SemanticRetrievalEngine(db)


def get_scoring_engine() -> MultiSignalScoringEngine:
    """Dependency for scoring engine."""
    return MultiSignalScoringEngine()


def get_reranker() -> LLMReRanker:
    """Dependency for LLM reranker."""
    return LLMReRanker()


def get_filter_engine() -> FilterEngine:
    """Dependency for filter engine."""
    return FilterEngine()


def get_constraint_validator() -> ConstraintValidator:
    """Dependency for constraint validator."""
    return ConstraintValidator()


# =============================================================================
# Search Endpoints
# =============================================================================


@router.post("/search", status_code=status.HTTP_200_OK, response_model=SearchResponse)
async def search_movies(
    request: SearchRequest,
    db: DatabaseSession,  # noqa: ARG001
    query_parser: QueryParser = Depends(get_query_parser),
    retrieval_engine: SemanticRetrievalEngine = Depends(get_retrieval_engine),
    scoring_engine: MultiSignalScoringEngine = Depends(get_scoring_engine),
    reranker: LLMReRanker = Depends(get_reranker),
    filter_engine: FilterEngine = Depends(get_filter_engine),
    validator: ConstraintValidator = Depends(get_constraint_validator),
) -> SearchResponse:
    """
    Natural language movie search with full intelligence pipeline.

    Pipeline:
    1. Parse query to extract intent and constraints
    2. Validate and normalize constraints
    3. Retrieve candidates using semantic search
    4. Apply hard filters
    5. Score candidates using multi-signal ranking
    6. Re-rank top results with LLM

    Args:
        request: Search request with query and optional filters
        db: Database session
        query_parser: Query parser service
        retrieval_engine: Semantic retrieval service
        scoring_engine: Multi-signal scoring service
        reranker: LLM re-ranking service
        filter_engine: Filter engine service
        validator: Constraint validator service

    Returns:
        Search results with ranked movies and query interpretation

    Raises:
        ValidationException: If query or filters are invalid
    """
    logger.info(f"Search request: {request.query}")

    # Validate query
    if not request.query or len(request.query.strip()) < MIN_QUERY_LENGTH:
        msg = f"Query must be at least {MIN_QUERY_LENGTH} characters"
        raise ValidationException(
            msg,
            details={"query": request.query},
        )

    # Step 1: Parse query to extract intent
    try:
        query_intent = query_parser.parse(request.query)
        logger.info(f"Parsed intent: {query_intent.dict()}")
    except Exception as exc:
        logger.error(f"Query parsing failed: {exc}")
        msg = f"Failed to parse query: {exc!s}"
        raise ValidationException(
            msg,
            details={"query": request.query},
        ) from exc

    # Merge request filters with parsed constraints
    merged_constraints = _merge_constraints(query_intent, request.filters)

    # Step 2: Validate and normalize constraints
    try:
        validated_constraints = validator.validate(merged_constraints)
        logger.info(f"Validated constraints: {validated_constraints.dict()}")
    except ValueError as exc:
        msg = f"Invalid constraints: {exc!s}"
        raise ValidationException(
            msg,
            details={"constraints": merged_constraints.dict()},
        ) from exc

    # Step 3: Retrieve candidates using semantic search
    try:
        candidates = retrieval_engine.retrieve(
            query=query_intent.semantic_query or request.query,
            top_k=request.limit * RETRIEVAL_MULTIPLIER,
        )
        logger.info(f"Retrieved {len(candidates)} candidates")
    except Exception as exc:
        logger.error(f"Retrieval failed: {exc}")
        msg = f"Failed to retrieve candidates: {exc!s}"
        raise ValidationException(
            msg,
            details={"query": request.query},
        ) from exc

    # Step 4: Apply hard filters
    filtered_candidates = filter_engine.apply_filters(candidates, validated_constraints)
    logger.info(f"Filtered to {len(filtered_candidates)} candidates")

    if not filtered_candidates:
        return SearchResponse(
            query=request.query,
            results=[],
            total=0,
            query_interpretation=build_empty_query_interpretation(
                query_intent, validated_constraints
            ),
        )

    # Step 5: Score candidates using multi-signal ranking
    try:
        scored_candidates = scoring_engine.score_batch(
            candidates=filtered_candidates,
            query_intent=query_intent,
        )
        logger.info(f"Scored {len(scored_candidates)} candidates")
    except Exception as exc:
        logger.error(f"Scoring failed: {exc}")
        msg = f"Failed to score candidates: {exc!s}"
        raise ValidationException(
            msg,
        ) from exc

    # Step 6: Re-rank top results with LLM
    top_k = min(request.limit, len(scored_candidates))
    try:
        reranked_results = reranker.rerank(
            query=request.query,
            candidates=scored_candidates[: top_k * RERANK_MULTIPLIER],
            top_k=top_k,
        )
        logger.info(f"Re-ranked to top {len(reranked_results)} results")
    except Exception as exc:
        logger.error(f"Re-ranking failed: {exc}")
        # Fallback to scored results if re-ranking fails
        reranked_results = scored_candidates[:top_k]

    # Convert to response format
    results = movies_to_search_results(reranked_results)

    return SearchResponse(
        query=request.query,
        results=results,
        total=len(filtered_candidates),
        query_interpretation=build_query_interpretation(query_intent, validated_constraints),
    )


@router.get("/movie/{movie_id}", status_code=status.HTTP_200_OK, response_model=MovieResponse)
async def get_movie_details(
    movie_id: int,
    db: DatabaseSession,
) -> MovieResponse:
    """
    Get detailed information about a specific movie.

    Args:
        movie_id: Database ID of the movie
        db: Database session

    Returns:
        Detailed movie information

    Raises:
        NotFoundException: If movie not found
    """
    movie = get_movie_by_id(db, movie_id)
    return movie_to_response(movie)


@router.get("/movie/similar/{movie_id}", status_code=status.HTTP_200_OK)
async def get_similar_movies(
    movie_id: int,
    db: DatabaseSession,
    pagination: PaginationParams,
    retrieval_engine: SemanticRetrievalEngine = Depends(get_retrieval_engine),
) -> dict:
    """
    Find movies similar to a specific movie.

    Uses semantic similarity based on plot embeddings.

    Args:
        movie_id: Database ID of the reference movie
        db: Database session
        pagination: Pagination parameters (skip, limit)
        retrieval_engine: Semantic retrieval service

    Returns:
        List of similar movies with similarity scores

    Raises:
        NotFoundException: If reference movie not found
    """
    # Get reference movie
    reference_movie = get_movie_by_id(db, movie_id)

    logger.info(f"Finding movies similar to: {reference_movie.title}")

    # Use movie's overview for semantic search
    if not reference_movie.overview:
        msg = "Cannot find similar movies: reference movie has no overview"
        raise ValidationException(
            msg,
            details={"movie_id": movie_id},
        )

    # Retrieve similar movies (add buffer because reference movie will be in results)
    similar_movies = retrieval_engine.retrieve(
        query=reference_movie.overview,
        top_k=pagination["limit"] + SIMILAR_MOVIES_BUFFER,
    )

    # Filter out the reference movie itself
    similar_movies = [m for m in similar_movies if m.id != movie_id]

    # Apply pagination
    skip = pagination["skip"]
    limit = pagination["limit"]
    similar_movies = similar_movies[skip : skip + limit]

    # Convert to response format
    results = movies_to_search_results(similar_movies)

    return {
        "reference_movie": {
            "id": reference_movie.id,
            "title": reference_movie.title,
        },
        "similar_movies": results,
        "total": len(similar_movies),
    }


@router.post("/filter", status_code=status.HTTP_200_OK)
async def filter_movies(
    filters: SearchFilters,
    db: DatabaseSession,
    pagination: PaginationParams,
    filter_engine: FilterEngine = Depends(get_filter_engine),
    validator: ConstraintValidator = Depends(get_constraint_validator),
) -> dict:
    """
    Filter movies by constraints without semantic search.

    Uses only hard filters (year, rating, genre, etc.).

    Args:
        filters: Filter constraints
        db: Database session
        pagination: Pagination parameters (skip, limit)
        filter_engine: Filter engine service
        validator: Constraint validator service

    Returns:
        Filtered movie list

    Raises:
        ValidationException: If filters are invalid
    """
    logger.info(f"Filter request: {filters.dict(exclude_none=True)}")

    # Convert SearchFilters to QueryConstraints
    constraints = _convert_filters_to_constraints(filters)

    # Validate constraints
    try:
        validated_constraints = validator.validate(constraints)
    except ValueError as exc:
        msg = f"Invalid filters: {exc!s}"
        raise ValidationException(
            msg,
            details={"filters": filters.dict()},
        ) from exc

    # Get all movies from database
    all_movies = get_all_movies(db)
    logger.info(f"Total movies in database: {len(all_movies)}")

    # Apply filters
    filtered_movies = filter_engine.apply_filters(all_movies, validated_constraints)
    logger.info(f"Filtered to {len(filtered_movies)} movies")

    # Apply pagination
    skip = pagination["skip"]
    limit = pagination["limit"]
    paginated_movies = filtered_movies[skip : skip + limit]

    # Convert to response format
    results = movies_to_responses(paginated_movies)

    return {
        "movies": results,
        "total": len(filtered_movies),
        "filters_applied": validated_constraints.dict(exclude_none=True),
    }


@router.get("/trending", status_code=status.HTTP_200_OK)
async def get_trending_movies(
    db: DatabaseSession,
    pagination: PaginationParams,
) -> dict:
    """
    Get trending movies sorted by popularity.

    Args:
        db: Database session
        pagination: Pagination parameters (skip, limit)

    Returns:
        List of trending movies
    """
    # Get movies sorted by popularity
    movies, total = fetch_trending_movies(db, skip=pagination["skip"], limit=pagination["limit"])

    # Convert to response format
    results = movies_to_responses(movies)

    return {
        "movies": results,
        "total": total,
    }


# =============================================================================
# Helper Functions
# =============================================================================


def _convert_filters_to_constraints(filters: SearchFilters) -> QueryConstraints:
    """
    Convert SearchFilters to QueryConstraints.

    Args:
        filters: Search filter schema

    Returns:
        QueryConstraints schema
    """
    return QueryConstraints(
        min_year=filters.min_year,
        max_year=filters.max_year,
        min_rating=filters.min_rating,
        max_rating=filters.max_rating,
        min_runtime=filters.min_runtime,
        max_runtime=filters.max_runtime,
        genres=filters.genres,
        excluded_genres=filters.excluded_genres,
        languages=filters.languages,
        exclude_adult=filters.exclude_adult,
        streaming_providers=filters.streaming_providers,
        min_popularity=filters.min_popularity,
        max_popularity=filters.max_popularity,
    )


def _merge_constraints(query_intent: QueryIntent, filters: SearchFilters | None) -> QueryIntent:
    """
    Merge query-parsed constraints with explicit filter constraints.

    Explicit filters take precedence over parsed constraints.

    Args:
        query_intent: Parsed query intent with constraints
        filters: Explicit filter constraints from request

    Returns:
        Merged query intent with combined constraints
    """
    if not filters:
        return query_intent

    # Create merged constraints
    merged_intent = query_intent.copy(deep=True)

    # Override with explicit filters
    if filters.min_year is not None:
        merged_intent.constraints.min_year = filters.min_year
    if filters.max_year is not None:
        merged_intent.constraints.max_year = filters.max_year
    if filters.min_rating is not None:
        merged_intent.constraints.min_rating = filters.min_rating
    if filters.max_rating is not None:
        merged_intent.constraints.max_rating = filters.max_rating
    if filters.min_runtime is not None:
        merged_intent.constraints.min_runtime = filters.min_runtime
    if filters.max_runtime is not None:
        merged_intent.constraints.max_runtime = filters.max_runtime
    if filters.genres:
        merged_intent.constraints.genres = filters.genres
    if filters.excluded_genres:
        merged_intent.constraints.excluded_genres = filters.excluded_genres
    if filters.languages:
        merged_intent.constraints.languages = filters.languages
    if filters.exclude_adult is not None:
        merged_intent.constraints.exclude_adult = filters.exclude_adult
    if filters.streaming_providers:
        merged_intent.constraints.streaming_providers = filters.streaming_providers
    if filters.min_popularity is not None:
        merged_intent.constraints.min_popularity = filters.min_popularity
    if filters.max_popularity is not None:
        merged_intent.constraints.max_popularity = filters.max_popularity

    return merged_intent
