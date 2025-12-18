"""
Signal Extractors - Extract individual ranking signals from movie data.

This module provides extractors for different ranking signals:
- Semantic similarity (from vector search)
- Genre/keyword match (exact matches with query)
- Popularity (normalized TMDB popularity)
- Rating quality (vote average and count)
- Recency (boost for recent releases)

Design Patterns:
- Strategy Pattern: Different extraction strategies for different signals
- Single Responsibility: Each extractor handles one signal type
"""

from datetime import UTC, datetime
import logging
import math
from typing import Any

from app.schemas.query import ParsedQuery


logger = logging.getLogger(__name__)


# Constants for extractor configuration
DEFAULT_MAX_LOG_POPULARITY = 7.0
DEFAULT_RECENCY_DECAY_BASE = 0.85
MIN_RECENCY_SCORE = 0.1
DEFAULT_YEAR_SCORE = 0.5
RATING_MIN_WEIGHT = 0.3
RATING_CONFIDENCE_FACTOR = 0.7

# Genre/keyword matching constants
GENRE_MATCH_SCORE = 0.3  # Score per matching genre
THEME_MATCH_SCORE = 0.1  # Score per matching theme/keyword
DEFAULT_NO_GENRE_SCORE = 0.5  # Default score when no genres specified
MAX_THEME_CONTRIBUTION = 0.5  # Maximum contribution from theme matches


class SignalExtractor:
    """Base class for signal extractors."""

    def extract(
        self, movie: dict[str, Any], parsed_query: ParsedQuery, context: dict[str, Any]
    ) -> float:
        """
        Extract signal score for a movie.

        Args:
            movie: Movie data dictionary with metadata
            parsed_query: Parsed user query with intent
            context: Additional context (e.g., all candidates for normalization)

        Returns:
            Signal score in range [0.0, 1.0]
        """
        raise NotImplementedError


class SemanticSimilarityExtractor(SignalExtractor):
    """
    Extract semantic similarity score from vector search.

    This signal represents how semantically similar the movie's
    content is to the user's query based on embeddings.
    """

    def extract(
        self, movie: dict[str, Any], parsed_query: ParsedQuery, context: dict[str, Any]
    ) -> float:
        """
        Extract semantic similarity score.

        Args:
            movie: Movie with 'similarity_score' from vector search
            parsed_query: Parsed query (not used for this extractor)
            context: Additional context (not used for this extractor)

        Returns:
            Similarity score in [0.0, 1.0]
        """
        _ = parsed_query, context  # Unused but part of interface
        # Similarity score already normalized from vector search
        similarity = movie.get("similarity_score", 0.0)
        return max(0.0, min(1.0, similarity))


class GenreKeywordMatchExtractor(SignalExtractor):
    """
    Extract genre and keyword match score.

    Measures how well the movie's genres and keywords match
    the query's intent (genres, themes, keywords).
    """

    def extract(
        self, movie: dict[str, Any], parsed_query: ParsedQuery, context: dict[str, Any]
    ) -> float:
        """
        Calculate genre/keyword match score.

        Scoring:
        - Each matching genre: +0.3 (up to 1.0)
        - Each matching theme/keyword: +0.1 (up to 0.5)

        Args:
            movie: Movie with 'genres' and 'keywords' lists
            parsed_query: Query with intent.genres and intent.themes
            context: Additional context (not used here)

        Returns:
            Match score in [0.0, 1.0]
        """
        _ = context  # Unused but part of interface
        score = 0.0

        # Extract movie metadata
        movie_genres = {g.lower() for g in movie.get("genres", [])}
        movie_keywords = {k.lower() for k in movie.get("keywords", [])}

        # Extract query intent
        intent = parsed_query.intent
        query_genres = set()
        query_themes = {t.lower() for t in intent.themes}

        # Add genre constraints if present
        if parsed_query.constraints and parsed_query.constraints.genres:
            query_genres = {g.lower() for g in parsed_query.constraints.genres}

        # Genre matching
        if query_genres:
            genre_matches = len(movie_genres & query_genres)
            score += min(1.0, genre_matches * GENRE_MATCH_SCORE)
        else:
            # If no genres specified, don't penalize
            score += DEFAULT_NO_GENRE_SCORE

        # Theme/keyword matching
        if query_themes:
            keyword_matches = len(movie_keywords & query_themes)
            score += min(MAX_THEME_CONTRIBUTION, keyword_matches * THEME_MATCH_SCORE)

        # Normalize to [0, 1]
        return min(1.0, score)


class PopularityExtractor(SignalExtractor):
    """
    Extract normalized popularity score.

    Uses TMDB popularity metric, normalized using log scale
    to prevent extremely popular movies from dominating.
    """

    def extract(
        self, movie: dict[str, Any], parsed_query: ParsedQuery, context: dict[str, Any]
    ) -> float:
        """
        Calculate normalized popularity score.

        Uses logarithmic scaling to compress the range:
        - popularity 0-10: maps to ~0.0-0.5
        - popularity 10-100: maps to ~0.5-0.8
        - popularity 100+: maps to ~0.8-1.0

        Args:
            movie: Movie with 'popularity' field
            parsed_query: Parsed query (not used for this extractor)
            context: Can contain 'max_popularity' for normalization

        Returns:
            Normalized popularity in [0.0, 1.0]
        """
        _ = parsed_query  # Unused but part of interface
        popularity = movie.get("popularity", 0.0)

        if popularity <= 0:
            return 0.0

        # Log scale normalization
        # log(1) = 0, log(100) ≈ 4.6, log(1000) ≈ 6.9
        log_popularity = math.log(popularity + 1)

        # Normalize: most popular movies have popularity ~500-1000
        # log(500) ≈ 6.2, log(1000) ≈ 6.9
        # We'll use 7.0 as our max for normalization
        max_log = context.get("max_log_popularity", DEFAULT_MAX_LOG_POPULARITY)

        normalized = log_popularity / max_log

        return min(1.0, normalized)


