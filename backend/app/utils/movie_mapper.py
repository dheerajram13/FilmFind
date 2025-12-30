"""
Movie mapping utilities.

Provides DRY utilities for converting Movie models to response schemas.
"""

from app.models.movie import Movie
from app.schemas.movie import MovieResponse, MovieSearchResult


def movie_to_response(movie: Movie) -> MovieResponse:
    """
    Convert Movie model to MovieResponse schema.

    Args:
        movie: Movie model instance

    Returns:
        MovieResponse schema
    """
    return MovieResponse(
        id=movie.id,
        tmdb_id=movie.tmdb_id,
        title=movie.title,
        release_date=movie.release_date,
        overview=movie.overview,
        poster_path=movie.poster_path,
        backdrop_path=movie.backdrop_path,
        genres=movie.genres,
        vote_average=movie.vote_average,
        vote_count=movie.vote_count,
        popularity=movie.popularity,
        runtime=movie.runtime,
        original_language=movie.original_language,
        adult=movie.adult,
    )


def movie_to_search_result(movie: Movie) -> MovieSearchResult:
    """
    Convert Movie model to MovieSearchResult schema.

    Includes similarity and relevance scores if present.

    Args:
        movie: Movie model instance (may have similarity_score, final_score attrs)

    Returns:
        MovieSearchResult schema
    """
    return MovieSearchResult(
        id=movie.id,
        tmdb_id=movie.tmdb_id,
        title=movie.title,
        release_date=movie.release_date,
        overview=movie.overview,
        poster_path=movie.poster_path,
        backdrop_path=movie.backdrop_path,
        genres=movie.genres,
        vote_average=movie.vote_average,
        vote_count=movie.vote_count,
        popularity=movie.popularity,
        similarity_score=getattr(movie, "similarity_score", 0.0),
        relevance_score=getattr(movie, "final_score", 0.0),
    )


def movies_to_responses(movies: list[Movie]) -> list[MovieResponse]:
    """
    Convert list of Movie models to list of MovieResponse schemas.

    Args:
        movies: List of Movie model instances

    Returns:
        List of MovieResponse schemas
    """
    return [movie_to_response(movie) for movie in movies]


def movies_to_search_results(movies: list[Movie]) -> list[MovieSearchResult]:
    """
    Convert list of Movie models to list of MovieSearchResult schemas.

    Args:
        movies: List of Movie model instances

    Returns:
        List of MovieSearchResult schemas
    """
    return [movie_to_search_result(movie) for movie in movies]
