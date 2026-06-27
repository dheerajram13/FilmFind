"""
Movie repository for movie-specific database operations.

Design Patterns:
- Repository Pattern: Encapsulates data access
- Query Object: Complex queries as methods
- Lazy/Eager Loading: Optimized relationship loading
"""

from datetime import UTC, datetime
from typing import Optional

from sqlalchemy import and_, desc, func, or_
from sqlalchemy.orm import Session, selectinload

from app.models.media import Cast, Genre, Keyword, Media, MediaEmbedding, Movie, TVShow
from app.repositories.base import BaseRepository


class MovieRepository(BaseRepository[Movie]):
    """
    Repository for Movie entity with domain-specific queries.

    Provides optimized queries for:
    - Finding movies by TMDB ID
    - Searching movies by title
    - Filtering by genre, language, year
    - Retrieving popular/top-rated movies
    - Finding movies with/without embeddings
    """

    def __init__(self, db: Session):
        """Initialize movie repository with database session."""
        super().__init__(Movie, db)

    
    # Single-record lookups

    def find_by_tmdb_id(self, tmdb_id: int) -> Optional[Movie]:
        """
        Find movie by TMDB external ID.

        Args:
            tmdb_id: TMDB movie identifier

        Returns:
            Movie instance or None if not found
        """
        return self.db.query(Movie).filter(Movie.tmdb_id == tmdb_id).first()

    def find_by_imdb_id(self, imdb_id: str) -> Optional[Movie]:
        """
        Find movie by IMDB ID.

        Args:
            imdb_id: IMDB identifier (e.g., "tt1234567")

        Returns:
            Movie instance or None if not found
        """
        return self.db.query(Movie).filter(Movie.imdb_id == imdb_id).first()

    def get_with_relations(self, movie_id: int) -> Optional[Movie]:
        """
        Get movie by media_id with all relationships eagerly loaded.

        Eagerly loads genres, keywords, cast, and assets via the media anchor.
        Optimized for detail pages where all data is needed.

        Args:
            movie_id: The media_id (anchor PK) of the movie

        Returns:
            Movie with relationships loaded, or None
        """
        return (
            self.db.query(Movie)
            .options(
                selectinload(Movie.media).selectinload(Media.genres),
                selectinload(Movie.media).selectinload(Media.keywords),
                selectinload(Movie.media).selectinload(Media.cast_members),
                selectinload(Movie.media).selectinload(Media.assets),
            )
            .filter(Movie.media_id == movie_id)
            .first()
        )

    
    # Search
    

    def search_by_title(
        self,
        query: str,
        skip: int = 0,
        limit: int = 20,
        include_adult: bool = False,
    ) -> list[Movie]:
        """
        Search movies by title (case-insensitive partial match).

        Args:
            query: Search query string
            skip: Offset for pagination
            limit: Maximum results to return
            include_adult: Include adult content in results

        Returns:
            List of matching movies, ordered by popularity
        """
        filters = [
            or_(
                Movie.title.ilike(f"%{query}%"),
                Movie.original_title.ilike(f"%{query}%"),
            )
        ]
        if not include_adult:
            filters.append(Movie.adult == False)  

        return (
            self.db.query(Movie)
            .filter(and_(*filters))
            .order_by(desc(Movie.popularity))
            .offset(skip)
            .limit(limit)
            .all()
        )

    
    # Filter operations
    

    def filter_by_genre(
        self,
        genre_ids: list[int],
        skip: int = 0,
        limit: int = 50,
        include_adult: bool = False,
    ) -> list[Movie]:
        """
        Filter movies by genre IDs (AND logic — movie must have ALL genres).

        Joins through the media anchor since genres live on media_genres.

        Args:
            genre_ids: List of genre IDs
            skip: Offset for pagination
            limit: Maximum results
            include_adult: Include adult content

        Returns:
            List of movies matching all genres
        """
        query = (
            self.db.query(Movie)
            .join(Movie.media)
            .join(Media.genres)
        )
        filters = [Genre.id.in_(genre_ids)]
        if not include_adult:
            filters.append(Movie.adult == False)  

        return (
            query.filter(and_(*filters))
            .group_by(Movie.id)
            .having(func.count(Genre.id) == len(genre_ids))
            .order_by(desc(Movie.popularity))
            .offset(skip)
            .limit(limit)
            .all()
        )

    def filter_by_language(
        self,
        language: str,
        skip: int = 0,
        limit: int = 50,
        include_adult: bool = False,
    ) -> list[Movie]:
        """
        Filter movies by original language (ISO 639-1 code).

        Args:
            language: ISO 639-1 language code (e.g., "en", "te", "ko")
            skip: Offset
            limit: Maximum results
            include_adult: Include adult content

        Returns:
            List of movies in specified language
        """
        filters = [Movie.original_language == language]
        if not include_adult:
            filters.append(Movie.adult == False)  

        return (
            self.db.query(Movie)
            .filter(and_(*filters))
            .order_by(desc(Movie.popularity))
            .offset(skip)
            .limit(limit)
            .all()
        )

    def filter_by_year_range(
        self,
        start_year: Optional[int] = None,
        end_year: Optional[int] = None,
        skip: int = 0,
        limit: int = 50,
        include_adult: bool = False,
    ) -> list[Movie]:
        """
        Filter movies by release year range.

        Args:
            start_year: Minimum release year (inclusive)
            end_year: Maximum release year (inclusive)
            skip: Offset
            limit: Maximum results
            include_adult: Include adult content

        Returns:
            List of movies released in date range
        """
        filters = []
        if start_year:
            filters.append(func.extract("year", Movie.release_date) >= start_year)
        if end_year:
            filters.append(func.extract("year", Movie.release_date) <= end_year)
        if not include_adult:
            filters.append(Movie.adult == False)  

        return (
            self.db.query(Movie)
            .filter(and_(*filters))
            .order_by(desc(Movie.release_date))
            .offset(skip)
            .limit(limit)
            .all()
        )

    
    # Curated lists
    

    def get_popular(
        self,
        skip: int = 0,
        limit: int = 50,
        include_adult: bool = False,
        min_vote_count: int = 100,
    ) -> list[Movie]:
        """
        Get popular movies ordered by popularity score.

        Args:
            skip: Offset
            limit: Maximum results
            include_adult: Include adult content
            min_vote_count: Minimum number of votes (filters out obscure movies)

        Returns:
            List of popular movies
        """
        filters = [Movie.vote_count >= min_vote_count]
        if not include_adult:
            filters.append(Movie.adult == False)  

        return (
            self.db.query(Movie)
            .filter(and_(*filters))
            .order_by(desc(Movie.popularity))
            .offset(skip)
            .limit(limit)
            .all()
        )

    def get_top_rated(
        self,
        skip: int = 0,
        limit: int = 50,
        include_adult: bool = False,
        min_vote_count: int = 500,
    ) -> list[Movie]:
        """
        Get top-rated movies ordered by vote average.

        Args:
            skip: Offset
            limit: Maximum results
            include_adult: Include adult content
            min_vote_count: Minimum votes to avoid obscure high-rated movies

        Returns:
            List of top-rated movies
        """
        filters = [Movie.vote_count >= min_vote_count]
        if not include_adult:
            filters.append(Movie.adult == False)  

        return (
            self.db.query(Movie)
            .filter(and_(*filters))
            .order_by(desc(Movie.vote_average), desc(Movie.vote_count))
            .offset(skip)
            .limit(limit)
            .all()
        )

    def get_recent_releases(
        self,
        days: int = 90,
        skip: int = 0,
        limit: int = 50,
        include_adult: bool = False,
    ) -> list[Movie]:
        """
        Get recently released movies (last N days).

        Args:
            days: Number of days to look back
            skip: Offset
            limit: Maximum results
            include_adult: Include adult content

        Returns:
            List of recent movies
        """
        from datetime import timedelta

        cutoff_date = datetime.now(UTC) - timedelta(days=days)
        filters = [Movie.release_date >= cutoff_date]
        if not include_adult:
            filters.append(Movie.adult == False)  

        return (
            self.db.query(Movie)
            .filter(and_(*filters))
            .order_by(desc(Movie.release_date))
            .offset(skip)
            .limit(limit)
            .all()
        )

    
    # Embedding operations (via MediaEmbedding satellite table)
    

    def get_movies_without_embeddings(self, limit: int = 100, offset: int = 0) -> list[Movie]:
        """
        Get movies whose media anchor has no embedding row yet.

        Useful for batch embedding generation. Eagerly loads relationships
        (genres, keywords, cast) to avoid N+1 query problems.

        Args:
            limit: Maximum number of movies to return
            offset: Number of movies to skip

        Returns:
            List of movies without embeddings, with relationships loaded
        """
        return (
            self.db.query(Movie)
            .outerjoin(Movie.media)
            .outerjoin(Media.embedding)
            .options(
                selectinload(Movie.media).selectinload(Media.genres),
                selectinload(Movie.media).selectinload(Media.keywords),
                selectinload(Movie.media).selectinload(Media.cast_members),
            )
            .filter(MediaEmbedding.media_id.is_(None))
            .order_by(desc(Movie.popularity))
            .offset(offset)
            .limit(limit)
            .all()
        )

    def get_movies_with_embeddings(self, skip: int = 0, limit: int = 100) -> list[Movie]:
        """
        Get movies that have embeddings (for validation and index building).

        Args:
            skip: Offset
            limit: Maximum results

        Returns:
            List of movies with embeddings
        """
        return (
            self.db.query(Movie)
            .join(Movie.media)
            .join(Media.embedding)
            .filter(MediaEmbedding.embedding.isnot(None))
            .offset(skip)
            .limit(limit)
            .all()
        )

    def count_movies_with_embeddings(self) -> int:
        """Count how many movies have embeddings."""
        return (
            self.db.query(Movie)
            .join(Movie.media)
            .join(Media.embedding)
            .filter(MediaEmbedding.embedding.isnot(None))
            .count()
        )

    def count_movies_without_embeddings(self) -> int:
        """Count how many movies don't have embeddings yet."""
        return (
            self.db.query(Movie)
            .outerjoin(Movie.media)
            .outerjoin(Media.embedding)
            .filter(MediaEmbedding.media_id.is_(None))
            .count()
        )

    def update_embedding(
        self,
        movie_id: int,
        embedding: list[float],
        model_name: str = "sentence-transformers/all-mpnet-base-v2",
    ) -> None:
        """
        Update (or create) the MediaEmbedding row for a movie's media anchor.

        Args:
            movie_id: Movie primary key
            embedding: Embedding vector as list of floats
            model_name: Name of the embedding model used

        Raises:
            ValueError: If movie not found
        """
        from app.models.media import MediaEmbedding

        movie = self.get_by_id(movie_id)
        if not movie:
            raise ValueError(f"Movie with ID {movie_id} not found")

        emb = movie.media.embedding
        if emb is None:
            emb = MediaEmbedding(media_id=movie.media_id, model_name=model_name)
            self.db.add(emb)

        emb.embedding = embedding
        emb.needs_rebuild = False
        self.db.flush()

    
    # Bulk operations
    

    def find_by_ids(self, media_ids: list[int], eager_load_relations: bool = True) -> list[Media]:
        """
        Get Media anchors by their IDs (returned by pgvector search).

        Both Movie and TVShow records are accessible via media.movie / media.tv_show.

        Args:
            media_ids: List of media anchor IDs
            eager_load_relations: Whether to eagerly load genres, keywords, cast, assets

        Returns:
            List of Media instances with concrete types and relationships loaded
        """
        query = self.db.query(Media).filter(Media.id.in_(media_ids))
        if eager_load_relations:
            query = query.options(
                selectinload(Media.movie),
                selectinload(Media.tv_show),
                selectinload(Media.genres),
                selectinload(Media.keywords),
                selectinload(Media.cast_members),
                selectinload(Media.assets),
            )
        return query.all()

    def get_by_tmdb_ids(self, tmdb_ids: list[int]) -> list[Movie]:
        """
        Get multiple movies by TMDB IDs (bulk fetch).

        Args:
            tmdb_ids: List of TMDB identifiers

        Returns:
            List of movies (may be fewer than input if some don't exist)
        """
        return self.db.query(Movie).filter(Movie.tmdb_id.in_(tmdb_ids)).all()

    def upsert_movie(self, movie_data: dict) -> Movie:
        """
        Insert or update a Movie by tmdb_id. Creates a Media anchor if needed.

        If movie exists (by tmdb_id), updates its fields. Otherwise creates a
        Media anchor first, then the Movie row pointing at it.

        Args:
            movie_data: Dictionary with movie fields (must include tmdb_id)

        Returns:
            Created or updated Movie instance
        """
        from app.models.media import Media

        tmdb_id = movie_data.get("tmdb_id")
        if not tmdb_id:
            raise ValueError("tmdb_id is required for upsert")

        existing = self.find_by_tmdb_id(tmdb_id)
        if existing:
            for key, value in movie_data.items():
                if hasattr(existing, key) and key not in ("id", "media_id"):
                    setattr(existing, key, value)
            existing.updated_at = datetime.now(UTC)
            self.db.commit()
            self.db.refresh(existing)
            return existing

        # Create Media anchor first, then Movie
        anchor = Media(content_type="Movie")
        self.db.add(anchor)
        self.db.flush()  # get anchor.id

        movie = Movie(media_id=anchor.id, **{k: v for k, v in movie_data.items() if k != "media_id"})
        return self.create(movie)

    
    # Stats
    

    def get_total_movies(self, include_adult: bool = False) -> int:
        """
        Get total number of movies in database.

        Args:
            include_adult: Count adult content

        Returns:
            Total movie count
        """
        query = self.db.query(func.count(Movie.id))
        if not include_adult:
            query = query.filter(Movie.adult == False)  
        return query.scalar()

    def get_languages_count(self) -> list[tuple]:
        """
        Get count of movies per language.

        Returns:
            List of (language_code, count) tuples, ordered by count desc
        """
        return (
            self.db.query(Movie.original_language, func.count(Movie.id).label("count"))
            .group_by(Movie.original_language)
            .order_by(desc("count"))
            .all()
        )


