"""
Tests for database models.

This module tests the Movie, Genre, Keyword, and Cast models including:
- Model creation
- Relationships
- Computed properties
- Constraints
"""

from datetime import datetime

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.database import Base
from app.models.movie import Cast, Genre, Keyword, Movie


# =============================================================================
# Test Fixtures
# =============================================================================


@pytest.fixture(scope="function")
def db_session():
    """
    Create an in-memory SQLite database for testing.

    This fixture creates a fresh database for each test and tears it down after.
    """
    # Create in-memory database
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)

    # Create session
    TestingSessionLocal = sessionmaker(bind=engine)
    session = TestingSessionLocal()

    yield session

    # Cleanup
    session.close()
    Base.metadata.drop_all(engine)


@pytest.fixture()
def sample_genre():
    """Create a sample genre for testing."""
    return Genre(
        tmdb_id=28,
        name="Action",
    )


@pytest.fixture()
def sample_keyword():
    """Create a sample keyword for testing."""
    return Keyword(
        tmdb_id=1234,
        name="time travel",
    )


@pytest.fixture()
def sample_cast():
    """Create a sample cast member for testing."""
    return Cast(
        tmdb_id=500,
        name="Tom Hanks",
        profile_path="/path/to/profile.jpg",
        popularity=95.5,
    )


@pytest.fixture()
def sample_movie(db_session, sample_genre, sample_keyword, sample_cast):
    """Create a complete movie with relationships for testing."""
    # Save related entities first
    db_session.add(sample_genre)
    db_session.add(sample_keyword)
    db_session.add(sample_cast)
    db_session.commit()

    movie = Movie(
        tmdb_id=550,
        title="Fight Club",
        original_title="Fight Club",
        overview="An insomniac office worker and a devil-may-care soap maker...",
        tagline="Mischief. Mayhem. Soap.",
        release_date=datetime(1999, 10, 15),
        runtime=139,
        adult=False,
        popularity=85.3,
        vote_average=8.4,
        vote_count=25000,
        original_language="en",
        poster_path="/pB8BM7pdSp6B6Ih7QZ4DrQ3PmJK.jpg",
        backdrop_path="/fCayJrkfRaCRCTh8GqN30f8oyQF.jpg",
        status="Released",
        budget=63000000,
        revenue=100853753,
        imdb_id="tt0137523",
        embedding_vector=[0.1, 0.2, 0.3],  # Mock embedding
        embedding_model="all-mpnet-base-v2",
        embedding_dimension=3,
        streaming_providers={"Netflix": ["US"], "Prime": ["GB"]},
    )

    movie.genres = [sample_genre]
    movie.keywords = [sample_keyword]
    movie.cast_members = [sample_cast]

    db_session.add(movie)
    db_session.commit()

    return movie


# =============================================================================
# Model Tests
# =============================================================================


class TestMovie:
    """Tests for Movie model."""

    def test_create_movie(self, db_session):
        """Test creating a basic movie."""
        movie = Movie(
            tmdb_id=123,
            title="Test Movie",
            release_date=datetime(2023, 1, 1),
        )

        db_session.add(movie)
        db_session.commit()

        assert movie.id is not None
        assert movie.tmdb_id == 123
        assert movie.title == "Test Movie"
        assert movie.created_at is not None
        assert movie.updated_at is not None

    def test_movie_with_relationships(self, sample_movie):
        """Test movie with genres, keywords, and cast."""
        assert len(sample_movie.genres) == 1
        assert sample_movie.genres[0].name == "Action"

        assert len(sample_movie.keywords) == 1
        assert sample_movie.keywords[0].name == "time travel"

        assert len(sample_movie.cast_members) == 1
        assert sample_movie.cast_members[0].name == "Tom Hanks"

    def test_movie_computed_properties(self, sample_movie):
        """Test computed properties on Movie model."""
        # Test year property
        assert sample_movie.year == 1999

        # Test poster_url property
        assert (
            sample_movie.poster_url
            == "https://image.tmdb.org/t/p/w500/pB8BM7pdSp6B6Ih7QZ4DrQ3PmJK.jpg"
        )

        # Test backdrop_url property
        assert (
            sample_movie.backdrop_url
            == "https://image.tmdb.org/t/p/original/fCayJrkfRaCRCTh8GqN30f8oyQF.jpg"
        )

        # Test runtime_formatted property
        assert sample_movie.runtime_formatted == "2h 19m"

        # Test has_embedding property
        assert sample_movie.has_embedding is True

    def test_movie_without_embedding(self, db_session):
        """Test has_embedding property when no embedding exists."""
        movie = Movie(
            tmdb_id=456,
            title="No Embedding Movie",
        )

        db_session.add(movie)
        db_session.commit()

        assert movie.has_embedding is False

    def test_movie_repr(self, sample_movie):
        """Test string representation of Movie."""
        repr_str = repr(sample_movie)
        assert "Movie" in repr_str
        assert str(sample_movie.tmdb_id) in repr_str
        assert sample_movie.title in repr_str

    def test_unique_tmdb_id_constraint(self, db_session):
        """Test that tmdb_id must be unique."""
        movie1 = Movie(tmdb_id=999, title="Movie 1")
        movie2 = Movie(tmdb_id=999, title="Movie 2")

        db_session.add(movie1)
        db_session.commit()

        db_session.add(movie2)

        with pytest.raises(Exception):  # IntegrityError for unique constraint
            db_session.commit()


