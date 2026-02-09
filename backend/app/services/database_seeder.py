"""
Database seeding service for importing TMDB data into PostgreSQL.

This service reads TMDB JSON files from the data/raw directory and populates
the database using the Repository pattern. It handles:
- Genres, Keywords, Cast upsert (insert or update)
- Movie creation with relationships
- Batch processing for performance
- Transaction management
- Progress tracking

Design Patterns:
- Service Pattern: Business logic layer
- Repository Pattern: Data access abstraction
- Unit of Work: Transaction management
- Batch Processing: Performance optimization
"""

from datetime import datetime
import json
from pathlib import Path
from typing import Optional

from sqlalchemy.orm import Session
from tqdm import tqdm

from app.core.database import SessionLocal
from app.models.movie import Cast, Genre, Keyword, Movie
from app.repositories.movie_repository import (
    CastRepository,
    GenreRepository,
    KeywordRepository,
    MovieRepository,
)
from app.utils.logger import get_logger


logger = get_logger(__name__)


class DatabaseSeederService:
    """
    Service for seeding database from TMDB JSON files.

    This service orchestrates the import of TMDB data into the database,
    ensuring data integrity and performance through batching and transactions.
    """

    def __init__(self, db: Optional[Session] = None):
        """
        Initialize seeder service with database session.

        Args:
            db: SQLAlchemy session (if None, creates new session)
        """
        self.db = db or SessionLocal()
        self.owns_session = db is None  # Track if we created the session

        # Initialize repositories
        self.movie_repo = MovieRepository(self.db)
        self.genre_repo = GenreRepository(self.db)
        self.keyword_repo = KeywordRepository(self.db)
        self.cast_repo = CastRepository(self.db)

        # Caches for lookups (to avoid repeated DB queries)
        self._genre_cache: dict[int, Genre] = {}  # tmdb_id -> Genre
        self._keyword_cache: dict[int, Keyword] = {}  # tmdb_id -> Keyword
        self._cast_cache: dict[int, Cast] = {}  # tmdb_id -> Cast

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - cleanup session."""
        if self.owns_session:
            if exc_type is not None:
                self.db.rollback()
            self.db.close()

    # =============================================================================
    # Public Methods
    # =============================================================================

    def seed_from_directory(
        self,
        data_dir: str = "data/raw",
        batch_size: int = 100,
        max_movies: Optional[int] = None,
    ) -> dict[str, int]:
        """
        Seed database from all JSON files in directory.

        Args:
            data_dir: Directory containing TMDB JSON files
            batch_size: Number of movies to process in each batch
            max_movies: Maximum number of movies to import (None = all)

        Returns:
            Dictionary with import statistics:
                - movies_imported: Number of movies successfully imported
                - movies_skipped: Number of movies skipped (duplicates)
                - movies_failed: Number of movies that failed to import
                - genres_created: Number of genres created
                - keywords_created: Number of keywords created
                - cast_created: Number of cast members created

        Example:
            ```python
            seeder = DatabaseSeederService()
            stats = seeder.seed_from_directory("data/raw", max_movies=1000)
            print(f"Imported {stats['movies_imported']} movies")
            ```
        """
        data_path = Path(data_dir)
        if not data_path.exists():
            raise FileNotFoundError(f"Data directory not found: {data_dir}")

        # Find all JSON files
        json_files = list(data_path.glob("**/*.json"))
        if not json_files:
            logger.warning(f"No JSON files found in {data_dir}")
            return self._empty_stats()

        logger.info(f"Found {len(json_files)} JSON files in {data_dir}")

        # Load all movie data from JSON files
        all_movies = []
        for json_file in json_files:
            try:
                with open(json_file, encoding="utf-8") as f:
                    data = json.load(f)
                    # Handle both single movie and list of movies
                    if isinstance(data, list):
                        all_movies.extend(data)
                    else:
                        all_movies.append(data)
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse {json_file}: {e}")
                continue
            except Exception as e:
                logger.error(f"Error reading {json_file}: {e}")
                continue

        if max_movies:
            all_movies = all_movies[:max_movies]

        logger.info(f"Found {len(all_movies)} movies to import")

        # Import movies in batches
        return self._import_movies_batch(all_movies, batch_size)

    def seed_from_file(self, json_file: str) -> dict[str, int]:
        """
        Seed database from a single JSON file.

        Args:
            json_file: Path to JSON file containing TMDB movie data

        Returns:
            Import statistics dictionary
        """
        file_path = Path(json_file)
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {json_file}")

        with open(file_path, encoding="utf-8") as f:
            data = json.load(f)

        # Handle both single movie and list of movies
        movies = data if isinstance(data, list) else [data]

        return self._import_movies_batch(movies, batch_size=len(movies))

    # =============================================================================
    # Private Methods - Import Logic
    # =============================================================================

    def _import_movies_batch(
        self,
        movies_data: list[dict],
        batch_size: int = 100,
    ) -> dict[str, int]:
        """
        Import movies in batches for better performance.

        Args:
            movies_data: List of movie dictionaries from TMDB
            batch_size: Number of movies per batch

        Returns:
            Import statistics
        """
        stats = self._empty_stats()

        # Process in batches
        total_batches = (len(movies_data) + batch_size - 1) // batch_size

        for batch_idx in range(total_batches):
            start_idx = batch_idx * batch_size
            end_idx = min((batch_idx + 1) * batch_size, len(movies_data))
            batch = movies_data[start_idx:end_idx]

            logger.info(f"Processing batch {batch_idx + 1}/{total_batches} ({len(batch)} movies)")

            batch_stats = self._process_batch(batch)
            stats = self._merge_stats(stats, batch_stats)

        return stats

    def _process_batch(self, batch: list[dict]) -> dict[str, int]:
        """
        Process a single batch of movies within a transaction.

        Args:
            batch: List of movie dictionaries

        Returns:
            Statistics for this batch
        """
        stats = self._empty_stats()

        try:
            for movie_data in tqdm(batch, desc="Importing movies"):
                try:
                    result = self._import_single_movie(movie_data)
                    if result == "imported":
                        stats["movies_imported"] += 1
                    elif result == "skipped":
                        stats["movies_skipped"] += 1
                except Exception as e:
                    logger.error(f"Failed to import movie {movie_data.get('id', 'unknown')}: {e}")
                    stats["movies_failed"] += 1

            # Commit batch
            self.db.commit()
            logger.info(
                f"Batch committed: {stats['movies_imported']} imported, {stats['movies_skipped']} skipped, {stats['movies_failed']} failed"
            )

        except Exception as e:
            logger.error(f"Batch failed, rolling back: {e}")
            self.db.rollback()
            stats["movies_failed"] += len(batch)

        return stats

    def _import_single_movie(self, movie_data: dict) -> str:
        """
        Import a single movie with all relationships.

        Args:
            movie_data: Movie dictionary from TMDB API

        Returns:
            "imported" or "skipped"
        """
        # Support both 'id' and 'tmdb_id' field names
        tmdb_id = movie_data.get("id") or movie_data.get("tmdb_id")
        if not tmdb_id:
            raise ValueError("Movie data missing 'id' or 'tmdb_id' field")

        # Check if movie already exists
        existing = self.movie_repo.find_by_tmdb_id(tmdb_id)
        if existing:
            logger.debug(f"Movie {tmdb_id} already exists, skipping")
            return "skipped"

        # Create movie entity (pass tmdb_id separately)
        movie = self._create_movie_from_data(movie_data, tmdb_id)

        # Add relationships
        if "genres" in movie_data:
            movie.genres = [self._get_or_create_genre(g) for g in movie_data["genres"]]

        if "keywords" in movie_data and isinstance(movie_data["keywords"], dict):
            keywords_list = movie_data["keywords"].get("keywords", [])
            movie.keywords = [self._get_or_create_keyword(k) for k in keywords_list]

        if "credits" in movie_data and isinstance(movie_data["credits"], dict):
            cast_list = movie_data["credits"].get("cast", [])[:10]  # Top 10 cast
            movie.cast_members = [self._get_or_create_cast(c) for c in cast_list]

        # Save to database
        self.movie_repo.create(movie)

        return "imported"

    # =============================================================================
    # Private Methods - Entity Creation
    # =============================================================================

    def _create_movie_from_data(self, data: dict, tmdb_id: int) -> Movie:
        """
        Create Movie entity from TMDB data.

        Args:
            data: TMDB movie dictionary
            tmdb_id: TMDB ID of the movie

        Returns:
            Movie instance (not yet saved to DB)
        """
        # Parse release date - support both ISO format and datetime string
        release_date = None
        if data.get("release_date"):
            try:
                # Try ISO format first (YYYY-MM-DD)
                release_date = datetime.strptime(data["release_date"], "%Y-%m-%d")
            except ValueError:
                try:
                    # Try datetime format with time (YYYY-MM-DD HH:MM:SS)
                    release_date = datetime.strptime(data["release_date"], "%Y-%m-%d %H:%M:%S")
                except ValueError:
                    logger.warning(f"Invalid release date format: {data['release_date']}")

        # Extract streaming providers (if available)
        streaming_providers = None
        if "watch/providers" in data:
            streaming_providers = data["watch/providers"].get("results", {})

        return Movie(
            tmdb_id=tmdb_id,
            title=data.get("title", ""),
            original_title=data.get("original_title"),
            overview=data.get("overview"),
            tagline=data.get("tagline"),
            release_date=release_date,
            runtime=data.get("runtime"),
            adult=data.get("adult", False),
            popularity=data.get("popularity"),
            vote_average=data.get("vote_average"),
            vote_count=data.get("vote_count"),
            original_language=data.get("original_language"),
            poster_path=data.get("poster_path"),
            backdrop_path=data.get("backdrop_path"),
            status=data.get("status"),
            budget=data.get("budget"),
            revenue=data.get("revenue"),
            imdb_id=data.get("imdb_id"),
            streaming_providers=streaming_providers,
        )

    def _get_or_create_genre(self, genre_data: dict) -> Genre:
        """Get or create genre (cached)."""
        tmdb_id = genre_data["id"]

        if tmdb_id in self._genre_cache:
            return self._genre_cache[tmdb_id]

        # Try to find in database
        genre = self.genre_repo.find_by_tmdb_id(tmdb_id)
        if not genre:
            # Create new genre
            genre = Genre(
                tmdb_id=tmdb_id,
                name=genre_data["name"],
            )
            genre = self.genre_repo.create(genre)

        self._genre_cache[tmdb_id] = genre
        return genre

    def _get_or_create_keyword(self, keyword_data: dict) -> Keyword:
        """Get or create keyword (cached)."""
        tmdb_id = keyword_data["id"]

        if tmdb_id in self._keyword_cache:
            return self._keyword_cache[tmdb_id]

        keyword = self.keyword_repo.find_by_tmdb_id(tmdb_id)
        if not keyword:
            keyword = Keyword(
                tmdb_id=tmdb_id,
                name=keyword_data["name"],
            )
            keyword = self.keyword_repo.create(keyword)

        self._keyword_cache[tmdb_id] = keyword
        return keyword

    def _get_or_create_cast(self, cast_data: dict) -> Cast:
        """Get or create cast member (cached)."""
        tmdb_id = cast_data["id"]

        if tmdb_id in self._cast_cache:
            return self._cast_cache[tmdb_id]

        cast = self.cast_repo.find_by_tmdb_id(tmdb_id)
        if not cast:
            cast = Cast(
                tmdb_id=tmdb_id,
                name=cast_data["name"],
                profile_path=cast_data.get("profile_path"),
                popularity=cast_data.get("popularity"),
            )
            cast = self.cast_repo.create(cast)

        self._cast_cache[tmdb_id] = cast
        return cast

    # =============================================================================
    # Helper Methods
    # =============================================================================

    def _empty_stats(self) -> dict[str, int]:
        """Create empty statistics dictionary."""
        return {
            "movies_imported": 0,
            "movies_skipped": 0,
            "movies_failed": 0,
            "genres_created": 0,
            "keywords_created": 0,
            "cast_created": 0,
        }

    def _merge_stats(self, stats1: dict[str, int], stats2: dict[str, int]) -> dict[str, int]:
        """Merge two statistics dictionaries."""
        return {key: stats1[key] + stats2[key] for key in stats1}
