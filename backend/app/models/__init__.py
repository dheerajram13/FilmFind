"""Database models"""
# New polymorphic models (production-grade schema)
from app.models.media import Media, Movie, TVShow, Genre, Keyword, Cast

__all__ = [
    "Media",
    "Movie",
    "TVShow",
    "Genre",
    "Keyword",
    "Cast",
]
