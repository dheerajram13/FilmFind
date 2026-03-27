"""
Query understanding schemas for structured query parsing output.

This module defines Pydantic models for representing parsed query information,
including intents, constraints, themes, tones, and reference titles.
"""

from __future__ import annotations

from datetime import UTC, datetime
from enum import Enum
from typing import TYPE_CHECKING

from pydantic import BaseModel, Field, field_validator

if TYPE_CHECKING:
    from app.schemas.search import SearchFilters


class MediaType(str, Enum):
    """Media type enumeration"""

    MOVIE = "movie"
    TV_SHOW = "tv_show"
    BOTH = "both"


class ToneType(str, Enum):
    """Tone type enumeration"""

    DARK = "dark"
    LIGHT = "light"
    SERIOUS = "serious"
    COMEDIC = "comedic"
    INSPIRATIONAL = "inspirational"
    INTENSE = "intense"
    RELAXING = "relaxing"
    SUSPENSEFUL = "suspenseful"


class EmotionType(str, Enum):
    """Emotion type enumeration (8 dimensions)"""

    JOY = "joy"
    FEAR = "fear"
    SADNESS = "sadness"
    AWE = "awe"
    THRILL = "thrill"
    HOPE = "hope"
    ROMANCE = "romance"
    DARK_TONE = "dark_tone"


