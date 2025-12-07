"""
Base repository class with common CRUD operations.

This module provides a generic base repository that implements common
database operations for all entities. Specific repositories inherit from
this class and add domain-specific query methods.

Design Patterns:
- Repository Pattern: Abstracts data access
- Generic Programming: Type-safe operations via TypeVar
- Unit of Work: Session management via dependency injection
"""

from typing import Generic, Optional, TypeVar

from sqlalchemy.orm import Session

from app.core.database import Base


# Type variable for domain models
ModelType = TypeVar("ModelType", bound=Base)


class BaseRepository(Generic[ModelType]):
    """
    Base repository with common CRUD operations.

    Provides standard create, read, update, delete operations for any model.
    Specific repositories should inherit from this and add domain-specific queries.

    Type Parameters:
        ModelType: The SQLAlchemy model class

    Example:
        ```python
        class MovieRepository(BaseRepository[Movie]):
            def find_by_tmdb_id(self, tmdb_id: int) -> Optional[Movie]:
                return self.db.query(self.model).filter_by(tmdb_id=tmdb_id).first()
        ```
    """

    def __init__(self, model: type[ModelType], db: Session):
        """
        Initialize repository with model class and database session.

        Args:
            model: SQLAlchemy model class
            db: Database session (injected dependency)
        """
        self.model = model
        self.db = db

    # =============================================================================
    # Create Operations
    # =============================================================================

    def create(self, obj: ModelType) -> ModelType:
        """
        Create a new entity in the database.

        Args:
            obj: Model instance to create

        Returns:
            Created model instance with ID assigned

        Example:
            ```python
            movie = Movie(tmdb_id=123, title="Inception")
            created = repo.create(movie)
            ```
        """

        self.db.add(obj)
        self.db.commit()
        self.db.refresh(obj)
        return obj

    def create_many(self, objects: list[ModelType]) -> list[ModelType]:
        """
        Create multiple entities in a single transaction.

        Args:
            objects: List of model instances to create

        Returns:
            List of created model instances

        Note:
            More efficient than multiple create() calls as it uses bulk insert.
        """

        self.db.add_all(objects)
        self.db.commit()
        for obj in objects:
            self.db.refresh(obj)
        return objects

    # =============================================================================
    # Read Operations
    # =============================================================================

    def get_by_id(self, id: int) -> Optional[ModelType]:
        """
        Retrieve entity by primary key ID.

        Args:
            id: Primary key value

        Returns:
            Model instance or None if not found
        """

        return self.db.query(self.model).filter(self.model.id == id).first()

    def get_all(self, skip: int = 0, limit: int = 100) -> list[ModelType]:
        """
        Retrieve all entities with pagination.

        Args:
            skip: Number of records to skip (offset)
            limit: Maximum number of records to return

        Returns:
            List of model instances
        """

        return self.db.query(self.model).offset(skip).limit(limit).all()

    def count(self) -> int:
        """
        Count total number of entities.

        Returns:
            Total count of records in table
        """

        return self.db.query(self.model).count()

    def exists(self, id: int) -> bool:
        """
        Check if entity exists by ID.

        Args:
            id: Primary key value

        Returns:
            True if exists, False otherwise
        """

        return self.db.query(self.model.id).filter(self.model.id == id).first() is not None

    # =============================================================================
    # Update Operations
    # =============================================================================

    def update(self, obj: ModelType) -> ModelType:
        """
        Update an existing entity.

        Args:
            obj: Model instance with updated fields

        Returns:
            Updated model instance

        Note:
            The object must already be tracked by the session or have a valid ID.
        """

        self.db.merge(obj)
        self.db.commit()
        self.db.refresh(obj)
        return obj

    # =============================================================================
    # Delete Operations
    # =============================================================================

    def delete(self, id: int) -> bool:
        """
        Delete entity by ID.

        Args:
            id: Primary key value

        Returns:
            True if deleted, False if not found
        """

        obj = self.get_by_id(id)
        if obj:
            self.db.delete(obj)
            self.db.commit()
            return True
        return False

    def delete_many(self, ids: list[int]) -> int:
        """
        Delete multiple entities by IDs.

        Args:
            ids: List of primary key values

        Returns:
            Number of deleted records
        """
        deleted = (
            self.db.query(self.model)
            .filter(self.model.id.in_(ids))
            .delete(synchronize_session=False)
        )
        self.db.commit()
        return deleted

    # =============================================================================
    # Utility Methods
    # =============================================================================

    def refresh(self, obj: ModelType) -> ModelType:
        """
        Refresh entity from database (reload from DB).

        Args:
            obj: Model instance to refresh

        Returns:
            Refreshed model instance
        """
        self.db.refresh(obj)
        return obj

    def commit(self) -> None:
        """Commit current transaction."""
        self.db.commit()

    def rollback(self) -> None:
        """Rollback current transaction."""
        self.db.rollback()

    def flush(self) -> None:
        """Flush pending changes to database without committing."""
        self.db.flush()
