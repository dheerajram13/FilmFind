"""
Tests for repository layer.

This module tests the Repository pattern implementation:
- BaseRepository CRUD operations
- MovieRepository domain-specific queries
- GenreRepository, KeywordRepository, CastRepository
"""

from datetime import datetime

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.database import Base
from app.models.movie import Cast, Genre, Movie
from app.repositories.movie_repository import (
    CastRepository,
    GenreRepository,
    KeywordRepository,
    MovieRepository,
)


# =============================================================================
# Test Fixtures
# =============================================================================


@pytest.fixture(scope="function")
def db_session():
    """Create an in-memory SQLite database for testing."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)

    TestingSessionLocal = sessionmaker(bind=engine)
    session = TestingSessionLocal()

    yield session

    session.close()
    Base.metadata.drop_all(engine)


@pytest.fixture()
def movie_repo(db_session):
    """Create MovieRepository instance."""
    return MovieRepository(db_session)


@pytest.fixture()
def genre_repo(db_session):
    """Create GenreRepository instance."""
    return GenreRepository(db_session)


@pytest.fixture()
def keyword_repo(db_session):
    """Create KeywordRepository instance."""
    return KeywordRepository(db_session)


@pytest.fixture()
def cast_repo(db_session):
    """Create CastRepository instance."""
    return CastRepository(db_session)


@pytest.fixture()
def sample_movies(db_session, genre_repo):
    """Create sample movies for testing queries."""
    # Create genres
    action = Genre(tmdb_id=28, name="Action")
    scifi = Genre(tmdb_id=878, name="Science Fiction")
    genre_repo.create(action)
    genre_repo.create(scifi)

    # Create movies
    movies = [
        Movie(
            tmdb_id=550,
            title="Fight Club",
            original_language="en",
            popularity=85.0,
            vote_average=8.4,
            vote_count=25000,
            release_date=datetime(1999, 10, 15),
            adult=False,
        ),
        Movie(
            tmdb_id=13,
            title="Forrest Gump",
            original_language="en",
            popularity=75.0,
            vote_average=8.5,
            vote_count=30000,
            release_date=datetime(1994, 7, 6),
            adult=False,
        ),
        Movie(
            tmdb_id=27205,
            title="Inception",
            original_language="en",
            popularity=90.0,
            vote_average=8.3,
            vote_count=35000,
            release_date=datetime(2010, 7, 16),
            adult=False,
            embedding_vector=[0.1, 0.2, 0.3],
        ),
        Movie(
            tmdb_id=155,
            title="The Dark Knight",
            original_language="en",
            popularity=95.0,
            vote_average=8.5,
            vote_count=40000,
            release_date=datetime(2008, 7, 18),
            adult=False,
        ),
        Movie(
            tmdb_id=99999,
            title="Telugu Movie",
            original_language="te",  # Telugu
            popularity=65.0,
            vote_average=7.5,
            vote_count=5000,
            release_date=datetime(2020, 1, 1),
            adult=False,
        ),
    ]

    for movie in movies:
        db_session.add(movie)

    # Add genres to some movies
    movies[2].genres.append(action)  # Inception
    movies[2].genres.append(scifi)
    movies[3].genres.append(action)  # The Dark Knight

    db_session.commit()

    return movies


# =============================================================================
# BaseRepository Tests (via MovieRepository)
# =============================================================================


class TestBaseRepository:
    """Tests for BaseRepository CRUD operations."""

    def test_create(self, movie_repo):
        """Test creating an entity."""
        movie = Movie(tmdb_id=123, title="Test Movie")
        created = movie_repo.create(movie)

        assert created.id is not None
        assert created.tmdb_id == 123
        assert created.title == "Test Movie"

    def test_get_by_id(self, movie_repo, sample_movies):
        """Test retrieving entity by ID."""
        movie = sample_movies[0]
        retrieved = movie_repo.get_by_id(movie.id)

        assert retrieved is not None
        assert retrieved.id == movie.id
        assert retrieved.title == movie.title

    def test_get_by_id_not_found(self, movie_repo):
        """Test retrieving non-existent entity."""
        retrieved = movie_repo.get_by_id(99999)
        assert retrieved is None

    def test_get_all(self, movie_repo, sample_movies):
        """Test retrieving all entities."""
        movies = movie_repo.get_all(limit=100)
        assert len(movies) == len(sample_movies)

    def test_get_all_pagination(self, movie_repo, sample_movies):
        """Test pagination in get_all."""
        # Get first 2 movies
        movies_page1 = movie_repo.get_all(skip=0, limit=2)
        assert len(movies_page1) == 2

        # Get next 2 movies
        movies_page2 = movie_repo.get_all(skip=2, limit=2)
        assert len(movies_page2) == 2

        # Ensure different movies
        assert movies_page1[0].id != movies_page2[0].id

    def test_count(self, movie_repo, sample_movies):
        """Test counting entities."""
        count = movie_repo.count()
        assert count == len(sample_movies)

    def test_exists(self, movie_repo, sample_movies):
        """Test checking if entity exists."""
        movie = sample_movies[0]
        assert movie_repo.exists(movie.id) is True
        assert movie_repo.exists(99999) is False

    def test_delete(self, movie_repo, sample_movies):
        """Test deleting an entity."""
        movie = sample_movies[0]
        deleted = movie_repo.delete(movie.id)

        assert deleted is True
        assert movie_repo.get_by_id(movie.id) is None

    def test_delete_not_found(self, movie_repo):
        """Test deleting non-existent entity."""
        deleted = movie_repo.delete(99999)
        assert deleted is False


# =============================================================================
# MovieRepository Tests
# =============================================================================


class TestMovieRepository:
    """Tests for MovieRepository domain-specific queries."""

    def test_find_by_tmdb_id(self, movie_repo, sample_movies):
        """Test finding movie by TMDB ID."""
        movie = movie_repo.find_by_tmdb_id(550)  # Fight Club

        assert movie is not None
        assert movie.title == "Fight Club"
        assert movie.tmdb_id == 550

    def test_find_by_tmdb_id_not_found(self, movie_repo):
        """Test finding non-existent TMDB ID."""
        movie = movie_repo.find_by_tmdb_id(88888)
        assert movie is None

    def test_search_by_title(self, movie_repo, sample_movies):
        """Test searching movies by title."""
        # Search for "Club" should match "Fight Club"
        results = movie_repo.search_by_title("Club")

        assert len(results) > 0
        assert any(m.title == "Fight Club" for m in results)

    def test_search_by_title_case_insensitive(self, movie_repo, sample_movies):
        """Test case-insensitive title search."""
        results = movie_repo.search_by_title("FIGHT")

        assert len(results) > 0
        assert any(m.title == "Fight Club" for m in results)

    def test_filter_by_language(self, movie_repo, sample_movies):
        """Test filtering movies by language."""
        # Filter English movies
        en_movies = movie_repo.filter_by_language("en")
        assert len(en_movies) == 4

        # Filter Telugu movies
        te_movies = movie_repo.filter_by_language("te")
        assert len(te_movies) == 1
        assert te_movies[0].title == "Telugu Movie"

    def test_filter_by_year_range(self, movie_repo, sample_movies):
        """Test filtering movies by year range."""
        # Movies from 2000-2010
        movies = movie_repo.filter_by_year_range(start_year=2000, end_year=2010)

        assert len(movies) == 2  # Inception (2010), Dark Knight (2008)

    def test_get_popular(self, movie_repo, sample_movies):
        """Test getting popular movies."""
        popular = movie_repo.get_popular(limit=3, min_vote_count=10000)

        # Should be ordered by popularity (descending)
        assert popular[0].title == "The Dark Knight"  # popularity=95.0
        assert popular[1].title == "Inception"  # popularity=90.0

    def test_get_top_rated(self, movie_repo, sample_movies):
        """Test getting top-rated movies."""
        top_rated = movie_repo.get_top_rated(limit=3, min_vote_count=10000)

        # Should include high-rated movies (8.5, 8.5, 8.4, 8.3)
        assert len(top_rated) >= 2

    def test_get_movies_without_embeddings(self, movie_repo, sample_movies):
        """Test finding movies without embeddings."""
        movies = movie_repo.get_movies_without_embeddings(limit=10)

        # Only one movie has embedding (Inception)
        assert len(movies) == 4

        # Verify none have embeddings
        for movie in movies:
            assert movie.embedding_vector is None

    def test_get_movies_with_embeddings(self, movie_repo, sample_movies):
        """Test finding movies with embeddings."""
        movies = movie_repo.get_movies_with_embeddings(limit=10)

        assert len(movies) == 1
        assert movies[0].title == "Inception"

    def test_count_movies_with_embeddings(self, movie_repo, sample_movies):
        """Test counting movies with embeddings."""
        count = movie_repo.count_movies_with_embeddings()
        assert count == 1

    def test_upsert_movie_insert(self, movie_repo):
        """Test upserting a new movie (insert)."""
        movie_data = {
            "tmdb_id": 777,
            "title": "New Movie",
            "original_language": "en",
        }

        movie = movie_repo.upsert_movie(movie_data)

        assert movie.id is not None
        assert movie.tmdb_id == 777
        assert movie.title == "New Movie"

    def test_upsert_movie_update(self, movie_repo, sample_movies):
        """Test upserting an existing movie (update)."""
        movie_data = {
            "tmdb_id": 550,  # Existing Fight Club
            "title": "Fight Club (Updated)",
            "popularity": 99.9,
        }

        movie = movie_repo.upsert_movie(movie_data)

        assert movie.tmdb_id == 550
        assert movie.title == "Fight Club (Updated)"
        assert movie.popularity == 99.9

    def test_get_total_movies(self, movie_repo, sample_movies):
        """Test counting total movies."""
        total = movie_repo.get_total_movies()
        assert total == len(sample_movies)


# =============================================================================
# GenreRepository Tests
# =============================================================================


class TestGenreRepository:
    """Tests for GenreRepository."""

    def test_find_by_name(self, genre_repo):
        """Test finding genre by name."""
        genre = Genre(tmdb_id=1, name="Comedy")
        genre_repo.create(genre)

        found = genre_repo.find_by_name("Comedy")
        assert found is not None
        assert found.name == "Comedy"

    def test_find_by_tmdb_id(self, genre_repo):
        """Test finding genre by TMDB ID."""
        genre = Genre(tmdb_id=12, name="Adventure")
        genre_repo.create(genre)

        found = genre_repo.find_by_tmdb_id(12)
        assert found is not None
        assert found.name == "Adventure"

    def test_get_all_genres(self, genre_repo):
        """Test getting all genres ordered by name."""
        genres_data = [
            Genre(tmdb_id=1, name="Comedy"),
            Genre(tmdb_id=2, name="Action"),
            Genre(tmdb_id=3, name="Drama"),
        ]

        for genre in genres_data:
            genre_repo.create(genre)

        all_genres = genre_repo.get_all_genres()

        assert len(all_genres) == 3
        # Should be ordered alphabetically
        assert all_genres[0].name == "Action"
        assert all_genres[1].name == "Comedy"
        assert all_genres[2].name == "Drama"


# =============================================================================
# CastRepository Tests
# =============================================================================


class TestCastRepository:
    """Tests for CastRepository."""

    def test_find_by_name(self, cast_repo):
        """Test finding cast member by name."""
        cast = Cast(tmdb_id=1, name="Tom Hanks")
        cast_repo.create(cast)

        found = cast_repo.find_by_name("Tom Hanks")
        assert found is not None
        assert found.name == "Tom Hanks"

    def test_search_by_name(self, cast_repo):
        """Test searching cast members by partial name."""
        cast_members = [
            Cast(tmdb_id=1, name="Tom Hanks", popularity=95.0),
            Cast(tmdb_id=2, name="Tom Cruise", popularity=90.0),
            Cast(tmdb_id=3, name="Leonardo DiCaprio", popularity=88.0),
        ]

        for cast in cast_members:
            cast_repo.create(cast)

        # Search for "Tom" should return both Hanks and Cruise
        results = cast_repo.search_by_name("Tom")

        assert len(results) == 2
        assert all("Tom" in c.name for c in results)
        # Should be ordered by popularity
        assert results[0].name == "Tom Hanks"
