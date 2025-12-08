#!/usr/bin/env python3
"""
CLI script for generating movie embeddings.

This script orchestrates the embedding generation pipeline:
- Fetches movies from database
- Preprocesses movie text
- Generates semantic embeddings
- Stores embeddings back to database

Usage:
    # Generate embeddings for all movies without them
    python scripts/generate_embeddings.py

    # Process only 1000 movies
    python scripts/generate_embeddings.py --limit 1000

    # Use custom batch sizes
    python scripts/generate_embeddings.py --embedding-batch-size 64 --db-batch-size 200

    # Regenerate all embeddings (including existing)
    python scripts/generate_embeddings.py --regenerate

    # Check current progress
    python scripts/generate_embeddings.py --progress

    # Validate existing embeddings
    python scripts/generate_embeddings.py --validate --sample-size 100

    # Resume failed processing
    python scripts/generate_embeddings.py --resume

Examples:
    # Standard workflow - generate embeddings for new movies
    python scripts/generate_embeddings.py

    # Quick test with small batch
    python scripts/generate_embeddings.py --limit 100

    # Production run with optimized batch sizes
    python scripts/generate_embeddings.py --embedding-batch-size 64 --db-batch-size 500
"""

import argparse
import logging
from pathlib import Path
import sys


# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.database import SessionLocal
from app.services.embedding_batch_processor import EmbeddingBatchProcessor


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler()],
)

logger = logging.getLogger(__name__)


def generate_embeddings(args):
    """Generate embeddings for movies."""
    logger.info("Starting embedding generation...")
    logger.info(
        f"Configuration: embedding_batch_size={args.embedding_batch_size}, "
        f"db_batch_size={args.db_batch_size}"
    )

    db = SessionLocal()

    try:
        processor = EmbeddingBatchProcessor(
            db=db,
            embedding_batch_size=args.embedding_batch_size,
            db_batch_size=args.db_batch_size,
        )

        # Process movies
        stats = processor.process_all_movies(
            limit=args.limit,
            skip_existing=not args.regenerate,
        )

        # Display results
        logger.info("=" * 60)
        logger.info("EMBEDDING GENERATION COMPLETE")
        logger.info("=" * 60)
        logger.info(f"Total movies found:    {stats['total_movies']}")
        logger.info(f"Successfully processed: {stats['processed']}")
        logger.info(f"Skipped (invalid):     {stats['skipped']}")
        logger.info(f"Failed:                {stats['failed']}")
        logger.info(f"Total batches:         {stats['batches']}")
        logger.info("=" * 60)

        # Show updated progress
        progress = processor.get_progress()
        logger.info(f"Overall progress: {progress['completed']}/{progress['total']} movies")
        logger.info(f"Completion: {progress['percentage']:.2f}%")
        logger.info(f"Remaining: {progress['remaining']} movies")

    except KeyboardInterrupt:
        logger.warning("Process interrupted by user")
        logger.info("Progress has been saved. Run with --resume to continue.")
        sys.exit(1)

    except Exception as e:
        logger.error(f"Embedding generation failed: {e}", exc_info=True)
        sys.exit(1)

    finally:
        db.close()


def show_progress(args):
    """Show current embedding generation progress."""
    db = SessionLocal()

    try:
        processor = EmbeddingBatchProcessor(db=db)
        progress = processor.get_progress()

        logger.info("=" * 60)
        logger.info("EMBEDDING GENERATION PROGRESS")
        logger.info("=" * 60)
        logger.info(f"Total movies:          {progress['total']}")
        logger.info(f"Completed:             {progress['completed']}")
        logger.info(f"Remaining:             {progress['remaining']}")
        logger.info(f"Progress:              {progress['percentage']:.2f}%")
        logger.info("=" * 60)

    except Exception as e:
        logger.error(f"Failed to get progress: {e}", exc_info=True)
        sys.exit(1)

    finally:
        db.close()


def validate_embeddings(args):
    """Validate existing embeddings."""
    logger.info(f"Validating {args.sample_size} random embeddings...")

    db = SessionLocal()

    try:
        processor = EmbeddingBatchProcessor(db=db)
        results = processor.validate_embeddings(sample_size=args.sample_size)

        logger.info("=" * 60)
        logger.info("EMBEDDING VALIDATION RESULTS")
        logger.info("=" * 60)
        logger.info(f"Checked:  {results['checked']}")
        logger.info(f"Valid:    {results['valid']}")
        logger.info(f"Invalid:  {results['invalid']}")
        logger.info("=" * 60)

        if results["errors"]:
            logger.warning(f"Found {len(results['errors'])} validation errors:")
            for error in results["errors"][:10]:  # Show first 10 errors
                logger.warning(f"  - {error}")
            if len(results["errors"]) > 10:
                logger.warning(f"  ... and {len(results['errors']) - 10} more errors")

    except Exception as e:
        logger.error(f"Validation failed: {e}", exc_info=True)
        sys.exit(1)

    finally:
        db.close()


def resume_processing(args):
    """Resume failed or interrupted processing."""
    logger.info("Resuming embedding generation for failed movies...")

    db = SessionLocal()

    try:
        processor = EmbeddingBatchProcessor(
            db=db,
            embedding_batch_size=args.embedding_batch_size,
            db_batch_size=args.db_batch_size,
        )

        stats = processor.reprocess_failed()

        logger.info("=" * 60)
        logger.info("RESUME PROCESSING COMPLETE")
        logger.info("=" * 60)
        logger.info(f"Processed: {stats['processed']}")
        logger.info(f"Failed:    {stats['failed']}")
        logger.info("=" * 60)

    except Exception as e:
        logger.error(f"Resume processing failed: {e}", exc_info=True)
        sys.exit(1)

    finally:
        db.close()


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Generate semantic embeddings for movies",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )

    # Operation modes (mutually exclusive)
    mode_group = parser.add_mutually_exclusive_group()
    mode_group.add_argument(
        "--progress",
        action="store_true",
        help="Show current progress without processing",
    )
    mode_group.add_argument(
        "--validate",
        action="store_true",
        help="Validate existing embeddings",
    )
    mode_group.add_argument(
        "--resume",
        action="store_true",
        help="Resume processing for movies without embeddings",
    )

    # Processing options
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Limit number of movies to process (default: all)",
    )
    parser.add_argument(
        "--regenerate",
        action="store_true",
        help="Regenerate embeddings for all movies (including existing)",
    )
    parser.add_argument(
        "--embedding-batch-size",
        type=int,
        default=32,
        help="Batch size for embedding generation (default: 32)",
    )
    parser.add_argument(
        "--db-batch-size",
        type=int,
        default=100,
        help="Batch size for database operations (default: 100)",
    )
    parser.add_argument(
        "--sample-size",
        type=int,
        default=100,
        help="Sample size for validation (default: 100)",
    )

    args = parser.parse_args()

    # Route to appropriate function
    if args.progress:
        show_progress(args)
    elif args.validate:
        validate_embeddings(args)
    elif args.resume:
        resume_processing(args)
    else:
        generate_embeddings(args)


if __name__ == "__main__":
    main()
