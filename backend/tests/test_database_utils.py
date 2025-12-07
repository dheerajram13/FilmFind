"""
Tests for database utility functions.

This module tests the database health check and maintenance utilities.
"""

import pytest
from sqlalchemy import create_engine

from app.core.database_utils import (
    check_database_connection,
    get_connection_pool_status,
    reindex_database,
    vacuum_database,
)


class TestDatabaseNameValidation:
    """Tests for database name validation in maintenance functions."""

    def test_reindex_rejects_unsafe_database_names(self, monkeypatch):
        """Test that reindex_database rejects database names with unsafe characters."""
        # Create a mock engine with unsafe database name
        unsafe_engine = create_engine(
            "postgresql://user:pass@localhost/filmfind; DROP TABLE movies;"
        )

        # Monkeypatch the engine in database_utils
        import app.core.database_utils as db_utils

        monkeypatch.setattr(db_utils, "engine", unsafe_engine)

        # Should raise ValueError for unsafe database name
        with pytest.raises(ValueError, match="Unsafe database name"):
            reindex_database()

    def test_reindex_accepts_safe_database_names(self, monkeypatch):
        """Test that reindex_database accepts valid database names."""
        # Create a mock engine with safe database names
        safe_names = [
            "filmfind",
            "filmfind_test",
            "filmfind_staging",
            "filmfind_prod",
            "test_db",
            "_underscore_db",
        ]

        import app.core.database_utils as db_utils

        for db_name in safe_names:
            # Create engine with safe name
            safe_engine = create_engine(f"postgresql://user:pass@localhost/{db_name}")
            monkeypatch.setattr(db_utils, "engine", safe_engine)

            # Should NOT raise ValueError
            # Note: This will fail with OperationalError (no actual DB connection)
            # but that's expected - we're only testing name validation
            try:
                reindex_database()
            except ValueError as e:
                pytest.fail(f"Safe database name '{db_name}' was rejected: {e}")
            except Exception:
                # Expected: connection errors, etc.
                pass

    def test_reindex_rejects_database_names_with_spaces(self, monkeypatch):
        """Test that database names with spaces are rejected."""
        import app.core.database_utils as db_utils

        # Database name with space (unsafe)
        unsafe_engine = create_engine("postgresql://user:pass@localhost/film find")
        monkeypatch.setattr(db_utils, "engine", unsafe_engine)

        with pytest.raises(ValueError, match="Unsafe database name"):
            reindex_database()

    def test_reindex_rejects_database_names_with_special_chars(self, monkeypatch):
        """Test that database names with special characters are rejected."""
        import app.core.database_utils as db_utils

        unsafe_names = [
            "film-find",  # Hyphen
            "film.find",  # Dot
            "film@find",  # At sign
            "film$find",  # Dollar sign
        ]

        for db_name in unsafe_names:
            unsafe_engine = create_engine(f"postgresql://user:pass@localhost/{db_name}")
            monkeypatch.setattr(db_utils, "engine", unsafe_engine)

            with pytest.raises(ValueError, match="Unsafe database name"):
                reindex_database()


class TestConnectionPoolStatus:
    """Tests for connection pool status utility."""

    def test_get_connection_pool_status_returns_dict(self):
        """Test that connection pool status returns expected structure."""
        status = get_connection_pool_status()

        assert isinstance(status, dict)

        # Should have pool metrics or error
        if "error" not in status:
            assert "pool_size" in status
            assert "checked_in" in status
            assert "checked_out" in status


class TestDatabaseConnection:
    """Tests for database connection health check."""

    def test_check_database_connection_returns_dict(self):
        """Test that connection check returns expected structure."""
        result = check_database_connection()

        assert isinstance(result, dict)
        assert "status" in result

        # Should be either healthy or unhealthy
        assert result["status"] in ["healthy", "unhealthy"]

    def test_check_database_connection_handles_invalid_url(self, monkeypatch):
        """Test that connection check handles invalid database URLs gracefully."""
        import app.core.database_utils as db_utils

        # Create engine with invalid host
        invalid_engine = create_engine("postgresql://user:pass@invalid-host:5432/filmfind")
        monkeypatch.setattr(db_utils, "engine", invalid_engine)

        result = check_database_connection()

        assert result["status"] == "unhealthy"
        assert "error" in result


class TestMaintenanceFunctions:
    """Tests for database maintenance functions."""

    def test_vacuum_database_returns_boolean(self):
        """Test that vacuum_database returns a boolean."""
        # Will fail with no connection, but should return False (not raise)
        result = vacuum_database()
        assert isinstance(result, bool)

    def test_reindex_database_returns_boolean(self):
        """Test that reindex_database returns a boolean."""
        # Will fail with no connection, but should return False (not raise)
        try:
            result = reindex_database()
            assert isinstance(result, bool)
        except ValueError:
            # OK if database name is invalid
            pass
