#!/usr/bin/env python3
"""
FAISS Index Builder Script - Module 1.4

Builds FAISS HNSW index from movie embeddings stored in the database.
This script:
1. Loads all embeddings from the database
2. Builds FAISS HNSW index for fast similarity search
3. Saves index and metadata to disk
4. Provides options for index configuration

Usage:
    # Build index with default settings
    python scripts/build_index.py

    # Custom HNSW parameters
    python scripts/build_index.py --m 64 --ef-construction 400

    # Load and test existing index
    python scripts/build_index.py --test-only

    # Rebuild index (overwrite existing)
    python scripts/build_index.py --force

    # Benchmark search performance
    python scripts/build_index.py --benchmark
"""

import argparse
import logging
from pathlib import Path
import sys
import time


# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

import numpy as np
from sqlalchemy import func

from app.core.database import SessionLocal
from app.models.movie import Movie
from app.services.vector_search import VectorSearchService


# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler()],
)
logger = logging.getLogger(__name__)


def load_embeddings_from_db() -> tuple[np.ndarray, list[int]]:
    """
    Load all movie embeddings from database.

    Returns:
        Tuple of (embeddings_array, movie_ids)
        - embeddings_array: numpy array of shape (n_movies, dimension)
        - movie_ids: list of movie IDs
    """
    logger.info("Loading embeddings from database...")

    db = SessionLocal()
    try:
        # Get total count of movies with embeddings
        total_count = db.query(func.count(Movie.id)).filter(
            Movie.embedding_vector.isnot(None)
        ).scalar()
        logger.info(f"Found {total_count} movies with embeddings in database")

        if total_count == 0:
            msg = (
                "No embeddings found in database. "
                "Please run 'python scripts/generate_embeddings.py' first."
            )
            raise ValueError(msg)

        # Get embedding dimension from the first movie
        query = db.query(Movie.id, Movie.embedding_vector).filter(
            Movie.embedding_vector.isnot(None)
        ).order_by(Movie.id)
        first_row = query.first()
        if first_row is None:
            msg = "No embeddings found in database."
            raise ValueError(msg)

        embedding_dim = len(first_row.embedding_vector)
        logger.info(f"Embedding dimension: {embedding_dim}")

        # Pre-allocate numpy array for better memory efficiency
        embeddings_array = np.empty((total_count, embedding_dim), dtype=np.float32)
        movie_ids = []

        # Stream results in batches to avoid loading all data into memory at once
        for i, (movie_id, embedding_vector) in enumerate(query.yield_per(1000)):
            movie_ids.append(movie_id)
            # Direct assignment - no intermediate list conversion needed
            embeddings_array[i] = embedding_vector

        logger.info(f"Loaded {len(movie_ids)} embeddings with shape {embeddings_array.shape}")

        return embeddings_array, movie_ids

    except Exception as e:
        logger.error(f"Failed to load embeddings: {e}")
        raise
    finally:
        db.close()


def build_index(
    embeddings: np.ndarray,
    movie_ids: list[int],
    m: int = 32,
    ef_construction: int = 200,
    force: bool = False,
) -> VectorSearchService:
    """
    Build FAISS index from embeddings.

    Args:
        embeddings: Embeddings array
        movie_ids: Movie IDs
        m: HNSW graph connectivity
        ef_construction: Construction search depth
        force: Overwrite existing index

    Returns:
        VectorSearchService instance with built index
    """
    service = VectorSearchService()

    # Check if index exists
    if service.index_path.exists() and not force:
        logger.warning(f"Index already exists at {service.index_path}")
        logger.warning("Use --force to overwrite or --test-only to test existing index")
        msg = "Index already exists. Use --force to overwrite."
        raise FileExistsError(msg)

    logger.info(f"Building FAISS index with M={m}, ef_construction={ef_construction}")
    start_time = time.time()

    # Build index
    service.build_index(embeddings, movie_ids, m=m, ef_construction=ef_construction)

    build_time = time.time() - start_time
    logger.info(f"Index built in {build_time:.2f} seconds")

    # Save index
    logger.info("Saving index to disk...")
    service.save_index()

    return service


def test_index(service: VectorSearchService, num_queries: int = 5) -> None:
    """
    Test the index with random queries.

    Args:
        service: VectorSearchService with loaded index
        num_queries: Number of test queries to run
    """
    logger.info(f"\nRunning {num_queries} test queries...")

    # Get embedding service
    embedding_service = get_embedding_service()

    # Test queries
    test_queries = [
        "dark sci-fi thriller about space",
        "romantic comedy with happy ending",
        "action movie with explosions",
        "horror film with jump scares",
        "animated family friendly adventure",
    ]

    total_search_time = 0

    for i, query in enumerate(test_queries[:num_queries], 1):
        logger.info(f"\nQuery {i}: '{query}'")

        # Generate query embedding
        query_embedding = embedding_service.generate_embedding(query)

        # Search
        start_time = time.time()
        results = service.search(query_embedding, k=5, ef_search=100)
        search_time = time.time() - start_time
        total_search_time += search_time

        logger.info(f"Search completed in {search_time*1000:.2f}ms")
        logger.info(f"Top 5 results: {results[:5]}")

    avg_search_time = total_search_time / num_queries
    logger.info(f"\nAverage search time: {avg_search_time*1000:.2f}ms")


