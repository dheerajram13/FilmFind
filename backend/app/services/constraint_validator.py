"""
Constraint validator for validating and normalizing query constraints.

This module validates user-provided constraints, normalizes values,
and detects conflicting or invalid constraint combinations.

Design Patterns:
- Validator Pattern: Validates constraints before applying filters
- Builder Pattern: Builds normalized constraint objects
- Chain of Responsibility: Multiple validation rules applied sequentially
"""

from datetime import UTC, datetime

from pydantic import ValidationError

from app.schemas.query import MediaType, QueryConstraints
from app.utils.logger import get_logger
from app.utils.string_utils import normalize_string_list


logger = get_logger(__name__)


class ConstraintValidationError(Exception):
    """Raised when constraint validation fails."""


class ConstraintValidator:
    """
    Validates and normalizes query constraints.

    This validator ensures that constraints are valid, consistent, and
    properly formatted before being passed to the filter engine.

    Example:
        >>> validator = ConstraintValidator()
        >>> constraints = QueryConstraints(year_min=2020, year_max=2010)
        >>> validated = validator.validate(constraints)  # Raises error
    """

    def __init__(self) -> None:
        """Initialize constraint validator."""
        self.current_year = datetime.now(UTC).year

    def validate(self, constraints: QueryConstraints) -> QueryConstraints:
        """
        Validate and normalize constraints.

        Args:
            constraints: Constraints to validate

        Returns:
            Validated and normalized constraints

        Raises:
            ConstraintValidationError: If constraints are invalid
        """
        try:
            # Run all validation checks
            self._validate_year_range(constraints)
            self._validate_runtime_range(constraints)
            self._validate_rating(constraints)
            self._validate_media_type(constraints)
            self._validate_languages(constraints)
            self._validate_popularity_flags(constraints)

            # Normalize values
            normalized = self._normalize_constraints(constraints)

            logger.debug(f"Constraints validated successfully: {normalized}")
            return normalized

        except ValidationError as e:
            msg = f"Constraint validation failed: {e}"
            logger.error(msg)
            raise ConstraintValidationError(msg) from e

    def _validate_year_range(self, constraints: QueryConstraints) -> None:
        """
        Validate year range constraints.

        Checks:
        - year_min <= year_max
        - year_max <= current year (can't filter for future years)
        - year_min >= 1900 (earliest films)
        """
        year_min = constraints.year_min
        year_max = constraints.year_max

        if year_min is not None and year_min < 1900:
            msg = f"year_min ({year_min}) must be >= 1900"
            raise ConstraintValidationError(msg)

        if year_max is not None and year_max > self.current_year + 5:
            # Allow up to 5 years in the future for announced films
            msg = f"year_max ({year_max}) must be <= {self.current_year + 5}"
            raise ConstraintValidationError(msg)

        if year_min is not None and year_max is not None and year_min > year_max:
            msg = f"year_min ({year_min}) must be <= year_max ({year_max})"
            raise ConstraintValidationError(msg)

    def _validate_runtime_range(self, constraints: QueryConstraints) -> None:
        """
        Validate runtime range constraints.

        Checks:
        - runtime_min >= 0
        - runtime_max >= runtime_min
        - runtime values are reasonable (< 600 minutes = 10 hours)
        """
        runtime_min = constraints.runtime_min
        runtime_max = constraints.runtime_max

        if runtime_min is not None and runtime_min < 0:
            msg = f"runtime_min ({runtime_min}) must be >= 0"
            raise ConstraintValidationError(msg)

        if runtime_max is not None and runtime_max > 600:
            # Longest films are typically under 10 hours
            msg = f"runtime_max ({runtime_max}) is unreasonably high (> 600 minutes)"
            raise ConstraintValidationError(msg)

        if runtime_min is not None and runtime_max is not None and runtime_min > runtime_max:
            msg = f"runtime_min ({runtime_min}) must be <= runtime_max ({runtime_max})"
            raise ConstraintValidationError(msg)

    def _validate_rating(self, constraints: QueryConstraints) -> None:
        """
        Validate rating constraint.

        Checks:
        - rating_min is in valid range (0-10)
        """
        rating_min = constraints.rating_min

        if rating_min is not None and (rating_min < 0 or rating_min > 10):
            msg = f"rating_min ({rating_min}) must be between 0 and 10"
            raise ConstraintValidationError(msg)

    def _validate_media_type(self, constraints: QueryConstraints) -> None:
        """
        Validate media type constraint.

        Checks:
        - media_type is a valid MediaType enum value
        """
        if constraints.media_type is not None:
            valid_types = {MediaType.MOVIE, MediaType.TV_SHOW, MediaType.BOTH}
            if constraints.media_type not in valid_types:
                msg = f"Invalid media_type: {constraints.media_type}"
                raise ConstraintValidationError(msg)

    def _validate_languages(self, constraints: QueryConstraints) -> None:
        """
        Validate language constraints.

        Checks:
        - Language codes are 2-character ISO 639-1 codes
        """
        if not constraints.languages:
            return

        for lang in constraints.languages:
            if not isinstance(lang, str) or len(lang) != 2:
                msg = f"Invalid language code: {lang} (must be 2-character ISO 639-1 code)"
                logger.warning(msg)
                # Don't raise error, just warn and continue

    def _validate_popularity_flags(self, constraints: QueryConstraints) -> None:
        """
        Validate popularity preference flags.

        Checks:
        - popular_only and hidden_gems are not both True
        """
        if constraints.popular_only and constraints.hidden_gems:
            msg = "Cannot set both popular_only and hidden_gems to True"
            raise ConstraintValidationError(msg)

    def _normalize_constraints(self, constraints: QueryConstraints) -> QueryConstraints:
        """
        Normalize constraint values.

        Normalizations:
        - Convert language codes to lowercase
        - Trim whitespace from string values
        - Deduplicate lists
        - Sort lists for consistency

        Args:
            constraints: Original constraints

        Returns:
            Normalized constraints
        """
        # Create a dict of constraint values
        data = constraints.model_dump()

        # Normalize languages (lowercase, deduplicate, sort)
        if data["languages"]:
            data["languages"] = normalize_string_list(data["languages"])

        # Normalize genres (lowercase, deduplicate, sort)
        if data["genres"]:
            data["genres"] = normalize_string_list(data["genres"])

        if data["exclude_genres"]:
            data["exclude_genres"] = normalize_string_list(data["exclude_genres"])

        # Normalize streaming providers (lowercase, deduplicate, sort)
        if data["streaming_providers"]:
            data["streaming_providers"] = normalize_string_list(data["streaming_providers"])

        # Create new QueryConstraints with normalized values
        return QueryConstraints(**data)

    def get_active_constraints(self, constraints: QueryConstraints) -> list[str]:
        """
        Get list of active (non-default) constraints.

        Args:
            constraints: Constraints to analyze

        Returns:
            List of constraint names that are actively filtering
        """
        active = []

        if constraints.media_type and constraints.media_type != MediaType.BOTH:
            active.append(f"media_type={constraints.media_type}")

        if constraints.genres:
            active.append(f"genres={', '.join(constraints.genres)}")

        if constraints.exclude_genres:
            active.append(f"exclude_genres={', '.join(constraints.exclude_genres)}")

        if constraints.languages:
            active.append(f"languages={', '.join(constraints.languages)}")

        if constraints.year_min is not None:
            active.append(f"year_min={constraints.year_min}")

        if constraints.year_max is not None:
            active.append(f"year_max={constraints.year_max}")

        if constraints.rating_min is not None:
            active.append(f"rating_min={constraints.rating_min}")

        if constraints.runtime_min is not None:
            active.append(f"runtime_min={constraints.runtime_min}")

        if constraints.runtime_max is not None:
            active.append(f"runtime_max={constraints.runtime_max}")

        if constraints.streaming_providers:
            active.append(f"streaming={', '.join(constraints.streaming_providers)}")

        if not constraints.adult_content:
            active.append("adult_content=False")

        if constraints.popular_only:
            active.append("popular_only=True")

        if constraints.hidden_gems:
            active.append("hidden_gems=True")

        return active

    def detect_conflicts(self, constraints: QueryConstraints) -> list[str]:
        """
        Detect potential conflicts or issues in constraints.

        Args:
            constraints: Constraints to analyze

        Returns:
            List of detected conflicts/warnings
        """
        conflicts = []

        # Check for overly restrictive year range
        if constraints.year_min and constraints.year_max:
            year_range = constraints.year_max - constraints.year_min
            if year_range < 5:
                conflicts.append(f"Very narrow year range ({year_range} years) may limit results")

        # Check for overly restrictive runtime range
        if constraints.runtime_min and constraints.runtime_max:
            runtime_range = constraints.runtime_max - constraints.runtime_min
            if runtime_range < 30:
                conflicts.append(
                    f"Very narrow runtime range ({runtime_range} minutes) may limit results"
                )

        # Check for high rating threshold
        if constraints.rating_min and constraints.rating_min >= 8.0:
            conflicts.append(
                f"High rating threshold ({constraints.rating_min}) may significantly limit results"
            )

        # Check for multiple language constraints
        if len(constraints.languages) > 3:
            conflicts.append(
                f"Many language constraints ({len(constraints.languages)}) may be too broad"
            )

        # Check for conflicting genre requirements
        if constraints.genres and constraints.exclude_genres:
            overlap = set(constraints.genres).intersection(set(constraints.exclude_genres))
            if overlap:
                conflicts.append(
                    f"Genre appears in both required and excluded: {', '.join(overlap)}"
                )

        return conflicts


def validate_constraints(constraints: QueryConstraints) -> QueryConstraints:
    """
    Convenience function to validate constraints.

    Args:
        constraints: Constraints to validate

    Returns:
        Validated and normalized constraints

    Raises:
        ConstraintValidationError: If constraints are invalid
    """
    validator = ConstraintValidator()
    return validator.validate(constraints)