class QueryConstraints(BaseModel):
    """Constraints and filters extracted from the query"""

    # Media type
    media_type: MediaType | None = Field(
        default=MediaType.BOTH, description="Type of media (movie, tv_show, or both)"
    )

    # Genre constraints
    genres: list[str] = Field(default_factory=list, description="Required genres")
    exclude_genres: list[str] = Field(default_factory=list, description="Genres to exclude")

    # Language constraints
    languages: list[str] = Field(
        default_factory=list, description="Preferred languages (ISO 639-1 codes)"
    )

    # Year constraints
    year_min: int | None = Field(default=None, description="Minimum release year", ge=1900)
    year_max: int | None = Field(default=None, description="Maximum release year", ge=1900)

    @field_validator("year_max")
    @classmethod
    def validate_year_range(cls, v: int | None, info) -> int | None:
        """Validate that year_max >= year_min when both are provided."""
        if v is not None and info.data.get("year_min") is not None:
            year_min = info.data["year_min"]
            if v < year_min:
                msg = f"year_max ({v}) must be >= year_min ({year_min})"
                raise ValueError(msg)
        return v

    # Rating constraints
    rating_min: float | None = Field(
        default=None, description="Minimum rating (0-10)", ge=0.0, le=10.0
    )

    # Runtime constraints (minutes)
    runtime_min: int | None = Field(default=None, description="Minimum runtime in minutes")
    runtime_max: int | None = Field(default=None, description="Maximum runtime in minutes")

    # Streaming providers
    streaming_providers: list[str] = Field(
        default_factory=list, description="Preferred streaming services"
    )

    # Adult content
    adult_content: bool = Field(default=False, description="Include adult content")

    # Popularity/fame constraints
    popular_only: bool = Field(default=False, description="Only include popular titles")
    hidden_gems: bool = Field(default=False, description="Focus on lesser-known titles")

    class Config:
        use_enum_values = True

    @classmethod
    def from_search_filters(cls, filters: SearchFilters) -> QueryConstraints:
        """Build a QueryConstraints from explicit SearchFilters."""
        media_type = MediaType.BOTH
        if filters.media_type is not None:
            try:
                media_type = MediaType(filters.media_type)
            except ValueError:
                media_type = MediaType.BOTH

        return cls(
            media_type=media_type,
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

    def merge_with_filters(self, filters: SearchFilters | None) -> QueryConstraints:
        """
        Return a new QueryConstraints that overlays explicit filters on top of self.

        Genres extracted by the LLM are cleared from the base because they are
        semantic signals for the embedding model, not hard filter requirements.
        Explicit filters (from request.filters) always win.
        """
        # Start from a copy with genres cleared — LLM-extracted genres are not
        # hard filters; forcing them causes 0-result searches.
        merged = self.model_copy(deep=True)
        merged.genres = []

        if not filters:
            return merged

        if filters.year_min is not None:
            merged.year_min = filters.year_min
        if filters.year_max is not None:
            merged.year_max = filters.year_max
        if filters.rating_min is not None:
            merged.rating_min = filters.rating_min
        if filters.runtime_min is not None:
            merged.runtime_min = filters.runtime_min
        if filters.runtime_max is not None:
            merged.runtime_max = filters.runtime_max
        if filters.genres:
            merged.genres = filters.genres
        if filters.language:
            merged.languages = [filters.language]
        if filters.exclude_adult is not None:
            merged.adult_content = not filters.exclude_adult
        if filters.streaming_providers:
            merged.streaming_providers = filters.streaming_providers
        if filters.media_type is not None:
            try:
                merged.media_type = MediaType(filters.media_type)
            except ValueError:
                pass  # keep LLM-parsed media_type

        return merged


class QueryIntent(BaseModel):
    """Intent and semantic information extracted from the query"""

    # Core query elements
    raw_query: str = Field(..., description="Original user query")
    themes: list[str] = Field(
        default_factory=list,
        description="Extracted themes (e.g., 'time travel', 'revenge', 'coming of age')",
    )
    tones: list[ToneType] = Field(default_factory=list, description="Desired tones")
    emotions: list[EmotionType] = Field(
        default_factory=list, description="Desired emotional dimensions"
    )

    # Reference titles
    reference_titles: list[str] = Field(
        default_factory=list,
        description="Movies/shows mentioned as references (e.g., 'like Interstellar')",
    )

    # Keywords and descriptions
    keywords: list[str] = Field(
        default_factory=list, description="Important keywords from the query"
    )
    plot_elements: list[str] = Field(
        default_factory=list, description="Specific plot elements (e.g., 'school setting', 'heist')"
    )

    # Undesired elements
    undesired_themes: list[str] = Field(
        default_factory=list, description="Themes to avoid (e.g., 'less romance')"
    )
    undesired_tones: list[ToneType] = Field(default_factory=list, description="Tones to avoid")

    # Context
    is_comparison_query: bool = Field(
        default=False, description="Whether query compares to reference titles"
    )
    is_mood_query: bool = Field(default=False, description="Whether query is mood/emotion-based")

    class Config:
        use_enum_values = True


class ParsedQuery(BaseModel):
    """Complete parsed query with intent and constraints"""

    # Core components
    intent: QueryIntent = Field(..., description="Extracted intent and semantic information")
    constraints: QueryConstraints = Field(..., description="Filters and constraints")

    # Metadata
    parsed_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="Timestamp when query was parsed",
    )
    confidence_score: float = Field(
        default=1.0, description="Parser confidence (0-1)", ge=0.0, le=1.0
    )
    parsing_method: str = Field(
        default="llm", description="Method used for parsing (llm, rule-based, hybrid)"
    )

    # Embedding-ready text
    search_text: str = Field(
        ..., description="Optimized text for embedding generation and semantic search"
    )

    class Config:
        use_enum_values = True


class QueryParserConfig(BaseModel):
    """Configuration for query parser"""

    llm_provider: str = Field(default="gemini", description="LLM provider (gemini, groq, or ollama)")
    enable_fallback: bool = Field(
        default=True, description="Enable rule-based fallback if LLM fails"
    )
    max_retries: int = Field(default=2, description="Max retries for LLM calls", ge=0, le=5)
    timeout: int = Field(default=10, description="Timeout for LLM calls in seconds", ge=1, le=30)
    cache_results: bool = Field(default=True, description="Cache parsing results")
    cache_ttl: int = Field(default=3600, description="Cache TTL in seconds")

    class Config:
        use_enum_values = True
