"""
Database utility functions for health checks and maintenance.

This module provides utility functions for:
- Database health checks
- Connection testing
- Migration status checking
- Database statistics
- Session management helpers

Design Patterns:
- Utility Pattern: Stateless helper functions
- Health Check Pattern: System monitoring
"""

import time
from typing import Any, Optional

from sqlalchemy import text
from sqlalchemy.exc import OperationalError, SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.database import SessionLocal, engine
from app.utils.logger import get_logger


logger = get_logger(__name__)


# =============================================================================
# Health Check Functions
# =============================================================================


def check_database_connection(timeout: float = 5.0) -> dict[str, Any]:
    """
    Check if database is accessible and responsive.

    Args:
        timeout: Maximum time to wait for connection (seconds)

    Returns:
        Dictionary with health check results:
            - status: "healthy" or "unhealthy"
            - latency_ms: Connection latency in milliseconds
            - error: Error message if unhealthy

    Example:
        ```python
        health = check_database_connection()
        if health["status"] == "healthy":
            print(f"Database is healthy (latency: {health['latency_ms']}ms)")
        else:
            print(f"Database is unhealthy: {health['error']}")
        ```
    """

    start_time = time.time()

    try:
        # Try to establish connection with timeout
        with engine.connect() as connection:
            # Execute simple query
            connection.execute(text("SELECT 1"))
            connection.commit()

        latency_ms = (time.time() - start_time) * 1000

        return {
            "status": "healthy",
            "latency_ms": round(latency_ms, 2),
            "database": str(engine.url.database),
            "host": str(engine.url.host),
        }

    except OperationalError as e:
        logger.error(f"Database connection failed: {e}")
        return {
            "status": "unhealthy",
            "error": "Connection refused or database not available",
            "details": str(e),
        }

    except SQLAlchemyError as e:
        logger.error(f"Database error: {e}")
        return {
            "status": "unhealthy",
            "error": "Database error occurred",
            "details": str(e),
        }

    except Exception as e:
        logger.error(f"Unexpected error during health check: {e}")
        return {
            "status": "unhealthy",
            "error": "Unexpected error",
            "details": str(e),
        }


def check_database_tables(db: Optional[Session] = None) -> dict[str, Any]:
    """
    Check if required database tables exist.

    Args:
        db: Database session (creates new if None)

    Returns:
        Dictionary with table existence status:
            - status: "ready" or "missing_tables"
            - tables: List of existing tables
            - missing: List of missing tables (if any)
    """

    required_tables = {
        "movies",
        "genres",
        "keywords",
        "cast",
        "movie_genres",
        "movie_keywords",
        "movie_cast",
    }

    session = db or SessionLocal()
    owns_session = db is None

    try:
        # Query PostgreSQL system tables
        result = session.execute(
            text(
                """
                SELECT tablename
                FROM pg_tables
                WHERE schemaname = 'public'
                """
            )
        )

        existing_tables = {row[0] for row in result}
        missing_tables = required_tables - existing_tables

        if missing_tables:
            return {
                "status": "missing_tables",
                "tables": list(existing_tables),
                "missing": list(missing_tables),
            }

        return {
            "status": "ready",
            "tables": list(existing_tables),
        }

    except Exception as e:
        logger.error(f"Error checking tables: {e}")
        return {
            "status": "error",
            "error": str(e),
        }

    finally:
        if owns_session:
            session.close()


def get_database_statistics(db: Optional[Session] = None) -> dict[str, Any]:
    """
    Get database statistics (table row counts, etc.).

    Args:
        db: Database session (creates new if None)

    Returns:
        Dictionary with database statistics:
            - movies_count: Number of movies
            - genres_count: Number of genres
            - keywords_count: Number of keywords
            - cast_count: Number of cast members
            - movies_with_embeddings: Number of movies with embeddings
    """

    session = db or SessionLocal()
    owns_session = db is None

    try:
        stats = {}

        # Count movies
        result = session.execute(text("SELECT COUNT(*) FROM movies"))
        stats["movies_count"] = result.scalar()

        # Count genres
        result = session.execute(text("SELECT COUNT(*) FROM genres"))
        stats["genres_count"] = result.scalar()

        # Count keywords
        result = session.execute(text("SELECT COUNT(*) FROM keywords"))
        stats["keywords_count"] = result.scalar()

        # Count cast
        result = session.execute(text("SELECT COUNT(*) FROM cast"))
        stats["cast_count"] = result.scalar()

        # Count movies with embeddings
        result = session.execute(
            text("SELECT COUNT(*) FROM movies WHERE embedding_vector IS NOT NULL")
        )
        stats["movies_with_embeddings"] = result.scalar()

        return stats

    except Exception as e:
        logger.error(f"Error getting database statistics: {e}")
        return {"error": str(e)}

    finally:
        if owns_session:
            session.close()


