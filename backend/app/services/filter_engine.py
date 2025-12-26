"""
Filter engine for applying constraints to movie candidates.

This module implements filtering logic to apply hard constraints from parsed queries
to a list of movie candidates. Filters include language, year range, rating,
runtime, genres, streaming providers, and adult content.

Design Patterns:
- Strategy Pattern: Different filter strategies can be applied
- Chain of Responsibility: Filters are applied sequentially
- Immutable Operations: Returns new filtered lists, doesn't modify inputs
"""

from collections.abc import Sequence
from datetime import UTC, datetime

from app.models.movie import Movie
from app.schemas.query import QueryConstraints
from app.utils.logger import get_logger
from app.utils.stats_utils import calculate_median
from app.utils.string_utils import normalize_string


logger = get_logger(__name__)


class FilterEngine:
    """
    Applies hard constraints to movie candidates.

    This engine takes a list of movie candidates and a set of constraints,
    then applies each constraint sequentially to filter the list.

    Example:
        >>> engine = FilterEngine()
        >>> constraints = QueryConstraints(
        ...     languages=["en"],
        ...     year_min=2000,
        ...     rating_min=7.0,
        ...     adult_content=False
        ... )
        >>> filtered = engine.apply_filters(movies, constraints)
    """

    def apply_filters(
        self, candidates: Sequence[Movie], constraints: QueryConstraints
    ) -> list[Movie]:
        """
        Apply all constraints to filter movie candidates.

        Args:
            candidates: List of movie candidates to filter
            constraints: Constraints to apply

        Returns:
            Filtered list of movies that satisfy all constraints

        Note:
            Filters are applied in order of selectivity (most selective first)
            to minimize processing on subsequent filters.
        """
        if not candidates:
            return []

        filtered = list(candidates)
        initial_count = len(filtered)

        logger.info(f"Applying filters to {initial_count} candidates")

        # Apply filters in order of expected selectivity (most selective first)

        # 1. Adult content filter (very selective, fast)
        filtered = self._filter_adult_content(filtered, constraints)

        # 2. Language filter (highly selective)
        filtered = self._filter_language(filtered, constraints)

        # 3. Year range filter (moderately selective)
        filtered = self._filter_year_range(filtered, constraints)

        # 4. Rating filter (moderately selective)
        filtered = self._filter_rating(filtered, constraints)

        # 5. Runtime filter (less selective)
        filtered = self._filter_runtime(filtered, constraints)

        # 6. Genre filters (can be selective or not)
        filtered = self._filter_genres(filtered, constraints)

        # 7. Streaming provider filter (least selective, but complex)
        filtered = self._filter_streaming_providers(filtered, constraints)

        # 8. Popularity filters
        filtered = self._filter_popularity(filtered, constraints)

        final_count = len(filtered)
        logger.info(
            f"Filtering complete: {initial_count} → {final_count} "
            f"({100 * final_count / initial_count:.1f}% retained)"
        )

        return filtered

    def _filter_adult_content(
        self, movies: list[Movie], constraints: QueryConstraints
    ) -> list[Movie]:
        """Filter based on adult content preference."""
        if constraints.adult_content:
            # No filtering needed if adult content is allowed
            return movies

        # Exclude adult content
        filtered = [m for m in movies if not m.adult]
        if len(filtered) < len(movies):
            logger.debug(f"Adult content filter: {len(movies)} → {len(filtered)}")
        return filtered

    def _filter_language(self, movies: list[Movie], constraints: QueryConstraints) -> list[Movie]:
        """Filter based on language constraints."""
        if not constraints.languages:
            return movies

        # Normalize language codes to lowercase
        allowed_languages = {normalize_string(lang) for lang in constraints.languages}

        filtered = [
            m
            for m in movies
            if m.original_language and normalize_string(m.original_language) in allowed_languages
        ]

        if len(filtered) < len(movies):
            logger.debug(
                f"Language filter ({', '.join(constraints.languages)}): "
                f"{len(movies)} → {len(filtered)}"
            )
        return filtered

    def _filter_year_range(self, movies: list[Movie], constraints: QueryConstraints) -> list[Movie]:
        """Filter based on release year range."""
        year_min = constraints.year_min
        year_max = constraints.year_max

        if year_min is None and year_max is None:
            return movies

        current_year = datetime.now(UTC).year
        year_max = year_max or current_year  # Default to current year if not specified

        filtered = []
        for movie in movies:
            # Skip movies without release date
            if not movie.release_date:
                continue

            year = movie.release_date.year

            # Apply year constraints
            if year_min and year < year_min:
                continue
            if year_max and year > year_max:
                continue

            filtered.append(movie)

        if len(filtered) < len(movies):
            range_str = f"{year_min or 'any'}-{year_max or 'any'}"
            logger.debug(f"Year range filter ({range_str}): {len(movies)} → {len(filtered)}")

        return filtered

    def _filter_rating(self, movies: list[Movie], constraints: QueryConstraints) -> list[Movie]:
        """Filter based on minimum rating."""
        if constraints.rating_min is None:
            return movies

        min_rating = constraints.rating_min

        filtered = [
            m for m in movies if m.vote_average is not None and m.vote_average >= min_rating
        ]

        if len(filtered) < len(movies):
            logger.debug(f"Rating filter (≥{min_rating}): {len(movies)} → {len(filtered)}")

        return filtered

    def _filter_runtime(self, movies: list[Movie], constraints: QueryConstraints) -> list[Movie]:
        """Filter based on runtime constraints."""
        runtime_min = constraints.runtime_min
        runtime_max = constraints.runtime_max

        if runtime_min is None and runtime_max is None:
            return movies

        filtered = []
        for movie in movies:
            # Skip movies without runtime
            if not movie.runtime:
                continue

            # Apply runtime constraints
            if runtime_min and movie.runtime < runtime_min:
                continue
            if runtime_max and movie.runtime > runtime_max:
                continue

            filtered.append(movie)

        if len(filtered) < len(movies):
            range_str = f"{runtime_min or 0}-{runtime_max or '∞'} min"
            logger.debug(f"Runtime filter ({range_str}): {len(movies)} → {len(filtered)}")

        return filtered

    def _filter_genres(self, movies: list[Movie], constraints: QueryConstraints) -> list[Movie]:
        """Filter based on genre requirements and exclusions."""
        required_genres = constraints.genres
        excluded_genres = constraints.exclude_genres

        if not required_genres and not excluded_genres:
            return movies

        filtered = []
        for movie in movies:
            # Get movie genre names (case-insensitive)
            movie_genres = {normalize_string(g.name) for g in movie.genres}

            # Check required genres (must have ALL)
            if required_genres:
                required_set = {normalize_string(g) for g in required_genres}
                if not required_set.issubset(movie_genres):
                    continue

            # Check excluded genres (must have NONE)
            if excluded_genres:
                excluded_set = {normalize_string(g) for g in excluded_genres}
                if movie_genres.intersection(excluded_set):
                    continue

            filtered.append(movie)

        if len(filtered) < len(movies):
            filter_desc = []
            if required_genres:
                filter_desc.append(f"required: {', '.join(required_genres)}")
            if excluded_genres:
                filter_desc.append(f"excluded: {', '.join(excluded_genres)}")
            logger.debug(
                f"Genre filter ({'; '.join(filter_desc)}): {len(movies)} → {len(filtered)}"
            )

        return filtered

    def _filter_streaming_providers(
        self, movies: list[Movie], constraints: QueryConstraints
    ) -> list[Movie]:
        """Filter based on streaming provider availability."""
        if not constraints.streaming_providers:
            return movies

        # Normalize provider names (case-insensitive)
        desired_providers = {normalize_string(p) for p in constraints.streaming_providers}

        filtered = []
        for movie in movies:
            # Skip movies without streaming data
            if not movie.streaming_providers:
                continue

            # Check if movie is available on any of the desired providers
            # streaming_providers format: {"Netflix": ["US", "GB"], "Prime": ["US"]}
            available_providers = {normalize_string(p) for p in movie.streaming_providers}

            if available_providers.intersection(desired_providers):
                filtered.append(movie)

        if len(filtered) < len(movies):
            logger.debug(
                f"Streaming provider filter ({', '.join(constraints.streaming_providers)}): "
                f"{len(movies)} → {len(filtered)}"
            )

        return filtered

    def _filter_popularity(self, movies: list[Movie], constraints: QueryConstraints) -> list[Movie]:
        """Filter based on popularity preferences."""
        # If both are False or both are True, no filtering needed
        if constraints.popular_only == constraints.hidden_gems:
            return movies

        if not movies:
            return movies

        # Calculate median popularity for threshold
        popularities = [m.popularity for m in movies if m.popularity is not None]
        if not popularities:
            return movies

        median_popularity = calculate_median(popularities)

        if constraints.popular_only:
            # Keep only movies above median popularity
            filtered = [
                m for m in movies if m.popularity is not None and m.popularity >= median_popularity
            ]
            logger.debug(
                f"Popular only filter (≥{median_popularity:.1f}): "
                f"{len(movies)} → {len(filtered)}"
            )
        else:  # hidden_gems
            # Keep only movies below median popularity
            filtered = [
                m for m in movies if m.popularity is not None and m.popularity < median_popularity
            ]
            logger.debug(
                f"Hidden gems filter (<{median_popularity:.1f}): "
                f"{len(movies)} → {len(filtered)}"
            )

        return filtered


