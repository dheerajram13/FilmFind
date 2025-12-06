"""
TMDB data ingestion script
Fetches movies from TMDB API and stores in database

Usage:
    python scripts/ingest_tmdb.py --limit 1000 --strategy popular
    python scripts/ingest_tmdb.py --strategy genres --max-pages 5
"""
import argparse
from datetime import datetime
import json
from pathlib import Path
import sys
from typing import Any

from loguru import logger
from tqdm import tqdm


# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.config import settings
from app.services.TMDB.tmdb_service import TMDBService


class TMDBDataIngester:
    """
    TMDB data ingestion manager (SRP):
        Orchestrates data ingestion workflow
    """

    def __init__(self, output_dir: str = "data/raw", fetch_full_details: bool = False):
        """
        Initialize ingester

        Args:
            output_dir: Directory to save raw data
            fetch_full_details: If True, fetches complete movie details (slower)
                               If False, fetches basic data only (faster, recommended for bulk)
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.tmdb_service = TMDBService()
        self.fetch_full_details = fetch_full_details

    def save_movies_to_json(self, movies: list[dict[str, Any]], filename: str) -> None:
        """
        Save movies to JSON file

        Args:
            movies: List of movie dictionaries
            filename: Output filename
        """
        output_path = self.output_dir / filename
        logger.info(f"Saving {len(movies)} movies to {output_path}")

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(movies, f, indent=2, default=str, ensure_ascii=False)

        logger.success(f"Saved to {output_path}")

    def _fetch_popular_movies(self, max_pages: int = 10) -> list[dict[str, Any]]:
        """
        Fetch popular movies without saving (internal method)

        Args:
            max_pages: Maximum pages to fetch

        Returns:
            List of movie data
        """
        logger.info(f"Fetching popular movies (max {max_pages} pages)")
        return self.tmdb_service.fetch_popular_movies(
            max_pages=max_pages, fetch_full_details=self.fetch_full_details
        )

    def _fetch_top_rated_movies(self, max_pages: int = 10) -> list[dict[str, Any]]:
        """
        Fetch top rated movies without saving (internal method)

        Args:
            max_pages: Maximum pages to fetch

        Returns:
            List of movie data
        """
        logger.info(f"Fetching top rated movies (max {max_pages} pages)")
        return self.tmdb_service.fetch_top_rated_movies(
            max_pages=max_pages, fetch_full_details=self.fetch_full_details
        )

    def _fetch_by_genres(self, max_pages_per_genre: int = 5) -> list[dict[str, Any]]:
        """
        Fetch movies for all genres without saving (internal method)

        Args:
            max_pages_per_genre: Maximum pages per genre

        Returns:
            List of all unique movie data
        """
        logger.info("Fetching genre-based movies")

        # Get all genres
        genres = self.tmdb_service.get_all_genres()
        logger.info(f"Found {len(genres)} genres")

        all_movies = []
        seen_ids = set()

        # Fetch movies for each genre
        for genre in tqdm(genres, desc="Processing genres"):
            logger.info(f"Fetching movies for genre: {genre['name']} (ID: {genre['id']})")

            movies = self.tmdb_service.fetch_movies_by_genre(
                genre_id=genre["id"],
                max_pages=max_pages_per_genre,
                fetch_full_details=self.fetch_full_details,
            )

            # Deduplicate
            for movie in movies:
                if movie["tmdb_id"] not in seen_ids:
                    seen_ids.add(movie["tmdb_id"])
                    all_movies.append(movie)

        logger.info(f"Total unique movies collected: {len(all_movies)}")
        return all_movies

    def ingest_popular_movies(self, max_pages: int = 10, save: bool = True) -> list[dict[str, Any]]:
        """
        Ingest popular movies

        Args:
            max_pages: Maximum pages to fetch
            save: If True, saves to JSON file

        Returns:
            List of movie data
        """
        logger.info(f"Starting popular movies ingestion (max {max_pages} pages)")

        movies = self._fetch_popular_movies(max_pages=max_pages)

        if save:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            self.save_movies_to_json(movies, f"popular_movies_{timestamp}.json")

        return movies

    def ingest_top_rated_movies(
        self, max_pages: int = 10, save: bool = True
    ) -> list[dict[str, Any]]:
        """
        Ingest top rated movies

        Args:
            max_pages: Maximum pages to fetch
            save: If True, saves to JSON file

        Returns:
            List of movie data
        """
        logger.info(f"Starting top rated movies ingestion (max {max_pages} pages)")

        movies = self._fetch_top_rated_movies(max_pages=max_pages)

        if save:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            self.save_movies_to_json(movies, f"top_rated_movies_{timestamp}.json")

        return movies

    def ingest_by_genres(
        self, max_pages_per_genre: int = 5, save: bool = True
    ) -> list[dict[str, Any]]:
        """
        Ingest movies for all genres

        Args:
            max_pages_per_genre: Maximum pages per genre
            save: If True, saves to JSON file

        Returns:
            List of all movie data
        """
        logger.info("Starting genre-based ingestion")

        all_movies = self._fetch_by_genres(max_pages_per_genre=max_pages_per_genre)

        if save:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            self.save_movies_to_json(all_movies, f"genre_movies_{timestamp}.json")

        return all_movies

    def ingest_combined(
        self,
        max_pages_popular: int = 10,
        max_pages_top_rated: int = 10,
        max_pages_per_genre: int = 5,
    ) -> list[dict[str, Any]]:
        """
        Combined ingestion strategy for maximum coverage

        Fetches movies from multiple sources and deduplicates.
        Only saves a single combined JSON file (no individual files).

        Args:
            max_pages_popular: Pages for popular movies
            max_pages_top_rated: Pages for top rated movies
            max_pages_per_genre: Pages per genre

        Returns:
            List of all unique movies
        """

        logger.info("Starting combined ingestion strategy")

        all_movies = []
        seen_ids = set()

        # 1. Popular movies (use private method to avoid duplicate saves)
        logger.info("Step 1/3: Fetching popular movies")
        popular = self._fetch_popular_movies(max_pages=max_pages_popular)
        for movie in popular:
            if movie["tmdb_id"] not in seen_ids:
                seen_ids.add(movie["tmdb_id"])
                all_movies.append(movie)

        # 2. Top rated movies (use private method to avoid duplicate saves)
        logger.info("Step 2/3: Fetching top rated movies")
        top_rated = self._fetch_top_rated_movies(max_pages=max_pages_top_rated)
        for movie in top_rated:
            if movie["tmdb_id"] not in seen_ids:
                seen_ids.add(movie["tmdb_id"])
                all_movies.append(movie)

        # 3. Genre-based (use private method to avoid duplicate saves)
        logger.info("Step 3/3: Fetching by genres")
        genre_movies = self._fetch_by_genres(max_pages_per_genre=max_pages_per_genre)
        for movie in genre_movies:
            if movie["tmdb_id"] not in seen_ids:
                seen_ids.add(movie["tmdb_id"])
                all_movies.append(movie)

        logger.success(f"Combined ingestion complete: {len(all_movies)} unique movies")

        # Save only the combined result (no duplicate files)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.save_movies_to_json(all_movies, f"combined_movies_{timestamp}.json")

        return all_movies

    def close(self):
        """Cleanup resources"""
        self.tmdb_service.close()


def setup_logger(log_file: str = "logs/tmdb_ingestion.log"):
    """Setup logger with file and console output"""
    Path("logs").mkdir(exist_ok=True)

    logger.remove()  # Remove default handler
    logger.add(
        sys.stderr,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <level>{message}</level>",
        level="INFO",
    )
    logger.add(
        log_file,
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {message}",
        level="DEBUG",
        rotation="10 MB",
    )


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description="Ingest movie data from TMDB API")
    parser.add_argument(
        "--strategy",
        choices=["popular", "top_rated", "genres", "combined"],
        default="combined",
        help="Ingestion strategy",
    )
    parser.add_argument(
        "--max-pages", type=int, default=10, help="Maximum pages to fetch (for popular/top_rated)"
    )
    parser.add_argument(
        "--max-pages-per-genre",
        type=int,
        default=5,
        help="Maximum pages per genre (for genres/combined)",
    )
    parser.add_argument("--limit", type=int, help="Deprecated: use --max-pages instead")
    parser.add_argument(
        "--output-dir", type=str, default="data/raw", help="Output directory for raw JSON files"
    )
    parser.add_argument(
        "--log-file", type=str, default="logs/tmdb_ingestion.log", help="Log file path"
    )
    parser.add_argument(
        "--fetch-full-details",
        action="store_true",
        help="Fetch complete movie details (slower, includes cast/keywords). Default: False (faster, basic data only)",
    )
    parser.add_argument(
        "--fast",
        action="store_true",
        help="Alias for --no-fetch-full-details (fast mode, basic data only)",
    )

    args = parser.parse_args()

    # Handle --fast flag
    if args.fast:
        args.fetch_full_details = False

    # Handle deprecated --limit
    if args.limit:
        logger.warning("--limit is deprecated, using --max-pages instead")
        args.max_pages = args.limit // 20  # Approximate page conversion

    # Setup logging
    setup_logger(args.log_file)

    logger.info("=" * 60)
    logger.info("TMDB Data Ingestion Script - Module 1.1")
    logger.info("=" * 60)
    logger.info(f"Strategy: {args.strategy}")
    logger.info(f"Max pages: {args.max_pages}")
    logger.info(f"Max pages per genre: {args.max_pages_per_genre}")
    logger.info(f"Fetch full details: {args.fetch_full_details}")
    logger.info(f"Output directory: {args.output_dir}")

    if not args.fetch_full_details:
        logger.info("⚡ Fast mode enabled: Fetching basic data only (no cast/keywords)")
        logger.info("   Use --fetch-full-details for complete movie data (slower)")

    # Check API key
    if not settings.TMDB_API_KEY:
        logger.error("TMDB_API_KEY not found in environment variables!")
        logger.error("Please set TMDB_API_KEY in your .env file")
        return 1

    try:
        ingester = TMDBDataIngester(
            output_dir=args.output_dir, fetch_full_details=args.fetch_full_details
        )

        # Execute strategy
        if args.strategy == "popular":
            movies = ingester.ingest_popular_movies(max_pages=args.max_pages)
        elif args.strategy == "top_rated":
            movies = ingester.ingest_top_rated_movies(max_pages=args.max_pages)
        elif args.strategy == "genres":
            movies = ingester.ingest_by_genres(max_pages_per_genre=args.max_pages_per_genre)
        elif args.strategy == "combined":
            movies = ingester.ingest_combined(
                max_pages_popular=args.max_pages,
                max_pages_top_rated=args.max_pages,
                max_pages_per_genre=args.max_pages_per_genre,
            )

        logger.success("=" * 60)
        logger.success(f"Ingestion complete! Total movies: {len(movies)}")
        logger.success("=" * 60)

        ingester.close()
        return 0

    except KeyboardInterrupt:
        logger.warning("Ingestion interrupted by user")
        return 130
    except Exception as e:
        logger.exception(f"Ingestion failed with error: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
