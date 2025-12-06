"""
Movie database models
"""
from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, Text, ForeignKey, Table, ARRAY
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import JSONB
from datetime import datetime
from app.core.database import Base


# Association tables
movie_genres = Table(
    'movie_genres',
    Base.metadata,
    Column('movie_id', Integer, ForeignKey('movies.id', ondelete='CASCADE'), primary_key=True),
    Column('genre_id', Integer, ForeignKey('genres.id', ondelete='CASCADE'), primary_key=True)
)

movie_keywords = Table(
    'movie_keywords',
    Base.metadata,
    Column('movie_id', Integer, ForeignKey('movies.id', ondelete='CASCADE'), primary_key=True),
    Column('keyword_id', Integer, ForeignKey('keywords.id', ondelete='CASCADE'), primary_key=True)
)

movie_cast = Table(
    'movie_cast',
    Base.metadata,
    Column('movie_id', Integer, ForeignKey('movies.id', ondelete='CASCADE'), primary_key=True),
    Column('cast_id', Integer, ForeignKey('cast.id', ondelete='CASCADE'), primary_key=True),
    Column('character_name', String(255)),
    Column('order_position', Integer)
)


class Movie(Base):
    """Movie model"""
    __tablename__ = "movies"

    id = Column(Integer, primary_key=True, index=True)
    tmdb_id = Column(Integer, unique=True, index=True, nullable=False)
    title = Column(String(500), nullable=False, index=True)
    original_title = Column(String(500))
    overview = Column(Text)
    tagline = Column(String(500))
    release_date = Column(DateTime, index=True)
    runtime = Column(Integer)  # in minutes
    adult = Column(Boolean, default=False)
    popularity = Column(Float, index=True)
    vote_average = Column(Float, index=True)
    vote_count = Column(Integer)
    original_language = Column(String(10), index=True)
    poster_path = Column(String(255))
    backdrop_path = Column(String(255))
    status = Column(String(50))  # Released, Post Production, etc.
    budget = Column(Integer)
    revenue = Column(Integer)
    imdb_id = Column(String(20))

    # Vector embeddings (stored as JSON array)
    embedding_vector = Column(JSONB)  # Main semantic embedding
    embedding_model = Column(String(100))  # Model version used
    embedding_dimension = Column(Integer)  # Vector dimension

    # Streaming providers (stored as JSON)
    streaming_providers = Column(JSONB)  # {"Netflix": ["US", "GB"], "Prime": ["US"]}

    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    genres = relationship("Genre", secondary=movie_genres, back_populates="movies")
    keywords = relationship("Keyword", secondary=movie_keywords, back_populates="movies")
    cast_members = relationship("Cast", secondary=movie_cast, back_populates="movies")


class Genre(Base):
    """Genre model"""
    __tablename__ = "genres"

    id = Column(Integer, primary_key=True, index=True)
    tmdb_id = Column(Integer, unique=True, index=True)
    name = Column(String(100), unique=True, nullable=False, index=True)

    # Relationships
    movies = relationship("Movie", secondary=movie_genres, back_populates="genres")


class Keyword(Base):
    """Keyword model"""
    __tablename__ = "keywords"

    id = Column(Integer, primary_key=True, index=True)
    tmdb_id = Column(Integer, unique=True, index=True)
    name = Column(String(255), unique=True, nullable=False, index=True)

    # Relationships
    movies = relationship("Movie", secondary=movie_keywords, back_populates="keywords")


class Cast(Base):
    """Cast/Crew model"""
    __tablename__ = "cast"

    id = Column(Integer, primary_key=True, index=True)
    tmdb_id = Column(Integer, unique=True, index=True, nullable=False)
    name = Column(String(255), nullable=False, index=True)
    profile_path = Column(String(255))
    popularity = Column(Float)

    # Relationships
    movies = relationship("Movie", secondary=movie_cast, back_populates="cast_members")


# Alias for association tables (for imports)
MovieGenre = movie_genres
MovieKeyword = movie_keywords
MovieCast = movie_cast
