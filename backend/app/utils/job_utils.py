"""
Utility functions for background jobs.

Provides common patterns for job execution, timing, and statistics.
"""

from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any

from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.utils.logger import get_logger


logger = get_logger(__name__)


class JobTimer:
    """Context manager for timing job execution."""

    def __init__(self) -> None:
        """Initialize job timer."""
        self.start_time: datetime | None = None
        self.end_time: datetime | None = None

    def __enter__(self) -> "JobTimer":
        """Start timing."""
        self.start_time = datetime.now(UTC)
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Stop timing."""
        self.end_time = datetime.now(UTC)

    @property
    def duration_seconds(self) -> float:
        """
        Get duration in seconds.

        Returns:
            Duration in seconds (rounded to 2 decimal places)
        """
        if self.start_time and self.end_time:
            return round((self.end_time - self.start_time).total_seconds(), 2)
        return 0.0


class JobStats:
    """Job execution statistics tracker."""

    def __init__(self, **initial_stats: int) -> None:
        """
        Initialize job statistics.

        Args:
            **initial_stats: Initial stat counters (e.g., new_movies=0, errors=0)
        """
        self._stats: dict[str, int | float] = dict(initial_stats)
        self._stats.setdefault("errors", 0)

    def increment(self, key: str, amount: int = 1) -> None:
        """
        Increment a stat counter.

        Args:
            key: Stat key to increment
            amount: Amount to increment by
        """
        self._stats[key] = self._stats.get(key, 0) + amount

    def set(self, key: str, value: int | float) -> None:  # noqa: A003
        """
        Set a stat value.

        Args:
            key: Stat key
            value: Value to set
        """
        self._stats[key] = value

    def get(self, key: str, default: int | float = 0) -> int | float:
        """
        Get a stat value.

        Args:
            key: Stat key
            default: Default value if key doesn't exist

        Returns:
            Stat value
        """
        return self._stats.get(key, default)

    def to_dict(self) -> dict[str, int | float]:
        """
        Convert stats to dictionary.

        Returns:
            Stats dictionary
        """
        return self._stats.copy()


def execute_with_db(
    func: Callable[[Session, JobStats], None],
    job_name: str,
    initial_stats: dict[str, int] | None = None,
) -> dict[str, int | float]:
    """
    Execute a job function with database session and error handling.

    Provides:
    - Automatic database session management
    - Error handling with rollback
    - Execution timing
    - Statistics tracking
    - Logging

    Args:
        func: Job function that accepts (db: Session, stats: JobStats)
        job_name: Human-readable job name for logging
        initial_stats: Initial statistics counters

    Returns:
        Dictionary with job statistics including duration_seconds

    Example:
        ```python
        def my_job_logic(db: Session, stats: JobStats) -> None:
            movies = db.query(Movie).all()
            for movie in movies:
                # Process movie
                stats.increment("processed")

        stats = execute_with_db(my_job_logic, "My Job", {"processed": 0})
        ```
    """
    logger.info(f"Starting {job_name}")

    stats = JobStats(**(initial_stats or {}))
    db = SessionLocal()

    with JobTimer() as timer:
        try:
            func(db, stats)
            db.commit()

        except Exception as exc:
            logger.error(f"{job_name} failed: {exc}")
            db.rollback()
            stats.increment("errors")

        finally:
            db.close()

    # Add duration to stats
    stats.set("duration_seconds", timer.duration_seconds)

    # Log completion
    stats_dict = stats.to_dict()
    stats_str = ", ".join(f"{k}={v}" for k, v in stats_dict.items())
    logger.info(f"{job_name} completed: {stats_str}")

    return stats_dict


def batch_process(
    items: list[Any],
    process_func: Callable[[Any, Session, JobStats], None],
    db: Session,
    stats: JobStats,
    batch_size: int = 100,
    batch_stat_key: str = "processed",
) -> None:
    """
    Process items in batches with commits.

    Args:
        items: List of items to process
        process_func: Function to process each item (item, db, stats)
        db: Database session
        stats: Job statistics tracker
        batch_size: Number of items per batch before commit
        batch_stat_key: Stats key to track batch progress
    """
    total = len(items)
    logger.info(f"Processing {total} items in batches of {batch_size}")

    for i, item in enumerate(items, 1):
        try:
            process_func(item, db, stats)
            stats.increment(batch_stat_key)

            # Commit every batch_size items
            if i % batch_size == 0:
                db.commit()
                logger.info(f"Committed batch: {i}/{total} items processed")

        except Exception as exc:
            logger.error(f"Error processing item {i}: {exc}")
            stats.increment("errors")
            db.rollback()

    # Final commit for remaining items
    if total % batch_size != 0:
        db.commit()