class RatingQualityExtractor(SignalExtractor):
    """
    Extract rating quality score.

    Combines vote average and vote count to prevent
    obscure movies with few votes but high ratings from
    dominating well-established highly-rated movies.
    """

    def extract(
        self, movie: dict[str, Any], parsed_query: ParsedQuery, context: dict[str, Any]
    ) -> float:
        """
        Calculate rating quality score.

        Uses weighted average considering both rating and vote count:
        - Base score: vote_average / 10.0
        - Vote confidence weight: sigmoid(vote_count / 100)

        Args:
            movie: Movie with 'rating' (vote_average) and 'vote_count'
            parsed_query: Parsed query (not used for this extractor)
            context: Additional context (not used for this extractor)

        Returns:
            Rating quality score in [0.0, 1.0]
        """
        _ = parsed_query, context  # Unused but part of interface
        rating = movie.get("rating", 0.0)
        vote_count = movie.get("vote_count", 0)

        if rating <= 0:
            return 0.0

        # Normalize rating to [0, 1]
        normalized_rating = rating / 10.0

        # Vote confidence: more votes = more confidence
        # Using sigmoid to map vote count to confidence weight
        # 100 votes = 0.5 weight, 500 votes = 0.88, 1000 votes = 0.95
        vote_confidence = self._sigmoid(vote_count / 100.0)

        # Weighted score: rating weighted by vote confidence
        # Minimum weight ensures ratings with few votes still count
        weight = RATING_MIN_WEIGHT + (RATING_CONFIDENCE_FACTOR * vote_confidence)
        weighted_score = normalized_rating * weight

        return min(1.0, weighted_score)

    @staticmethod
    def _sigmoid(x: float) -> float:
        """Sigmoid function: 1 / (1 + e^-x)"""
        try:
            return 1.0 / (1.0 + math.exp(-x))
        except OverflowError:
            return 0.0 if x < 0 else 1.0


class RecencyExtractor(SignalExtractor):
    """
    Extract recency score to boost recent releases.

    Provides a small boost for newer movies, with decay
    over time. Useful for discovery of new content.
    """

    def extract(
        self, movie: dict[str, Any], parsed_query: ParsedQuery, context: dict[str, Any]
    ) -> float:
        """
        Calculate recency score with exponential decay.

        Scoring strategy:
        - Released this year: 1.0
        - Released last year: 0.8
        - Released 2 years ago: 0.6
        - Released 3+ years ago: decays to 0.3
        - Very old movies (10+ years): ~0.1

        Args:
            movie: Movie with 'year' or 'release_date'
            parsed_query: Parsed query (not used for this extractor)
            context: Can contain 'current_year' (defaults to now)

        Returns:
            Recency score in [0.0, 1.0]
        """
        _ = parsed_query  # Unused but part of interface
        # Get release year
        year = movie.get("year")
        if not year:
            # Try to extract from release_date
            release_date = movie.get("release_date")
            if release_date:
                try:
                    if isinstance(release_date, str):
                        year = int(release_date[:4])
                    else:
                        year = release_date.year
                except (ValueError, AttributeError):
                    return DEFAULT_YEAR_SCORE  # Default for unknown

        if not year:
            return DEFAULT_YEAR_SCORE  # Default score for missing year

        # Get current year

        current_year = context.get("current_year", datetime.now(UTC).year)

        # Calculate years ago
        years_ago = current_year - year

        if years_ago < 0:
            # Future release (shouldn't happen, but handle gracefully)
            return 1.0

        # Exponential decay: score = base^years_ago
        # Using base 0.85 gives reasonable decay:
        # 0 years: 1.0, 1 year: 0.85, 2 years: 0.72, 5 years: 0.44
        score = math.pow(DEFAULT_RECENCY_DECAY_BASE, years_ago)

        # Floor at MIN_RECENCY_SCORE for very old content
        score = max(MIN_RECENCY_SCORE, score)

        return min(1.0, score)


class SignalExtractorFactory:
    """
    Factory for creating signal extractors.

    Provides centralized access to all extractors.
    """

    @staticmethod
    def create_all_extractors() -> dict[str, SignalExtractor]:
        """
        Create all available signal extractors.

        Returns:
            Dictionary mapping signal names to extractors
        """
        return {
            "semantic_similarity": SemanticSimilarityExtractor(),
            "genre_keyword_match": GenreKeywordMatchExtractor(),
            "popularity": PopularityExtractor(),
            "rating_quality": RatingQualityExtractor(),
            "recency": RecencyExtractor(),
        }

    @staticmethod
    def get_extractor(signal_name: str) -> SignalExtractor:
        """
        Get a specific signal extractor by name.

        Args:
            signal_name: Name of the signal

        Returns:
            Signal extractor instance

        Raises:
            ValueError: If signal name is unknown
        """
        extractors = SignalExtractorFactory.create_all_extractors()
        if signal_name not in extractors:
            msg = f"Unknown signal: {signal_name}. Available: {list(extractors.keys())}"
            raise ValueError(msg)
        return extractors[signal_name]
