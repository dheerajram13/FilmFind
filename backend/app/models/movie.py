"""
Movie database models with proper indexing and relationships.

This module defines the core database models for the FilmFind application:
- Movie: Main movie entity
- Genre: Movie genres
- Keyword: Movie keywords for semantic search
- Cast: Cast and crew members

Design patterns:
- Repository pattern (accessed via repositories, not directly)
- Rich domain models (with computed properties)
- Normalized schema (many-to-many relationships)
"""

from datetime import datetime
from typing import Optional

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Table,
    Text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship

from app.core.database import Base

# =============================================================================
# Association Tables (Many-to-Many relationships)
# =============================================================================

movie_genres = Table(
    "movie_genres",
    Base.metadata,
    Column("movie_id", Integer, ForeignKey("movies.id", ondelete="CASCADE"), primary_key=True),
    Column("genre_id", Integer, ForeignKey("genres.id", ondelete="CASCADE"), primary_key=True),
    Column("created_at", DateTime, default=datetime.utcnow, nullable=False),
)

movie_keywords = Table(
    "movie_keywords",
    Base.metadata,
    Column("movie_id", Integer, ForeignKey("movies.id", ondelete="CASCADE"), primary_key=True),
    Column("keyword_id", Integer, ForeignKey("keywords.id", ondelete="CASCADE"), primary_key=True),
    Column("created_at", DateTime, default=datetime.utcnow, nullable=False),
)

movie_cast = Table(
    "movie_cast",
    Base.metadata,
    Column("movie_id", Integer, ForeignKey("movies.id", ondelete="CASCADE"), primary_key=True),
    Column("cast_id", Integer, ForeignKey("cast.id", ondelete="CASCADE"), primary_key=True),
    Column("character_name", String(255)),
    Column("order_position", Integer, nullable=False, default=0),  # 0 = main actor
    Column("created_at", DateTime, default=datetime.utcnow, nullable=False),
    # Note: Index 'idx_movie_cast_order' on (movie_id, order_position) is created via Alembic migration
)


# =============================================================================
# Domain Models
# =============================================================================


class Movie(Base):
    """
    Movie entity representing a film with all metadata.

    Attributes:
        id: Primary key
        tmdb_id: TMDB external identifier (unique)
        title: Display title
        original_title: Original language title
        overview: Plot summary/description
        tagline: Movie tagline
        release_date: Theatrical release date
        runtime: Duration in minutes
        adult: Adult content flag
        popularity: TMDB popularity score (changes over time)
        vote_average: Average rating (0-10)
        vote_count: Number of ratings
        original_language: ISO 639-1 language code
        poster_path: TMDB poster image path
        backdrop_path: TMDB backdrop image path
        status: Release status (Released, Post Production, etc.)
        budget: Production budget in USD
        revenue: Box office revenue in USD
        imdb_id: IMDB identifier (tt1234567)
        embedding_vector: Semantic embedding (768-dimensional)
        embedding_model: Model used for embedding
        embedding_dimension: Dimension of embedding vector
        streaming_providers: Available streaming platforms by region
    """

    __tablename__ = "movies"

    # Primary & Foreign Keys
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    tmdb_id = Column(Integer, index=True, nullable=False)  # Unique constraint is composite with media_type

    # Media Type
    media_type = Column(String(10), default="movie", index=True, nullable=False)  # 'movie' or 'tv'

    # Core Movie Information
    title = Column(String(500), nullable=False, index=True)
    original_title = Column(String(500))
    overview = Column(Text)
    tagline = Column(String(500))

    # Release & Runtime
    release_date = Column(DateTime, index=True)  # Indexed for year filtering
    runtime = Column(Integer)  # Duration in minutes

    # Content Flags
    adult = Column(Boolean, default=False, index=True, nullable=False)  # Filter adult content

    # Popularity & Ratings
    popularity = Column(Float, index=True)  # For sorting/boosting
    vote_average = Column(Float, index=True)  # For quality filtering
    vote_count = Column(Integer)

    # Language & Localization
    original_language = Column(String(10), index=True)  # ISO 639-1 code, indexed for filtering

    # Media Assets
    poster_path = Column(String(255))  # /path/to/poster.jpg
    backdrop_path = Column(String(255))  # /path/to/backdrop.jpg

    # Additional Metadata
    status = Column(String(50))  # Released, Post Production, Rumored, etc.
    budget = Column(Integer)  # Production budget (USD)
    revenue = Column(Integer)  # Box office revenue (USD)
    imdb_id = Column(String(20), index=True)  # IMDB identifier (unique)

    # Vector Embeddings (for semantic search)
    embedding_vector = Column(JSONB)  # Stored as JSON array for PostgreSQL compatibility
    embedding_model = Column(String(100))  # e.g., "all-mpnet-base-v2"
    embedding_dimension = Column(Integer)  # e.g., 768

    # Streaming Availability
    # Format: {"Netflix": ["US", "GB"], "Prime": ["US"], "Disney+": ["US"]}
    streaming_providers = Column(JSONB)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships (optimized loading strategies)
    # - selectin: Eager loading for frequently accessed small collections (genres, keywords)
    # - select: Lazy loading for potentially large collections (cast_members)
    genres = relationship("Genre", secondary=movie_genres, back_populates="movies", lazy="selectin")
    keywords = relationship(
        "Keyword", secondary=movie_keywords, back_populates="movies", lazy="selectin"
    )
    cast_members = relationship(
        "Cast", secondary=movie_cast, back_populates="movies", lazy="select"
    )

    # Composite Indexes (for complex queries)
    __table_args__ = (
        # Search by language + popularity
        Index("idx_movies_language_popularity", "original_language", "popularity"),
        # Filter by release year + rating
        Index("idx_movies_release_rating", "release_date", "vote_average"),
        # TMDB sync queries
        Index("idx_movies_updated_at", "updated_at"),
        # Adult content filter + popularity
        Index("idx_movies_adult_popularity", "adult", "popularity"),
        # Media type + popularity (for filtering movies vs TV)
        Index("idx_movies_media_type_popularity", "media_type", "popularity"),
    )

    # =============================================================================
    # Domain Methods & Computed Properties
    # =============================================================================

    @property
    def year(self) -> Optional[int]:
        """Extract release year from release_date."""
        return self.release_date.year if self.release_date else None

    @property
    def poster_url(self) -> Optional[str]:
        """Generate full TMDB poster URL (w500 size)."""
        if self.poster_path:
            return f"https://image.tmdb.org/t/p/w500{self.poster_path}"
        return None

    @property
    def backdrop_url(self) -> Optional[str]:
        """Generate full TMDB backdrop URL (original size)."""
        if self.backdrop_path:
            return f"https://image.tmdb.org/t/p/original{self.backdrop_path}"
        return None

    @property
    def runtime_formatted(self) -> Optional[str]:
        """Format runtime as 'Xh Ym'."""
        if self.runtime:
            hours = self.runtime // 60
            minutes = self.runtime % 60
            return f"{hours}h {minutes}m" if hours > 0 else f"{minutes}m"
        return None

    @property
    def has_embedding(self) -> bool:
        """Check if movie has semantic embedding."""
        return self.embedding_vector is not None and len(self.embedding_vector or []) > 0

    def __repr__(self) -> str:
        """String representation for debugging."""
        return (
            f"<Movie(id={self.id}, tmdb_id={self.tmdb_id}, title='{self.title}', year={self.year})>"
        )


