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


def movie_to_search_result(movie: Movie | dict) -> MovieSearchResult:
    """
    Convert Movie model or dict to MovieSearchResult schema.

    Includes similarity and relevance scores if present.

    Args:
        movie: Movie model instance or dict (may have similarity_score, final_score fields)

    Returns:
        MovieSearchResult schema
    """
    # Helper to get value from both dict and object
    def get_val(obj, key, default=None):
        if isinstance(obj, dict):
            return obj.get(key, default)
        return getattr(obj, key, default)

    return MovieSearchResult(
        id=get_val(movie, "id") or get_val(movie, "movie_id"),
        tmdb_id=get_val(movie, "tmdb_id"),
        title=get_val(movie, "title"),
        release_date=get_val(movie, "release_date"),
        overview=get_val(movie, "overview"),
        poster_path=get_val(movie, "poster_path") or get_val(movie, "poster_url"),
        backdrop_path=get_val(movie, "backdrop_path") or get_val(movie, "backdrop_url"),
        genres=get_val(movie, "genres", []),
        vote_average=get_val(movie, "vote_average") or get_val(movie, "rating"),
        vote_count=get_val(movie, "vote_count"),
        popularity=get_val(movie, "popularity"),
        similarity_score=get_val(movie, "similarity_score", 0.0),
        relevance_score=get_val(movie, "final_score", 0.0),
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


def movies_to_search_results(movies: list[Movie | dict]) -> list[MovieSearchResult]:
    """
    Convert list of Movie models or dicts to list of MovieSearchResult schemas.

    Args:
        movies: List of Movie model instances or dicts

    Returns:
        List of MovieSearchResult schemas
    """
    return [movie_to_search_result(movie) for movie in movies]