# =============================================================================
# Migration Utilities
# =============================================================================


def check_migration_status() -> dict[str, Any]:
    """
    Check Alembic migration status.

    Returns:
        Dictionary with migration information:
            - current_revision: Current database revision
            - is_up_to_date: Whether database is up to date
    """
    try:
        from alembic.config import Config
        from alembic.script import ScriptDirectory

        # Load Alembic config
        alembic_cfg = Config("alembic.ini")
        script = ScriptDirectory.from_config(alembic_cfg)

        # Get current revision
        with engine.connect() as connection:
            context = connection.execute(text("SELECT version_num FROM alembic_version"))
            current_revision = context.scalar()

        # Get head revision
        head_revision = script.get_current_head()

        return {
            "current_revision": current_revision,
            "head_revision": head_revision,
            "is_up_to_date": current_revision == head_revision,
        }

    except Exception as e:
        logger.warning(f"Could not check migration status: {e}")
        return {
            "error": "Migration table not found or alembic not initialized",
            "details": str(e),
        }


# =============================================================================
# Connection Pool Utilities
# =============================================================================


def get_connection_pool_status() -> dict[str, Any]:
    """
    Get connection pool statistics.

    Returns:
        Dictionary with pool information:
            - pool_size: Total pool size
            - checked_in: Connections checked in (available)
            - checked_out: Connections checked out (in use)
            - overflow: Overflow connections
    """
    try:
        pool = engine.pool

        return {
            "pool_size": pool.size(),
            "checked_in": pool.checkedin(),
            "checked_out": pool.checkedout(),
            "overflow": pool.overflow(),
            "max_overflow": engine.pool._max_overflow,
        }

    except Exception as e:
        logger.error(f"Error getting pool status: {e}")
        return {"error": str(e)}


# =============================================================================
# Session Management Helpers
# =============================================================================


def get_db_session() -> Session:
    """
    Get database session with proper error handling.

    This is a helper for dependency injection in FastAPI routes.

    Yields:
        Database session

    Example:
        ```python
        @app.get("/movies")
        def get_movies(db: Session = Depends(get_db_session)):
            return db.query(Movie).all()
        ```
    """
    db = SessionLocal()
    try:
        yield db
    except Exception as e:
        logger.error(f"Session error: {e}")
        db.rollback()
        raise
    finally:
        db.close()


# =============================================================================
# Maintenance Functions
# =============================================================================


def vacuum_database(analyze: bool = True) -> bool:
    """
    Run VACUUM on database to reclaim space and update statistics.

    Args:
        analyze: Whether to run ANALYZE with VACUUM

    Returns:
        True if successful, False otherwise

    Note:
        This operation can be slow on large databases.
    """
    try:
        with engine.connect().execution_options(isolation_level="AUTOCOMMIT") as connection:
            if analyze:
                connection.execute(text("VACUUM ANALYZE"))
                logger.info("VACUUM ANALYZE completed successfully")
            else:
                connection.execute(text("VACUUM"))
                logger.info("VACUUM completed successfully")

        return True

    except Exception as e:
        logger.error(f"VACUUM failed: {e}")
        return False


def reindex_database() -> bool:
    """
    Rebuild all database indexes.

    Returns:
        True if successful, False otherwise

    Raises:
        ValueError: If database name contains unsafe characters

    Note:
        This operation can be slow and locks tables.
        Uses CONCURRENTLY to avoid locking tables during reindex.
    """
    try:
        # Get database name from engine URL
        db_name = str(engine.url.database)

        # Validate database name to prevent SQL injection
        # Allow only valid Python identifiers (alphanumerics and underscores)
        if not db_name.isidentifier():
            error_msg = f"Unsafe database name: {db_name!r}"
            logger.error(error_msg)
            raise ValueError(error_msg)

        # Execute REINDEX with quoted identifier
        with engine.connect().execution_options(isolation_level="AUTOCOMMIT") as connection:
            connection.execute(text(f'REINDEX DATABASE CONCURRENTLY "{db_name}"'))
            logger.info(f"REINDEX completed successfully for database: {db_name}")

        return True

    except ValueError:
        # Re-raise ValueError for unsafe database names
        raise

    except Exception as e:
        logger.error(f"REINDEX failed: {e}")
        return False
