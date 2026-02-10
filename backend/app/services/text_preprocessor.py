"""
Text preprocessing service for movie embeddings.

This module handles text preparation for embedding generation:
- Combines movie metadata into coherent text
- Cleans and normalizes text
- Handles missing/null values gracefully

Design Patterns:
- Service Pattern: Stateless text processing
- Single Responsibility: Only handles text preprocessing
"""

import logging

from app.core.config import settings
from app.models.media import Movie


logger = logging.getLogger(__name__)


class TextPreprocessor:
    """
    Preprocessor for converting movie data into embedding-ready text.

    This service combines various movie attributes
    such as title, plot, genres, etc.
    into a structured text format optimized for
    semantic embedding generation.
    """

    @staticmethod
    def preprocess_movie(movie: Movie) -> str:
        """
        Preprocess a movie into structured text for embedding.

        Combines movie metadata in a format that captures semantic meaning:
        - Title and tagline
        - Plot/overview
        - Genres and keywords
        - Top cast members

        Args:
            movie: Movie entity with relationships loaded

        Returns:
            Cleaned, structured text ready for embedding

        Example:
            ```python
            text = TextPreprocessor.preprocess_movie(movie)
            # Output:
            # "Title: Inception
            #  Tagline: Your mind is the scene of the crime
            #  Plot: A thief who steals corporate secrets...
            #  Genres: Action, Science Fiction, Thriller
            #  Keywords: dream, subconscious, heist
            #  Cast: Leonardo DiCaprio, Tom Hardy, ..."
            ```
        """
        parts = []

        # 1. Title (always present)
        if movie.title:
            parts.append(f"Title: {movie.title.strip()}")

        # 2. Tagline (if available)
        if movie.tagline:
            tagline = movie.tagline.strip()
            if tagline:
                parts.append(f"Tagline: {tagline}")

        # 3. Plot/Overview (primary semantic content)
        if movie.overview:
            overview = movie.overview.strip()
            if overview:
                parts.append(f"Plot: {overview}")

        # 4. Genres (important for categorization)
        if movie.genres:
            genre_names = [g.name for g in movie.genres]
            if genre_names:
                parts.append(f"Genres: {', '.join(genre_names)}")

        # 5. Keywords (semantic themes)
        if movie.keywords:
            # Limit to top N most relevant keywords
            keyword_names = [k.name for k in movie.keywords[: settings.MAX_KEYWORDS]]
            if keyword_names:
                parts.append(f"Keywords: {', '.join(keyword_names)}")

        # 6. Top Cast (for actor-based similarity)
        if movie.cast_members:
            # Top N cast members for brevity
            cast_names = [c.name for c in movie.cast_members[: settings.MAX_CAST_MEMBERS]]
            if cast_names:
                parts.append(f"Cast: {', '.join(cast_names)}")

        # Join all parts with newlines
        combined_text = "\n".join(parts)

        # Clean up any excessive whitespace
        return TextPreprocessor._clean_text(combined_text)

    @staticmethod
    def _clean_text(text: str) -> str:
        """
        Clean text by removing excessive whitespace and normalizing.

        Args:
            text: Input text

        Returns:
            Cleaned text
        """
        # Replace multiple newlines with single newline while preserving line structure
        lines = [line.strip() for line in text.split("\n") if line.strip()]

        # Clean up excessive whitespace within each line
        lines = [" ".join(line.split()) for line in lines]

        text = "\n".join(lines)

        return text.strip()

    @staticmethod
    def validate_text(text: str, min_length: int | None = None) -> bool:
        """
        Validate that text is suitable for embedding generation.

        Args:
            text: Preprocessed text
            min_length: Minimum acceptable text length (defaults to config MIN_TEXT_LENGTH)

        Returns:
            True if text is valid, False otherwise

        Example:
            ```python
            text = TextPreprocessor.preprocess_movie(movie)
            if TextPreprocessor.validate_text(text):
                embedding = embedding_service.generate(text)
            ```
        """
        if not text or not isinstance(text, str):
            return False

        # Use config default if not specified
        if min_length is None:
            min_length = settings.MIN_TEXT_LENGTH

        # Check minimum length
        if len(text.strip()) < min_length:
            return False

        # Check that text contains actual content (not just punctuation)
        has_alphanumeric = any(c.isalnum() for c in text)
        if not has_alphanumeric:
            return False

        return True

    @staticmethod
    def batch_preprocess(movies: list[Movie]) -> list[tuple[int, str]]:
        """
        Preprocess multiple movies in batch.

        Args:
            movies: List of Movie entities

        Returns:
            List of (movie_id, preprocessed_text) tuples
            Skips movies that don't have enough data

        Example:
            ```python
            movies = movie_repo.get_movies_without_embeddings(limit=100)
            batch = TextPreprocessor.batch_preprocess(movies)
            # [(1, "Title: Movie1..."), (2, "Title: Movie2..."), ...]
            ```
        """
        results = []

        for movie in movies:
            # Skip None entries
            if movie is None:
                logger.warning("Skipping None movie in batch preprocessing")
                continue

            try:
                text = TextPreprocessor.preprocess_movie(movie)

                # Validate before adding
                if TextPreprocessor.validate_text(text):
                    results.append((movie.id, text))

            except Exception as e:
                # Skip movies with preprocessing errors but log them
                title = getattr(movie, "title", "unknown")
                movie_id = getattr(movie, "id", "unknown")
                logger.warning(
                    f"Failed to preprocess movie {movie_id} ('{title}'): {e}",
                    exc_info=True,
                )
                continue

        return results
