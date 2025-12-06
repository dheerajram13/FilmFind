"""
Search request/response schemas
"""
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from app.schemas.movie import MovieSearchResult


class SearchFilters(BaseModel):
    """Search filters"""
    year_min: Optional[int] = Field(None, description="Minimum release year")
    year_max: Optional[int] = Field(None, description="Maximum release year")
    rating_min: Optional[float] = Field(None, description="Minimum rating (0-10)")
    rating_max: Optional[float] = Field(None, description="Maximum rating (0-10)")
    runtime_min: Optional[int] = Field(None, description="Minimum runtime in minutes")
    runtime_max: Optional[int] = Field(None, description="Maximum runtime in minutes")
    language: Optional[str] = Field(None, description="Original language code (e.g., 'en', 'ko')")
    genres: Optional[List[str]] = Field(None, description="List of genre names")
    streaming_providers: Optional[List[str]] = Field(None, description="Streaming service names")
    exclude_adult: bool = Field(True, description="Exclude adult content")


class SearchRequest(BaseModel):
    """Search request"""
    query: str = Field(..., description="Natural language search query")
    limit: int = Field(10, ge=1, le=50, description="Number of results to return")
    filters: Optional[SearchFilters] = None


class QueryInterpretation(BaseModel):
    """Parsed query intent"""
    themes: List[str] = Field(default_factory=list, description="Extracted themes")
    emotions: List[str] = Field(default_factory=list, description="Detected emotions")
    reference_titles: List[str] = Field(default_factory=list, description="Reference movies/shows")
    excluded: List[str] = Field(default_factory=list, description="Excluded elements")
    tone: Optional[str] = Field(None, description="Overall tone (dark, light, etc.)")
    genre_hints: List[str] = Field(default_factory=list, description="Suggested genres")


class SearchResponse(BaseModel):
    """Search response"""
    results: List[MovieSearchResult]
    count: int
    query: str
    query_interpretation: Optional[QueryInterpretation] = None
    processing_time_ms: Optional[float] = None


class SimilarRequest(BaseModel):
    """Similar movies request"""
    movie_id: int = Field(..., description="TMDB movie ID")
    limit: int = Field(10, ge=1, le=50, description="Number of similar movies to return")
