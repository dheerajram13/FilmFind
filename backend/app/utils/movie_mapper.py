"""
Movie/Media mapping utilities.

Converts Movie / TVShow ORM objects (or dicts from the search pipeline)
to response schemas. The concrete models now hold all scalar fields directly;
relational data (genres, cast, keywords) lives on movie.media.
"""

from app.models.media import Movie, TVShow
from app.schemas.movie import MovieResponse, MovieSearchResult

# Type alias for the concrete resource types
_Resource = Movie | TVShow


def movie_to_response(resource: _Resource) -> MovieResponse:
    """Convert a Movie or TVShow ORM object to MovieResponse."""
    runtime = getattr(resource, "runtime", None)

    return MovieResponse(
        id=resource.media_id,           # expose media_id as the stable public ID
        tmdb_id=resource.tmdb_id,
        media_type=resource.media_type,
        title=resource.title,
        release_date=resource.release_date,
        overview=resource.overview,
        poster_path=resource.poster_url,
        backdrop_path=resource.backdrop_url,
        genres=resource.media.genres if resource.media else [],
        vote_average=resource.vote_average,
        vote_count=resource.vote_count,
        popularity=resource.popularity,
        runtime=runtime,
        original_language=resource.original_language,
        adult=resource.adult,
    )


def movie_to_search_result(movie: _Resource | dict) -> MovieSearchResult:
    """
    Convert a Movie/TVShow ORM object or a search pipeline dict to MovieSearchResult.

    The search pipeline passes dicts (from retrieval_engine) that may contain
    similarity_score, final_score, and match_explanation alongside media fields.
    """
    def get_val(obj, key, default=None):
        if isinstance(obj, dict):
            return obj.get(key, default)
        return getattr(obj, key, default)

    from app.schemas.movie import CastSchema, GenreSchema, KeywordSchema

    # Genres — string names, dicts, or ORM Genre objects
    genres_raw = get_val(movie, "genres", [])
    if not genres_raw and not isinstance(movie, dict) and movie.media:
        genres_raw = movie.media.genres
    genres = []
    for genre in genres_raw:
        if isinstance(genre, str):
            genres.append(GenreSchema(id=0, name=genre))
        elif isinstance(genre, dict):
            genres.append(GenreSchema(**genre))
        else:
            genres.append(genre)

    # Keywords
    keywords_raw = get_val(movie, "keywords", [])
    if not keywords_raw and not isinstance(movie, dict) and movie.media:
        keywords_raw = movie.media.keywords
    keywords = []
    for kw in keywords_raw:
        if isinstance(kw, str):
            keywords.append(KeywordSchema(id=0, name=kw))
        elif isinstance(kw, dict):
            keywords.append(KeywordSchema(**kw))
        else:
            keywords.append(kw)

    # Cast — retrieval_engine stores as "cast" (list of dicts)
    cast_raw = get_val(movie, "cast_members", None) or get_val(movie, "cast", [])
    if not cast_raw and not isinstance(movie, dict) and movie.media:
        cast_raw = movie.media.cast_members
    cast_members = []
    for c in (cast_raw or [])[:5]:
        if isinstance(c, dict):
            cast_members.append(CastSchema(
                id=c.get("id", 0),
                name=c.get("name", ""),
                profile_path=c.get("profile_path"),
            ))
        else:
            cast_members.append(c)

    # Resolve poster/backdrop — ORM objects expose .poster_url / .backdrop_url
    poster = (
        get_val(movie, "poster_path") or get_val(movie, "poster_url")
        if isinstance(movie, dict)
        else movie.poster_url
    )
    backdrop = (
        get_val(movie, "backdrop_path") or get_val(movie, "backdrop_url")
        if isinstance(movie, dict)
        else movie.backdrop_url
    )

    # Public ID: media_id for ORM objects, "id" or "movie_id" for dicts
    public_id = (
        get_val(movie, "id") or get_val(movie, "movie_id")
        if isinstance(movie, dict)
        else movie.media_id
    )

    return MovieSearchResult(
        id=public_id,
        tmdb_id=get_val(movie, "tmdb_id"),
        media_type=get_val(movie, "media_type", "movie"),
        title=get_val(movie, "title"),
        release_date=get_val(movie, "release_date"),
        overview=get_val(movie, "overview"),
        poster_path=poster,
        backdrop_path=backdrop,
        genres=genres,
        keywords=keywords,
        cast_members=cast_members,
        vote_average=get_val(movie, "vote_average") or get_val(movie, "rating"),
        vote_count=get_val(movie, "vote_count"),
        popularity=get_val(movie, "popularity"),
        similarity_score=get_val(movie, "similarity_score", 0.0),
        relevance_score=get_val(movie, "final_score", 0.0),
        match_explanation=get_val(movie, "match_explanation"),
    )


def movies_to_responses(movies: list[_Resource]) -> list[MovieResponse]:
    return [movie_to_response(m) for m in movies]


def movies_to_search_results(movies: list[_Resource | dict]) -> list[MovieSearchResult]:
    return [movie_to_search_result(m) for m in movies]
