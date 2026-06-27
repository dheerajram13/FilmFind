"""
Media data models.

Schema design:
- Resource: abstract Python mixin — shared columns for Movie and TVShow
- Movie(Resource): concrete movies table + media_id FK → media.id
- TVShow(Resource): concrete tv_shows table + media_id FK → media.id
- Media: lightweight anchor table (id only) — FK target for genres, cast, keywords,
         enrichment, assets, and embedding; keeps one set of junction tables for both types
- MediaEnrichment: one-to-one with Media, holds AI enrichment scores
- MediaEmbedding: one-to-one with Media, holds pgvector embedding
- MediaAsset: one-to-many with Media, replaces poster_path/backdrop_path columns
"""
from datetime import datetime
from typing import Optional

from sqlalchemy import (
    BigInteger,
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
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.orm import relationship, validates
from pgvector.sqlalchemy import Vector

from app.core.database import Base


# Resource: Abstract Python Mixin 
class Resource:
    """
    Shared column definitions for Movie and TVShow.

    Not a SQLAlchemy model — no __tablename__, no Base.
    Each subclass gets these columns stamped into its own table.
    """
    tmdb_id           = Column(Integer, nullable=False, index=True)
    imdb_id           = Column(String(20), index=True)
    title             = Column(String(500), nullable=False, index=True)
    original_title    = Column(String(500))
    overview          = Column(Text)
    tagline           = Column(String(500))
    release_date      = Column(DateTime, index=True)
    status            = Column(String(50))
    adult             = Column(Boolean, default=False, nullable=False, index=True)
    original_language = Column(String(10), index=True)
    popularity        = Column(Float, index=True)
    vote_average      = Column(Float, index=True)
    vote_count        = Column(Integer)
    belongs_to_collection = Column(JSONB)
    production_countries  = Column(ARRAY(Text))
    spoken_languages      = Column(ARRAY(Text))
    origin_country        = Column(ARRAY(Text))
    production_companies  = Column(JSONB)
    streaming_providers   = Column(JSONB)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    @property
    def year(self) -> Optional[int]:
        return self.release_date.year if self.release_date else None

    def _primary_asset_url(self, asset_type: str) -> Optional[str]:
        assets = self.media.assets if self.media else []
        primary = next((a for a in assets if a.asset_type == asset_type and a.is_primary), None)
        if primary:
            return primary.url
        first = next((a for a in assets if a.asset_type == asset_type), None)
        return first.url if first else None

    @property
    def poster_url(self) -> Optional[str]:
        return self._primary_asset_url("poster")

    @property
    def backdrop_url(self) -> Optional[str]:
        return self._primary_asset_url("backdrop")


# Association Tables (M2M — all FK to media.id, shared by Movie and TVShow)

media_genres = Table(
    "media_genres",
    Base.metadata,
    Column("media_id", Integer, ForeignKey("media.id", ondelete="CASCADE"), primary_key=True),
    Column("genre_id", Integer, ForeignKey("genres.id", ondelete="CASCADE"), primary_key=True),
    Column("created_at", DateTime, default=datetime.utcnow, nullable=False),
)

media_keywords = Table(
    "media_keywords",
    Base.metadata,
    Column("media_id", Integer, ForeignKey("media.id", ondelete="CASCADE"), primary_key=True),
    Column("keyword_id", Integer, ForeignKey("keywords.id", ondelete="CASCADE"), primary_key=True),
    Column("created_at", DateTime, default=datetime.utcnow, nullable=False),
)

media_cast = Table(
    "media_cast",
    Base.metadata,
    Column("media_id", Integer, ForeignKey("media.id", ondelete="CASCADE"), primary_key=True),
    Column("cast_id", Integer, ForeignKey("cast.id", ondelete="CASCADE"), primary_key=True),
    Column("character_name", String(255)),
    Column("order_position", Integer, nullable=False, default=0),
    Column("created_at", DateTime, default=datetime.utcnow, nullable=False),
)



# Stored DB values for content_type.
# Keys ARE the stored values — extend here to add new types ('Short', 'Podcast', etc.)
CONTENT_TYPES: dict[str, str] = {
    "Movie":   "Movie",
    "TV Show": "TV Show",
}


class Media(Base):
    """
    Lightweight anchor — FK target for all relational data.

    content_type identifies the concrete type ('Movie' | 'TV Show') without
    joining either concrete table. Enforced at both ORM and DB levels.
    Extend CONTENT_TYPES to support new categories in the future.
    """
    __tablename__ = "media"

    id           = Column(Integer, primary_key=True, autoincrement=True)
    content_type = Column(String(20), nullable=False, index=True)
    created_at   = Column(DateTime, default=datetime.utcnow, nullable=False)

    @validates("content_type")
    def _validate_content_type(self, _, value: str) -> str:
        if value not in CONTENT_TYPES:
            raise ValueError(f"Invalid content_type {value!r}. Must be one of: {list(CONTENT_TYPES)}")
        return value

    # Reverse one-to-one back to the concrete type
    movie   = relationship("Movie",   back_populates="media", uselist=False)
    tv_show = relationship("TVShow",  back_populates="media", uselist=False)

    # Relational data — one set for both movies + TV shows
    genres       = relationship("Genre",   secondary=media_genres,   back_populates="media_items", lazy="selectin")
    keywords     = relationship("Keyword", secondary=media_keywords,  back_populates="media_items", lazy="selectin")
    cast_members = relationship("Cast",    secondary=media_cast,      back_populates="media_items", lazy="select")

    # Satellite tables
    enrichment = relationship("MediaEnrichment", back_populates="media", uselist=False)
    embedding  = relationship("MediaEmbedding",  back_populates="media", uselist=False)
    assets     = relationship("MediaAsset",      back_populates="media")



# Movie (concrete table — all Resource columns live here)


class Movie(Resource, Base):
    __tablename__ = "movies"

    id       = Column(Integer, primary_key=True, autoincrement=True)
    media_id = Column(
        Integer,
        ForeignKey("media.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
        index=True,
    )
    runtime = Column(Integer)
    budget  = Column(BigInteger)
    revenue = Column(BigInteger)

    media = relationship("Media", back_populates="movie")

    __table_args__ = (
        Index("uq_movies_tmdb_id", "tmdb_id", unique=True),
        Index("idx_movies_language_popularity", "original_language", "popularity"),
        Index("idx_movies_release_rating", "release_date", "vote_average"),
        Index("idx_movies_adult_popularity", "adult", "popularity"),
        Index("idx_movies_updated_at", "updated_at"),
    )

    @property
    def media_type(self) -> str:
        return "movie"



# TVShow (concrete table — all Resource columns live here)


class TVShow(Resource, Base):
    __tablename__ = "tv_shows"

    id       = Column(Integer, primary_key=True, autoincrement=True)
    media_id = Column(
        Integer,
        ForeignKey("media.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
        index=True,
    )
    number_of_seasons  = Column(Integer)
    number_of_episodes = Column(Integer)
    episode_run_time   = Column(JSONB)
    last_air_date      = Column(DateTime)
    in_production      = Column(Boolean, default=False)
    networks           = Column(JSONB)
    created_by         = Column(JSONB)
    show_type          = Column(String(50))

    media = relationship("Media", back_populates="tv_show")

    __table_args__ = (
        Index("uq_tv_shows_tmdb_id", "tmdb_id", unique=True),
        Index("idx_tv_shows_language_popularity", "original_language", "popularity"),
        Index("idx_tv_shows_release_rating", "release_date", "vote_average"),
        Index("idx_tv_shows_adult_popularity", "adult", "popularity"),
        Index("idx_tv_shows_updated_at", "updated_at"),
    )

    @property
    def media_type(self) -> str:
        return "tv"



# MediaEnrichment — one-to-one satellite for AI enrichment scores


class MediaEnrichment(Base):
    __tablename__ = "media_enrichment"

    media_id         = Column(Integer, ForeignKey("media.id", ondelete="CASCADE"), primary_key=True)
    narrative_dna    = Column(Text)
    themes           = Column(ARRAY(Text))
    tone_tags        = Column(ARRAY(Text))
    darkness_score   = Column(Integer)
    complexity_score = Column(Integer)
    energy_score     = Column(Integer)
    mood_scores      = Column(JSONB)
    context_scores   = Column(JSONB)
    craving_scores   = Column(JSONB)
    is_fully_scored  = Column(Boolean, nullable=False, default=False, server_default="false", index=True)
    enriched_at      = Column(DateTime, default=datetime.utcnow)

    media = relationship("Media", back_populates="enrichment")



# MediaEmbedding — one-to-one satellite for pgvector


class MediaEmbedding(Base):
    __tablename__ = "media_embedding"

    media_id      = Column(Integer, ForeignKey("media.id", ondelete="CASCADE"), primary_key=True)
    embedding     = Column(Vector(768), nullable=True)
    model_name    = Column(String(100), default="sentence-transformers/all-mpnet-base-v2")
    needs_rebuild = Column(Boolean, nullable=False, default=True)
    updated_at    = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    media = relationship("Media", back_populates="embedding")

    __table_args__ = (
        Index(
            "idx_media_embedding_hnsw",
            "embedding",
            postgresql_using="hnsw",
            postgresql_ops={"embedding": "vector_cosine_ops"},
            postgresql_with={"m": 16, "ef_construction": 64},
        ),
    )



# MediaAsset — one-to-many for images and videos

class MediaAsset(Base):
    """
    Stores multiple images/videos per title.

    asset_type: 'poster' | 'backdrop' | 'still' | 'trailer' | 'clip'
    source:     'tmdb'   | 'supabase' | 'youtube'
    """
    __tablename__ = "media_asset"

    id            = Column(Integer, primary_key=True, autoincrement=True)
    media_id      = Column(Integer, ForeignKey("media.id", ondelete="CASCADE"), nullable=False, index=True)
    asset_type    = Column(String(20), nullable=False)
    source        = Column(String(20), nullable=False)
    url           = Column(String(1000), nullable=False)
    file_path     = Column(String(500))
    language      = Column(String(10))
    width         = Column(Integer)
    height        = Column(Integer)
    is_primary    = Column(Boolean, nullable=False, default=False)
    display_order = Column(Integer, nullable=False, default=0)
    created_at    = Column(DateTime, default=datetime.utcnow, nullable=False)

    media = relationship("Media", back_populates="assets")

    __table_args__ = (
        Index("idx_media_asset_media_type", "media_id", "asset_type"),
        Index("idx_media_asset_primary",    "media_id", "asset_type", "is_primary"),
    )



# Supporting Models


class Genre(Base):
    __tablename__ = "genres"

    id        = Column(Integer, primary_key=True, autoincrement=True)
    tmdb_id   = Column(Integer, unique=True, nullable=True, index=True)
    name      = Column(String(100), unique=True, nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    media_items = relationship("Media", secondary=media_genres, back_populates="genres")


class Keyword(Base):
    __tablename__ = "keywords"

    id         = Column(Integer, primary_key=True, autoincrement=True)
    name       = Column(String(255), unique=True, nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    media_items = relationship("Media", secondary=media_keywords, back_populates="keywords")


class Cast(Base):
    __tablename__ = "cast"

    id           = Column(Integer, primary_key=True, autoincrement=True)
    tmdb_id      = Column(Integer, unique=True, index=True, nullable=False)
    name         = Column(String(255), nullable=False, index=True)
    profile_path = Column(String(255))
    popularity   = Column(Float)
    created_at   = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at   = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    media_items = relationship("Media", secondary=media_cast, back_populates="cast_members")
