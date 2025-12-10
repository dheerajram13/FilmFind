"""Tests for TextPreprocessor service."""

import pytest

from app.models.movie import Cast, Genre, Keyword, Movie
from app.services.text_preprocessor import TextPreprocessor


@pytest.fixture()
def sample_movie():
    """Create a sample movie with all fields populated."""
    movie = Movie(
        id=1,
        tmdb_id=12345,
        title="Inception",
        tagline="Your mind is the scene of the crime",
        overview="A thief who steals corporate secrets through dream-sharing technology.",
        original_language="en",
        popularity=100.0,
        vote_average=8.8,
        vote_count=10000,
        runtime=148,
    )

    # Add relationships
    movie.genres = [
        Genre(id=1, name="Action"),
        Genre(id=2, name="Science Fiction"),
        Genre(id=3, name="Thriller"),
    ]

    movie.keywords = [
        Keyword(id=1, name="dream"),
        Keyword(id=2, name="subconscious"),
        Keyword(id=3, name="heist"),
    ]

    movie.cast_members = [
        Cast(id=1, tmdb_id=6193, name="Leonardo DiCaprio"),
        Cast(id=2, tmdb_id=2524, name="Tom Hardy"),
        Cast(id=3, tmdb_id=27578, name="Elliot Page"),
    ]

    return movie


@pytest.fixture()
def minimal_movie():
    """Create a movie with only title."""
    return Movie(id=2, tmdb_id=67890, title="Minimal Movie")


class TestPreprocessMovie:
    """Tests for preprocess_movie method."""

    def test_preprocess_full_movie(self, sample_movie):
        """Test preprocessing with all fields populated."""
        text = TextPreprocessor.preprocess_movie(sample_movie)

        # Check all sections are present
        assert "Title: Inception" in text
        assert "Tagline: Your mind is the scene of the crime" in text
        assert "Plot: A thief who steals corporate secrets" in text
        assert "Genres: Action, Science Fiction, Thriller" in text
        assert "Keywords: dream, subconscious, heist" in text
        assert "Cast: Leonardo DiCaprio, Tom Hardy, Elliot Page" in text

    def test_preprocess_minimal_movie(self, minimal_movie):
        """Test preprocessing with only title."""
        text = TextPreprocessor.preprocess_movie(minimal_movie)

        assert "Title: Minimal Movie" in text
        assert "Tagline:" not in text
        assert "Plot:" not in text
        assert "Genres:" not in text

    def test_preprocess_handles_empty_strings(self):
        """Test that empty strings are filtered out."""
        movie = Movie(
            id=3,
            tmdb_id=11111,
            title="Test Movie",
            tagline="   ",  # Whitespace only
            overview="",  # Empty
        )

        text = TextPreprocessor.preprocess_movie(movie)

        assert "Title: Test Movie" in text
        assert "Tagline:" not in text  # Should be filtered out
        assert "Plot:" not in text  # Should be filtered out

    def test_preprocess_limits_keywords(self):
        """Test that keywords are limited to top 10."""
        movie = Movie(id=4, tmdb_id=22222, title="Keyword Test")

        # Add 15 keywords
        movie.keywords = [Keyword(id=i, name=f"keyword{i}") for i in range(15)]

        text = TextPreprocessor.preprocess_movie(movie)

        # Should only contain first 10
        assert "keyword0" in text
        assert "keyword9" in text
        assert "keyword10" not in text
        assert "keyword14" not in text

    def test_preprocess_limits_cast(self):
        """Test that cast is limited to top 5."""
        movie = Movie(id=5, tmdb_id=33333, title="Cast Test")

        # Add 8 cast members
        movie.cast_members = [
            Cast(id=i, tmdb_id=1000 + i, name=f"Actor{i}") for i in range(8)
        ]

        text = TextPreprocessor.preprocess_movie(movie)

        # Should only contain first 5
        assert "Actor0" in text
        assert "Actor4" in text
        assert "Actor5" not in text
        assert "Actor7" not in text


class TestCleanText:
    """Tests for _clean_text method."""

    def test_clean_excessive_whitespace(self):
        """Test removal of excessive whitespace."""
        text = "Title:  Inception\n\nTagline:   Mind    Crime\n\n\nGenres: Action"
        cleaned = TextPreprocessor._clean_text(text)

        # Should have single newlines and single spaces
        assert "  " not in cleaned
        assert "\n\n" not in cleaned

    def test_clean_preserves_structure(self):
        """Test that cleaning preserves line structure."""
        text = "Title: Movie\nPlot: A story\nGenres: Drama"
        cleaned = TextPreprocessor._clean_text(text)

        lines = cleaned.split("\n")
        assert len(lines) == 3
        assert lines[0] == "Title: Movie"
        assert lines[1] == "Plot: A story"
        assert lines[2] == "Genres: Drama"


class TestValidateText:
    """Tests for validate_text method."""

    def test_validate_good_text(self):
        """Test validation of good text."""
        text = "Title: Inception\nPlot: A story about dreams"
        assert TextPreprocessor.validate_text(text) is True

    def test_validate_rejects_none(self):
        """Test that None is rejected."""
        assert TextPreprocessor.validate_text(None) is False

    def test_validate_rejects_empty(self):
        """Test that empty string is rejected."""
        assert TextPreprocessor.validate_text("") is False
        assert TextPreprocessor.validate_text("   ") is False

    def test_validate_rejects_too_short(self):
        """Test that too-short text is rejected."""
        assert TextPreprocessor.validate_text("Short", min_length=10) is False

    def test_validate_rejects_no_alphanumeric(self):
        """Test that text with no alphanumeric chars is rejected."""
        assert TextPreprocessor.validate_text("!@#$%^&*()") is False

    def test_validate_accepts_min_length(self):
        """Test custom minimum length."""
        text = "12345"
        assert TextPreprocessor.validate_text(text, min_length=5) is True
        assert TextPreprocessor.validate_text(text, min_length=6) is False


class TestBatchPreprocess:
    """Tests for batch_preprocess method."""

    def test_batch_preprocess_multiple_movies(self, sample_movie, minimal_movie):
        """Test batch preprocessing of multiple movies."""
        movies = [sample_movie, minimal_movie]
        results = TextPreprocessor.batch_preprocess(movies)

        assert len(results) == 2
        assert results[0][0] == sample_movie.id
        assert results[1][0] == minimal_movie.id

        # Check text content
        assert "Inception" in results[0][1]
        assert "Minimal Movie" in results[1][1]

    def test_batch_preprocess_skips_invalid(self):
        """Test that invalid movies are skipped."""
        valid_movie = Movie(
            id=1,
            tmdb_id=111,
            title="Valid Movie",
            overview="Good overview",
        )

        invalid_movie = Movie(
            id=2,
            tmdb_id=222,
            title="",  # Empty title
            overview="",
        )

        movies = [valid_movie, invalid_movie]
        results = TextPreprocessor.batch_preprocess(movies)

        # Should only have 1 result (valid movie)
        assert len(results) == 1
        assert results[0][0] == valid_movie.id

    def test_batch_preprocess_handles_errors(self):
        """Test that preprocessing errors don't crash the batch."""
        good_movie = Movie(id=1, tmdb_id=111, title="Good")
        bad_movie = None  # Will cause an error

        # Should skip bad_movie without raising exception
        results = TextPreprocessor.batch_preprocess([good_movie, bad_movie])
        assert len(results) == 1
        assert results[0][0] == good_movie.id

    def test_batch_preprocess_empty_list(self):
        """Test batch preprocessing with empty list."""
        results = TextPreprocessor.batch_preprocess([])
        assert results == []