# =============================================================================
# Helper Repositories
# =============================================================================


class GenreRepository(BaseRepository[Genre]):
    """Repository for Genre entities."""

    def __init__(self, db: Session):
        super().__init__(Genre, db)

    def find_by_name(self, name: str) -> Optional[Genre]:
        """Find genre by name."""
        return self.db.query(Genre).filter(Genre.name == name).first()

    def find_by_tmdb_id(self, tmdb_id: int) -> Optional[Genre]:
        """Find genre by TMDB ID."""
        return self.db.query(Genre).filter(Genre.tmdb_id == tmdb_id).first()

    def get_all_genres(self) -> list[Genre]:
        """Get all genres ordered by name."""
        return self.db.query(Genre).order_by(Genre.name).all()


class KeywordRepository(BaseRepository[Keyword]):
    """Repository for Keyword entities."""

    def __init__(self, db: Session):
        super().__init__(Keyword, db)

    def find_by_name(self, name: str) -> Optional[Keyword]:
        """Find keyword by name."""
        return self.db.query(Keyword).filter(Keyword.name == name).first()

    def find_by_tmdb_id(self, tmdb_id: int) -> Optional[Keyword]:
        """Find keyword by TMDB ID."""
        return self.db.query(Keyword).filter(Keyword.tmdb_id == tmdb_id).first()


class CastRepository(BaseRepository[Cast]):
    """Repository for Cast entities."""

    def __init__(self, db: Session):
        super().__init__(Cast, db)

    def find_by_name(self, name: str) -> Optional[Cast]:
        """Find cast member by name."""
        return self.db.query(Cast).filter(Cast.name == name).first()

    def find_by_tmdb_id(self, tmdb_id: int) -> Optional[Cast]:
        """Find cast member by TMDB ID."""
        return self.db.query(Cast).filter(Cast.tmdb_id == tmdb_id).first()

    def search_by_name(self, query: str, limit: int = 20) -> list[Cast]:
        """Search cast members by name (partial match)."""
        return (
            self.db.query(Cast)
            .filter(Cast.name.ilike(f"%{query}%"))
            .order_by(desc(Cast.popularity))
            .limit(limit)
            .all()
        )
