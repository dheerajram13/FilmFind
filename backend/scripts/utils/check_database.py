#!/usr/bin/env python
"""
Database health check CLI tool.

This script checks the database connection, tables, and overall health status.
Useful for debugging and deployment validation.

Usage:
    # Show help
    python scripts/check_database.py --help

    # Basic health check (connection + tables)
    python scripts/check_database.py

    # Show database statistics
    python scripts/check_database.py --stats

    # Show connection pool status
    python scripts/check_database.py --pool

    # Check migration status
    python scripts/check_database.py --migrations

    # Show all information
    python scripts/check_database.py --all
"""

import argparse
from pathlib import Path
import sys


# Add parent directory to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.core.database_utils import (
    check_database_connection,
    check_database_tables,
    check_migration_status,
    get_connection_pool_status,
    get_database_statistics,
)


def print_section(title: str):
    """Print section header."""
    print()
    print("=" * 70)
    print(f" {title}")
    print("=" * 70)


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Check FilmFind database health")

    parser.add_argument(
        "--stats",
        action="store_true",
        help="Show database statistics (row counts)",
    )

    parser.add_argument(
        "--pool",
        action="store_true",
        help="Show connection pool status",
    )

    parser.add_argument(
        "--migrations",
        action="store_true",
        help="Check migration status",
    )

    parser.add_argument(
        "--all",
        action="store_true",
        help="Show all information",
    )

    args = parser.parse_args()

    # If no flags, show basic health check
    show_basic = not (args.stats or args.pool or args.migrations or args.all)

    # Banner
    print_section("FilmFind Database Health Check")

    # 1. Connection Check
    if show_basic or args.all:
        print("\n[1/4] Checking database connection...")
        health = check_database_connection()

        if health["status"] == "healthy":
            print(f"  ✓ Database connection: {health['status'].upper()}")
            print(f"  • Latency: {health['latency_ms']}ms")
            print(f"  • Database: {health['database']}")
            print(f"  • Host: {health['host']}")
        else:
            print(f"  ✗ Database connection: {health['status'].upper()}")
            print(f"  • Error: {health['error']}")
            if "details" in health:
                print(f"  • Details: {health['details']}")
            sys.exit(1)

    # 2. Tables Check
    if show_basic or args.all:
        print("\n[2/4] Checking database tables...")
        tables_status = check_database_tables()

        if tables_status["status"] == "ready":
            print(f"  ✓ All required tables exist ({len(tables_status['tables'])} tables)")
            print(f"  • Tables: {', '.join(sorted(tables_status['tables']))}")
        elif tables_status["status"] == "missing_tables":
            print(f"  ✗ Missing tables: {', '.join(tables_status['missing'])}")
            print("  • Run migrations: alembic upgrade head")
            sys.exit(1)
        else:
            print(f"  ✗ Error checking tables: {tables_status.get('error')}")
            sys.exit(1)

    # 3. Migration Status
    if args.migrations or args.all:
        print("\n[3/4] Checking migration status...")
        migration = check_migration_status()

        if "error" in migration:
            print(f"  ! Warning: {migration['error']}")
        else:
            print(f"  • Current revision: {migration['current_revision']}")
            print(f"  • Head revision: {migration['head_revision']}")
            if migration["is_up_to_date"]:
                print("  ✓ Database is up to date")
            else:
                print("  ⚠ Database needs migration")
                print("  • Run: alembic upgrade head")

    # 4. Statistics
    if args.stats or args.all:
        print("\n[4/4] Database statistics...")
        stats = get_database_statistics()

        if "error" not in stats:
            print(f"  • Movies: {stats.get('movies_count', 0):,}")
            print(f"  • Movies with embeddings: {stats.get('movies_with_embeddings', 0):,}")
            print(f"  • Genres: {stats.get('genres_count', 0):,}")
            print(f"  • Keywords: {stats.get('keywords_count', 0):,}")
            print(f"  • Cast members: {stats.get('cast_count', 0):,}")
        else:
            print(f"  ✗ Error getting statistics: {stats['error']}")

    # 5. Connection Pool
    if args.pool or args.all:
        print_section("Connection Pool Status")
        pool = get_connection_pool_status()

        if "error" not in pool:
            print(f"  • Pool size: {pool['pool_size']}")
            print(f"  • Checked in (available): {pool['checked_in']}")
            print(f"  • Checked out (in use): {pool['checked_out']}")
            print(f"  • Overflow: {pool['overflow']}")
            print(f"  • Max overflow: {pool['max_overflow']}")
        else:
            print(f"  ✗ Error getting pool status: {pool['error']}")

    # Success
    print()
    print("=" * 70)
    print("  ✓ Database health check completed successfully")
    print("=" * 70)
    print()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n❌ Check cancelled by user")
        sys.exit(130)
    except Exception as e:
        print(f"\n\n❌ Unexpected error: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