class FilterStatistics:
    """
    Track filter statistics for debugging and optimization.

    This class helps analyze which filters are most selective and how
    many candidates are removed at each step.
    """

    def __init__(self) -> None:
        """Initialize filter statistics tracking."""
        self.filter_counts: dict[str, tuple[int, int]] = {}  # {filter_name: (before, after)}

    def record(self, filter_name: str, before_count: int, after_count: int) -> None:
        """
        Record filter application statistics.

        Args:
            filter_name: Name of the filter applied
            before_count: Number of candidates before filter
            after_count: Number of candidates after filter
        """
        self.filter_counts[filter_name] = (before_count, after_count)

    def get_selectivity(self, filter_name: str) -> float | None:
        """
        Calculate filter selectivity (percentage of candidates removed).

        Args:
            filter_name: Name of the filter

        Returns:
            Selectivity as percentage (0-100), or None if filter not recorded
        """
        if filter_name not in self.filter_counts:
            return None

        before, after = self.filter_counts[filter_name]
        if before == 0:
            return 0.0

        return 100.0 * (before - after) / before

    def get_summary(self) -> dict[str, dict[str, int | float]]:
        """
        Get summary of all filter statistics.

        Returns:
            Dictionary mapping filter names to their statistics
        """
        return {
            name: {
                "before": before,
                "after": after,
                "removed": before - after,
                "selectivity": self.get_selectivity(name) or 0.0,
            }
            for name, (before, after) in self.filter_counts.items()
        }

    def __repr__(self) -> str:
        """String representation of statistics."""
        summary = self.get_summary()
        lines = ["Filter Statistics:"]
        for name, stats in summary.items():
            lines.append(
                f"  {name}: {stats['before']} → {stats['after']} "
                f"({stats['selectivity']:.1f}% removed)"
            )
        return "\n".join(lines)