class Genre(Base):
    """
    Movie genre entity (Action, Comedy, Drama, etc.).

    Genres are predefined by TMDB and referenced by tmdb_id.
    """

    __tablename__ = "genres"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    tmdb_id = Column(Integer, unique=True, index=True, nullable=False)
    name = Column(String(100), unique=True, nullable=False, index=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    movies = relationship("Movie", secondary=movie_genres, back_populates="genres", lazy="select")

    def __repr__(self) -> str:
        """String representation for debugging."""
        return f"<Genre(id={self.id}, name='{self.name}')>"


class Keyword(Base):
    """
    Movie keyword entity for semantic search and theme detection.

    Keywords are extracted from TMDB and used for:
    - Semantic embedding generation
    - Theme detection (e.g., "time travel", "space opera")
    - Query understanding
    """

    __tablename__ = "keywords"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    tmdb_id = Column(Integer, unique=True, index=True, nullable=False)
    name = Column(String(255), unique=True, nullable=False, index=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    movies = relationship(
        "Movie", secondary=movie_keywords, back_populates="keywords", lazy="select"
    )

    def __repr__(self) -> str:
        """String representation for debugging."""
        return f"<Keyword(id={self.id}, name='{self.name}')>"


class Cast(Base):
    """
    Cast and crew member entity.

    Represents actors, directors, and other crew members.
    Linked to movies via movie_cast association table with character and order.
    """

    __tablename__ = "cast"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    tmdb_id = Column(Integer, unique=True, index=True, nullable=False)
    name = Column(String(255), nullable=False, index=True)  # Indexed for actor search
    profile_path = Column(String(255))  # TMDB profile image path
    popularity = Column(Float)  # TMDB popularity score

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    movies = relationship(
        "Movie", secondary=movie_cast, back_populates="cast_members", lazy="select"
    )

    @property
    def profile_url(self) -> Optional[str]:
        """Generate full TMDB profile image URL (w185 size)."""
        if self.profile_path:
            return f"https://image.tmdb.org/t/p/w185{self.profile_path}"
        return None

    def __repr__(self) -> str:
        """String representation for debugging."""
        return f"<Cast(id={self.id}, name='{self.name}')>"


# =============================================================================
# Exports (for backward compatibility)
# =============================================================================

MovieGenre = movie_genres
MovieKeyword = movie_keywords
MovieCast = movie_cast