class TestGenre:
    """Tests for Genre model."""

    def test_create_genre(self, db_session):
        """Test creating a genre."""
        genre = Genre(
            tmdb_id=12,
            name="Adventure",
        )

        db_session.add(genre)
        db_session.commit()

        assert genre.id is not None
        assert genre.tmdb_id == 12
        assert genre.name == "Adventure"

    def test_genre_repr(self, sample_genre):
        """Test string representation of Genre."""
        repr_str = repr(sample_genre)
        assert "Genre" in repr_str
        assert sample_genre.name in repr_str

    def test_unique_genre_name(self, db_session):
        """Test that genre names must be unique."""
        genre1 = Genre(tmdb_id=1, name="Comedy")
        genre2 = Genre(tmdb_id=2, name="Comedy")  # Same name, different tmdb_id

        db_session.add(genre1)
        db_session.commit()

        db_session.add(genre2)

        with pytest.raises(Exception):  # IntegrityError
            db_session.commit()


class TestKeyword:
    """Tests for Keyword model."""

    def test_create_keyword(self, db_session):
        """Test creating a keyword."""
        keyword = Keyword(
            tmdb_id=9999,
            name="artificial intelligence",
        )

        db_session.add(keyword)
        db_session.commit()

        assert keyword.id is not None
        assert keyword.tmdb_id == 9999
        assert keyword.name == "artificial intelligence"

    def test_keyword_repr(self, sample_keyword):
        """Test string representation of Keyword."""
        repr_str = repr(sample_keyword)
        assert "Keyword" in repr_str
        assert sample_keyword.name in repr_str


class TestCast:
    """Tests for Cast model."""

    def test_create_cast(self, db_session):
        """Test creating a cast member."""
        cast = Cast(
            tmdb_id=1234,
            name="Leonardo DiCaprio",
            profile_path="/path.jpg",
            popularity=88.9,
        )

        db_session.add(cast)
        db_session.commit()

        assert cast.id is not None
        assert cast.tmdb_id == 1234
        assert cast.name == "Leonardo DiCaprio"
        assert cast.popularity == 88.9

    def test_cast_profile_url(self, sample_cast):
        """Test profile_url computed property."""
        assert sample_cast.profile_url == "https://image.tmdb.org/t/p/w185/path/to/profile.jpg"

    def test_cast_without_profile(self, db_session):
        """Test cast member without profile image."""
        cast = Cast(
            tmdb_id=5678,
            name="Unknown Actor",
        )

        db_session.add(cast)
        db_session.commit()

        assert cast.profile_url is None

    def test_cast_repr(self, sample_cast):
        """Test string representation of Cast."""
        repr_str = repr(sample_cast)
        assert "Cast" in repr_str
        assert sample_cast.name in repr_str


# =============================================================================
# Integration Tests
# =============================================================================


class TestRelationships:
    """Tests for model relationships."""

    def test_movie_genre_relationship(self, db_session, sample_movie, sample_genre):
        """Test many-to-many relationship between movies and genres."""
        # Add another genre
        genre2 = Genre(tmdb_id=99, name="Thriller")
        sample_movie.genres.append(genre2)
        db_session.commit()

        assert len(sample_movie.genres) == 2
        assert genre2 in sample_movie.genres

        # Test reverse relationship
        assert sample_movie in sample_genre.movies

    def test_cascade_delete_movie(self, db_session, sample_movie):
        """Test that deleting a movie removes association entries."""
        movie_id = sample_movie.id

        # Delete movie
        db_session.delete(sample_movie)
        db_session.commit()

        # Check that movie is gone
        movie = db_session.query(Movie).filter_by(id=movie_id).first()
        assert movie is None

        # Genres, keywords, and cast should still exist (many-to-many)
        genres = db_session.query(Genre).all()
        assert len(genres) > 0
