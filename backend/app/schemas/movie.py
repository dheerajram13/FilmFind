"""
Movie Pydantic schemas for API requests/responses
"""
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class GenreSchema(BaseModel):
    """Genre schema"""

    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str


class KeywordSchema(BaseModel):
    """Keyword schema"""

    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str


class CastSchema(BaseModel):
    """Cast schema"""

    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    character_name: Optional[str] = None
    profile_path: Optional[str] = None


class MovieBase(BaseModel):
    """Base movie schema"""

    title: str
    original_title: Optional[str] = None
    overview: Optional[str] = None
    tagline: Optional[str] = None
    release_date: Optional[datetime] = None
    runtime: Optional[int] = None
    original_language: Optional[str] = None
    poster_path: Optional[str] = None
    backdrop_path: Optional[str] = None


class MovieResponse(MovieBase):
    """Movie response schema"""

    model_config = ConfigDict(from_attributes=True)

    id: int
    tmdb_id: int
    media_type: str = Field(default="movie", description="Media type: 'movie' or 'tv'")
    popularity: Optional[float] = None
    vote_average: Optional[float] = None
    vote_count: Optional[int] = None
    genres: list[GenreSchema] = []
    keywords: list[KeywordSchema] = []
    cast_members: list[CastSchema] = []
    streaming_providers: Optional[dict] = None


class MovieSearchResult(MovieResponse):
    """Movie search result with similarity scores"""

    similarity_score: float = Field(default=0.0, description="Semantic similarity score")
    relevance_score: Optional[float] = Field(None, description="Final ranking score (alias for final_score)")
    match_explanation: Optional[str] = Field(None, description="Why this movie was recommended")
