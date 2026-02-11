"""
Movie/Media mapping utilities.

Provides DRY utilities for converting Media models to response schemas.
"""

from app.models.media import Media, Movie
from app.schemas.movie import MovieResponse, MovieSearchResult


def movie_to_response(media: Media) -> MovieResponse:
    """
    Convert Media model (Movie or TVShow) to MovieResponse schema.

    Args:
        media: Media model instance (Movie or TVShow)

    Returns:
        MovieResponse schema
    """
    # Get runtime from Movie-specific field if it's a Movie
    runtime = getattr(media, 'runtime', None) if hasattr(media, 'runtime') else None

    return MovieResponse(
        id=media.id,
        tmdb_id=media.tmdb_id,
        media_type=media.media_type,
        title=media.title,
        release_date=media.release_date,
        overview=media.overview,
        poster_path=media.poster_path,
        backdrop_path=media.backdrop_path,
        genres=media.genres,
        vote_average=media.vote_average,
        vote_count=media.vote_count,
        popularity=media.popularity,
        runtime=runtime,
        original_language=media.original_language,
        adult=media.adult,
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

    # Convert genres from strings to GenreSchema objects if needed
    genres_raw = get_val(movie, "genres", [])
    from app.schemas.movie import GenreSchema

    genres = []
    if genres_raw:
        for genre in genres_raw:
            if isinstance(genre, str):
                # Genre is a string name, convert to GenreSchema
                genres.append(GenreSchema(id=0, name=genre))
            elif isinstance(genre, dict):
                # Genre is already a dict with id and name
                genres.append(GenreSchema(**genre))
            else:
                # Genre is already a GenreSchema object
                genres.append(genre)

    return MovieSearchResult(
        id=get_val(movie, "id") or get_val(movie, "movie_id"),
        tmdb_id=get_val(movie, "tmdb_id"),
        media_type=get_val(movie, "media_type", "movie"),
        title=get_val(movie, "title"),
        release_date=get_val(movie, "release_date"),
        overview=get_val(movie, "overview"),
        poster_path=get_val(movie, "poster_path") or get_val(movie, "poster_url"),
        backdrop_path=get_val(movie, "backdrop_path") or get_val(movie, "backdrop_url"),
        genres=genres,
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
