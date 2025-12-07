#!/usr/bin/env python
"""
Database seeding script for FilmFind.

This script imports TMDB data from JSON files into the PostgreSQL database.
It uses the DatabaseSeederService to handle the import process with
proper transaction management and error handling.

Usage:
    # Show help
    python scripts/seed_database.py --help

    # Seed from default data directory
    python scripts/seed_database.py

    # Seed from specific directory
    python scripts/seed_database.py --data-dir data/raw

    # Seed specific file
    python scripts/seed_database.py --file data/raw/movie_550.json

    # Limit number of movies
    python scripts/seed_database.py --max-movies 1000

    # Custom batch size
    python scripts/seed_database.py --batch-size 50

    # Create tables before seeding (dev only, use Alembic in production)
    python scripts/seed_database.py --create-tables

Example Output:
    Found 1500 JSON files in data/raw
    Found 1500 movies to import
    Processing batch 1/15 (100 movies)
    Importing movies: 100%|██████████| 100/100 [00:15<00:00,  6.54it/s]
    Batch committed: 98 imported, 2 skipped, 0 failed
    ...
    ✓ Database seeding completed!
    Movies imported: 1470
    Movies skipped:  25
    Movies failed:   5
    Time taken: 3m 42s
"""

import argparse
from pathlib import Path
import sys
import time


# Add parent directory to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.core.database import engine
from app.models.movie import Base
from app.services.database_seeder import DatabaseSeederService
from app.utils.logger import get_logger


logger = get_logger(__name__)


def create_tables():
    """
    Create all database tables (if they don't exist).

    This is a convenience method for development.
    In production, use Alembic migrations instead.
    """
    logger.info("Creating database tables...")
    Base.metadata.create_all(bind=engine)
    logger.info("✓ Tables created successfully")


def main():
    """Main entry point for database seeding."""
    parser = argparse.ArgumentParser(
        description="Seed FilmFind database from TMDB JSON files",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )

    parser.add_argument(
        "--data-dir",
        type=str,
        default="data/raw",
        help="Directory containing TMDB JSON files (default: data/raw)",
    )

    parser.add_argument(
        "--file",
        type=str,
        help="Import from a specific JSON file instead of directory",
    )

    parser.add_argument(
        "--batch-size",
        type=int,
        default=100,
        help="Number of movies to process per batch (default: 100)",
    )

    parser.add_argument(
        "--max-movies",
        type=int,
        help="Maximum number of movies to import (default: all)",
    )

    parser.add_argument(
        "--create-tables",
        action="store_true",
        help="Create database tables before seeding (use Alembic migrations in production)",
    )

    args = parser.parse_args()

    # Banner
    print("=" * 70)
    print("FilmFind Database Seeder".center(70))
    print("=" * 70)
    print()

    start_time = time.time()

    try:
        # Create tables if requested
        if args.create_tables:
            create_tables()
            print()

        # Initialize seeder
        logger.info("Initializing database seeder...")
        seeder = DatabaseSeederService()

        # Seed database
        if args.file:
            # Single file import
            logger.info(f"Importing from file: {args.file}")
            stats = seeder.seed_from_file(args.file)
        else:
            # Directory import
            logger.info(f"Importing from directory: {args.data_dir}")
            stats = seeder.seed_from_directory(
                data_dir=args.data_dir,
                batch_size=args.batch_size,
                max_movies=args.max_movies,
            )

        # Print results
        elapsed = time.time() - start_time
        print()
        print("=" * 70)
        print("✓ Database seeding completed!".center(70))
        print("=" * 70)
        print()
        print(f"Movies imported:  {stats['movies_imported']:,}")
        print(f"Movies skipped:   {stats['movies_skipped']:,}")
        print(f"Movies failed:    {stats['movies_failed']:,}")
        print()
        print(f"Time taken: {_format_time(elapsed)}")
        print()

        # Return exit code based on failures
        if stats["movies_failed"] > 0:
            logger.warning(f"Completed with {stats['movies_failed']} failures")
            sys.exit(1)

    except FileNotFoundError as e:
        logger.error(f"❌ {e}")
        sys.exit(1)
    except KeyboardInterrupt:
        logger.warning("❌ Import cancelled by user")
        sys.exit(130)
    except Exception as e:
        logger.error(f"❌ Unexpected error: {e}", exc_info=True)
        sys.exit(1)


def _format_time(seconds: float) -> str:
    """Format seconds as human-readable time."""
    if seconds < 60:
        return f"{seconds:.1f}s"
    elif seconds < 3600:
        minutes = int(seconds // 60)
        secs = int(seconds % 60)
        return f"{minutes}m {secs}s"
    else:
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        return f"{hours}h {minutes}m"


if __name__ == "__main__":
    main()