def benchmark_search(service: VectorSearchService, num_queries: int = 100) -> None:
    """
    Benchmark search performance.

    Args:
        service: VectorSearchService with loaded index
        num_queries: Number of queries for benchmarking
    """
    logger.info(f"\n{'='*60}")
    logger.info("BENCHMARKING SEARCH PERFORMANCE")
    logger.info(f"{'='*60}")

    # Generate random query embeddings
    logger.info(f"Generating {num_queries} random query embeddings...")
    np.random.seed(42)
    query_embeddings = np.random.randn(num_queries, service.dimension).astype(np.float32)

    # Normalize using VectorNormalizer utility
    VectorNormalizer.normalize_l2(query_embeddings)

    # Benchmark different k values
    k_values = [1, 5, 10, 20, 50, 100]

    logger.info("\nIndex info:")
    logger.info(f"  Size: {service.size} vectors")
    logger.info(f"  Dimension: {service.dimension}")
    logger.info(f"  Type: {service.get_index_info()['index_type']}")

    for k in k_values:
        if k > service.size:
            continue

        times = []

        for query_emb in query_embeddings:
            start = time.time()
            service.search(query_emb, k=k, ef_search=100)
            times.append(time.time() - start)

        times = np.array(times)
        logger.info(f"\nk={k:3d}:")
        logger.info(f"  Mean:   {times.mean()*1000:6.2f}ms")
        logger.info(f"  Median: {np.median(times)*1000:6.2f}ms")
        logger.info(f"  P95:    {np.percentile(times, 95)*1000:6.2f}ms")
        logger.info(f"  P99:    {np.percentile(times, 99)*1000:6.2f}ms")
        logger.info(f"  Min:    {times.min()*1000:6.2f}ms")
        logger.info(f"  Max:    {times.max()*1000:6.2f}ms")

    # Benchmark different ef_search values
    logger.info(f"\n{'='*60}")
    logger.info("BENCHMARK: Effect of ef_search on latency")
    logger.info(f"{'='*60}")

    ef_values = [10, 50, 100, 200, 500]

    for ef in ef_values:
        times = []

        for query_emb in query_embeddings:
            start = time.time()
            service.search(query_emb, k=10, ef_search=ef)
            times.append(time.time() - start)

        times = np.array(times)
        logger.info(f"\nef_search={ef:3d}:")
        logger.info(f"  Mean:   {times.mean()*1000:6.2f}ms")
        logger.info(f"  P95:    {np.percentile(times, 95)*1000:6.2f}ms")

    logger.info(f"\n{'='*60}")
    logger.info("Benchmark complete!")
    logger.info(f"{'='*60}\n")


def main() -> None:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Build FAISS index from movie embeddings",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Build index with default settings
  python scripts/build_index.py

  # Custom HNSW parameters for better recall
  python scripts/build_index.py --m 64 --ef-construction 400

  # Rebuild existing index
  python scripts/build_index.py --force

  # Test existing index
  python scripts/build_index.py --test-only

  # Benchmark performance
  python scripts/build_index.py --benchmark

HNSW Parameters:
  --m: Graph connectivity (16-64, default: 32)
       Higher = better recall but more memory

  --ef-construction: Construction search depth (100-500, default: 200)
       Higher = better quality but slower build
        """,
    )

    parser.add_argument(
        "--m",
        type=int,
        default=32,
        help="HNSW M parameter (graph connectivity, default: 32)",
    )
    parser.add_argument(
        "--ef-construction",
        type=int,
        default=200,
        help="HNSW ef_construction parameter (default: 200)",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Force rebuild even if index exists",
    )
    parser.add_argument(
        "--test-only",
        action="store_true",
        help="Only test existing index (don't rebuild)",
    )
    parser.add_argument(
        "--benchmark",
        action="store_true",
        help="Run comprehensive performance benchmark",
    )
    parser.add_argument(
        "--num-test-queries",
        type=int,
        default=5,
        help="Number of test queries (default: 5)",
    )
    parser.add_argument(
        "--num-benchmark-queries",
        type=int,
        default=100,
        help="Number of benchmark queries (default: 100)",
    )

    args = parser.parse_args()

    try:
        logger.info("=" * 60)
        logger.info("FAISS Index Builder - Module 1.4")
        logger.info("=" * 60)

        if args.test_only:
            # Test existing index
            logger.info("Testing existing index...")
            service = VectorSearchService()
            service.load_index()

            info = service.get_index_info()
            logger.info("\nIndex info:")
            logger.info(f"  Size: {info['size']} vectors")
            logger.info(f"  Dimension: {info['dimension']}")
            logger.info(f"  Type: {info['index_type']}")
            logger.info(f"  Path: {info['index_path']}")

            test_index(service, num_queries=args.num_test_queries)

            if args.benchmark:
                benchmark_search(service, num_queries=args.num_benchmark_queries)

        else:
            # Build new index
            embeddings, movie_ids = load_embeddings_from_db()

            service = build_index(
                embeddings,
                movie_ids,
                m=args.m,
                ef_construction=args.ef_construction,
                force=args.force,
            )

            logger.info("\n" + "=" * 60)
            logger.info("Index built successfully!")
            logger.info("=" * 60)

            info = service.get_index_info()
            logger.info("\nIndex info:")
            logger.info(f"  Size: {info['size']} vectors")
            logger.info(f"  Dimension: {info['dimension']}")
            logger.info(f"  Type: {info['index_type']}")
            logger.info(f"  Saved to: {info['index_path']}")

            # Test the index
            test_index(service, num_queries=args.num_test_queries)

            if args.benchmark:
                benchmark_search(service, num_queries=args.num_benchmark_queries)

        logger.info("\n" + "=" * 60)
        logger.info("DONE!")
        logger.info("=" * 60)

    except Exception as e:
        logger.error(f"Error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
