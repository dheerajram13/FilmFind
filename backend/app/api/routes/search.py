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

from app.api.cache_dependencies import (
    get_filter_cache,
    get_movie_cache,
    get_search_cache,
    get_similar_cache,
    get_trending_cache,
)
from app.api.constants import (
    MIN_QUERY_LENGTH,
    RERANK_MULTIPLIER,
    RETRIEVAL_MULTIPLIER,
    SIMILAR_MOVIES_BUFFER,
)
from app.api.dependencies import DatabaseSession, PaginationParams
from app.api.exceptions import ValidationException
from app.core.cache_strategies import (
    FilterCacheStrategy,
    MovieCacheStrategy,
    SearchCacheStrategy,
    SimilarMoviesCacheStrategy,
    TrendingCacheStrategy,
)
from app.schemas.movie import MovieResponse
from app.schemas.query import ParsedQuery, QueryConstraints, QueryIntent
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
    from app.repositories.movie_repository import MovieRepository
    return SemanticRetrievalEngine(movie_repo=MovieRepository(db))


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
    cache: SearchCacheStrategy = Depends(get_search_cache),
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

    # Check cache first
    filters_dict = request.filters.dict(exclude_none=True) if request.filters else None
    cached_result = cache.get(request.query, filters_dict, request.limit)
    if cached_result:
        logger.info("Returning cached search results")
        return SearchResponse(**cached_result)

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
        # Create retrieval config with top_k
        from app.services.retrieval_engine import RetrievalConfig
        retrieval_config = RetrievalConfig(top_k=request.limit * RETRIEVAL_MULTIPLIER)
        candidates = retrieval_engine.retrieve(
            parsed_query=query_intent,
            config=retrieval_config,
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
            count=0,
            query_interpretation=build_empty_query_interpretation(
                query_intent.intent, validated_constraints
            ),
        )

    # Step 5: Score candidates using multi-signal ranking
    try:
        scored_candidates = scoring_engine.score_candidates(
            candidates=filtered_candidates,
            parsed_query=query_intent,
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

    response = SearchResponse(
        query=request.query,
        results=results,
        count=len(filtered_candidates),
        query_interpretation=build_query_interpretation(query_intent.intent, validated_constraints),
    )

    # Cache the response
    cache.set(request.query, response.dict(), filters_dict, request.limit)

    return response


@router.get("/movie/{movie_id}", status_code=status.HTTP_200_OK, response_model=MovieResponse)
async def get_movie_details(
    movie_id: int,
    db: DatabaseSession,
    cache: MovieCacheStrategy = Depends(get_movie_cache),
) -> MovieResponse:
    """
    Get detailed information about a specific movie.

    Args:
        movie_id: Database ID of the movie
        db: Database session
        cache: Movie cache strategy

    Returns:
        Detailed movie information

    Raises:
        NotFoundException: If movie not found
    """
    # Check cache first
    cached_result = cache.get(movie_id)
    if cached_result:
        logger.info(f"Returning cached movie details for ID: {movie_id}")
        return MovieResponse(**cached_result)

    # Fetch from database
    movie = get_movie_by_id(db, movie_id)
    response = movie_to_response(movie)

    # Cache the response
    cache.set(movie_id, response.dict())

    return response


@router.get("/movie/similar/{movie_id}", status_code=status.HTTP_200_OK)
async def get_similar_movies(
    movie_id: int,
    db: DatabaseSession,
    pagination: PaginationParams,
    retrieval_engine: SemanticRetrievalEngine = Depends(get_retrieval_engine),
    cache: SimilarMoviesCacheStrategy = Depends(get_similar_cache),
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
    # Check cache first
    skip = pagination["skip"]
    limit = pagination["limit"]
    cached_result = cache.get(movie_id, skip, limit)
    if cached_result:
        logger.info(f"Returning cached similar movies for ID: {movie_id}")
        return cached_result

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

    # Create a minimal ParsedQuery for the retrieval engine
    from app.services.retrieval_engine import RetrievalConfig
    simple_query = ParsedQuery(
        intent=QueryIntent(raw_query=reference_movie.overview),
        constraints=QueryConstraints(),
        search_text=reference_movie.overview,
    )
    retrieval_config = RetrievalConfig(top_k=pagination["limit"] + SIMILAR_MOVIES_BUFFER)

    # Retrieve similar movies (add buffer because reference movie will be in results)
    similar_movies = retrieval_engine.retrieve(
        parsed_query=simple_query,
        config=retrieval_config,
    )

    # Filter out the reference movie itself
    similar_movies = [m for m in similar_movies if m.id != movie_id]

    # Apply pagination
    similar_movies = similar_movies[skip : skip + limit]

    # Convert to response format
    results = movies_to_search_results(similar_movies)

    response = {
        "reference_movie": {
            "id": reference_movie.id,
            "title": reference_movie.title,
        },
        "similar_movies": [r.dict() for r in results],
        "total": len(similar_movies),
    }

    # Cache the response
    cache.set(movie_id, response, skip, limit)

    return {
        "reference_movie": response["reference_movie"],
        "similar_movies": results,
        "total": response["total"],
    }


@router.post("/filter", status_code=status.HTTP_200_OK)
async def filter_movies(
    filters: SearchFilters,
    db: DatabaseSession,
    pagination: PaginationParams,
    filter_engine: FilterEngine = Depends(get_filter_engine),
    validator: ConstraintValidator = Depends(get_constraint_validator),
    cache: FilterCacheStrategy = Depends(get_filter_cache),
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

    # Check cache first
    skip = pagination["skip"]
    limit = pagination["limit"]
    filters_dict = filters.dict(exclude_none=True)
    cached_result = cache.get(filters_dict, skip, limit)
    if cached_result:
        logger.info("Returning cached filter results")
        return cached_result

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
    paginated_movies = filtered_movies[skip : skip + limit]

    # Convert to response format
    results = movies_to_responses(paginated_movies)

    # Serialize for cache
    cached_response = {
        "movies": [r.dict() for r in results],
        "total": len(filtered_movies),
        "filters_applied": validated_constraints.dict(exclude_none=True),
    }

    # Cache the serialized response
    cache.set(filters_dict, cached_response, skip, limit)

    return {
        "movies": results,
        "total": len(filtered_movies),
        "filters_applied": validated_constraints.dict(exclude_none=True),
    }


@router.get("/trending", status_code=status.HTTP_200_OK)
async def get_trending_movies(
    db: DatabaseSession,
    pagination: PaginationParams,
    cache: TrendingCacheStrategy = Depends(get_trending_cache),
) -> dict:
    """
    Get trending movies sorted by popularity.

    Args:
        db: Database session
        pagination: Pagination parameters (skip, limit)
        cache: Trending cache strategy

    Returns:
        List of trending movies
    """
    # Check cache first
    skip = pagination["skip"]
    limit = pagination["limit"]
    cached_result = cache.get(skip, limit)
    if cached_result:
        logger.info("Returning cached trending movies")
        return cached_result

    # Get movies sorted by popularity
    movies, total = fetch_trending_movies(db, skip=skip, limit=limit)

    # Convert to response format
    results = movies_to_responses(movies)

    # Serialize for cache
    cached_response = {
        "movies": [r.dict() for r in results],
        "total": total,
    }

    # Cache the serialized response
    cache.set(cached_response, skip, limit)

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
        year_min=filters.year_min,
        year_max=filters.year_max,
        rating_min=filters.rating_min,
        runtime_min=filters.runtime_min,
        runtime_max=filters.runtime_max,
        genres=filters.genres or [],
        languages=[filters.language] if filters.language else [],
        adult_content=not filters.exclude_adult,
        streaming_providers=filters.streaming_providers or [],
    )


def _merge_constraints(parsed_query: ParsedQuery, filters: SearchFilters | None) -> QueryConstraints:
    """
    Merge query-parsed constraints with explicit filter constraints.

    Explicit filters take precedence over parsed constraints.

    Args:
        parsed_query: Parsed query with intent and constraints
        filters: Explicit filter constraints from request

    Returns:
        Merged constraints
    """
    # Start with parsed constraints
    merged_constraints = parsed_query.constraints.copy(deep=True)

    if not filters:
        return merged_constraints

    # Override with explicit filters
    if filters.year_min is not None:
        merged_constraints.year_min = filters.year_min
    if filters.year_max is not None:
        merged_constraints.year_max = filters.year_max
    if filters.rating_min is not None:
        merged_constraints.rating_min = filters.rating_min
    if filters.runtime_min is not None:
        merged_constraints.runtime_min = filters.runtime_min
    if filters.runtime_max is not None:
        merged_constraints.runtime_max = filters.runtime_max
    if filters.genres:
        merged_constraints.genres = filters.genres
    if filters.language:
        merged_constraints.languages = [filters.language]
    if filters.exclude_adult is not None:
        merged_constraints.adult_content = not filters.exclude_adult
    if filters.streaming_providers:
        merged_constraints.streaming_providers = filters.streaming_providers

    return merged_constraints
