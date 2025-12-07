"""
Database repositories for data access layer.

This module exports repository classes that encapsulate database operations.
Repositories follow the Repository pattern to:
- Abstract database operations from business logic
- Provide a clean interface for data access
- Enable easier testing with mocks
- Centralize query logic
"""

from app.repositories.base import BaseRepository
from app.repositories.movie_repository import (
    CastRepository,
    GenreRepository,
    KeywordRepository,
    MovieRepository,
)


__all__ = [
    "BaseRepository",
    "MovieRepository",
    "GenreRepository",
    "KeywordRepository",
    "CastRepository",
]
