"""initial_schema_movies_genres_keywords_cast

Revision ID: 1abfd592bb52
Revises:
Create Date: 2025-12-07 10:54:37.560241

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "1abfd592bb52"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema - create all tables with proper indexing."""

    # =============================================================================
    # Create genres table
    # =============================================================================
    op.create_table(
        "genres",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("tmdb_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("tmdb_id"),
        sa.UniqueConstraint("name"),
    )
    op.create_index(op.f("ix_genres_id"), "genres", ["id"], unique=False)
    op.create_index(op.f("ix_genres_name"), "genres", ["name"], unique=True)
    op.create_index(op.f("ix_genres_tmdb_id"), "genres", ["tmdb_id"], unique=True)

    # =============================================================================
    # Create keywords table
    # =============================================================================
    op.create_table(
        "keywords",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("tmdb_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("tmdb_id"),
        sa.UniqueConstraint("name"),
    )
    op.create_index(op.f("ix_keywords_id"), "keywords", ["id"], unique=False)
    op.create_index(op.f("ix_keywords_name"), "keywords", ["name"], unique=True)
    op.create_index(op.f("ix_keywords_tmdb_id"), "keywords", ["tmdb_id"], unique=True)

    # =============================================================================
    # Create cast table
    # =============================================================================
    op.create_table(
        "cast",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("tmdb_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("profile_path", sa.String(length=255), nullable=True),
        sa.Column("popularity", sa.Float(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("tmdb_id"),
    )
    op.create_index(op.f("ix_cast_id"), "cast", ["id"], unique=False)
    op.create_index(op.f("ix_cast_name"), "cast", ["name"], unique=False)
    op.create_index(op.f("ix_cast_tmdb_id"), "cast", ["tmdb_id"], unique=True)

    # =============================================================================
    # Create movies table (main table)
    # =============================================================================
    op.create_table(
        "movies",
        # Primary Keys
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("tmdb_id", sa.Integer(), nullable=False),
        # Core Information
        sa.Column("title", sa.String(length=500), nullable=False),
        sa.Column("original_title", sa.String(length=500), nullable=True),
        sa.Column("overview", sa.Text(), nullable=True),
        sa.Column("tagline", sa.String(length=500), nullable=True),
        # Release & Runtime
        sa.Column("release_date", sa.DateTime(), nullable=True),
        sa.Column("runtime", sa.Integer(), nullable=True),
        # Content Flags
        sa.Column("adult", sa.Boolean(), nullable=False, server_default=sa.false()),
        # Popularity & Ratings
        sa.Column("popularity", sa.Float(), nullable=True),
        sa.Column("vote_average", sa.Float(), nullable=True),
        sa.Column("vote_count", sa.Integer(), nullable=True),
        # Language
        sa.Column("original_language", sa.String(length=10), nullable=True),
        # Media Assets
        sa.Column("poster_path", sa.String(length=255), nullable=True),
        sa.Column("backdrop_path", sa.String(length=255), nullable=True),
        # Additional Metadata
        sa.Column("status", sa.String(length=50), nullable=True),
        sa.Column("budget", sa.Integer(), nullable=True),
        sa.Column("revenue", sa.Integer(), nullable=True),
        sa.Column("imdb_id", sa.String(length=20), nullable=True),
        # Embeddings
        sa.Column("embedding_vector", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("embedding_model", sa.String(length=100), nullable=True),
        sa.Column("embedding_dimension", sa.Integer(), nullable=True),
        # Streaming
        sa.Column("streaming_providers", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        # Timestamps
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("tmdb_id"),
    )

    # Basic Indexes
    op.create_index(op.f("ix_movies_id"), "movies", ["id"], unique=False)
    op.create_index(op.f("ix_movies_tmdb_id"), "movies", ["tmdb_id"], unique=True)
    op.create_index(op.f("ix_movies_title"), "movies", ["title"], unique=False)
    op.create_index(op.f("ix_movies_imdb_id"), "movies", ["imdb_id"], unique=False)
    op.create_index(op.f("ix_movies_release_date"), "movies", ["release_date"], unique=False)
    op.create_index(op.f("ix_movies_adult"), "movies", ["adult"], unique=False)
    op.create_index(op.f("ix_movies_popularity"), "movies", ["popularity"], unique=False)
    op.create_index(op.f("ix_movies_vote_average"), "movies", ["vote_average"], unique=False)
    op.create_index(
        op.f("ix_movies_original_language"), "movies", ["original_language"], unique=False
    )

    # Composite Indexes (for complex queries)
    op.create_index(
        "idx_movies_language_popularity",
        "movies",
        ["original_language", "popularity"],
        unique=False,
    )
    op.create_index(
        "idx_movies_release_rating", "movies", ["release_date", "vote_average"], unique=False
    )
    op.create_index("idx_movies_updated_at", "movies", ["updated_at"], unique=False)
    op.create_index("idx_movies_adult_popularity", "movies", ["adult", "popularity"], unique=False)

    # =============================================================================
    # Create association tables (many-to-many relationships)
    # =============================================================================

    # movie_genres
    op.create_table(
        "movie_genres",
        sa.Column("movie_id", sa.Integer(), nullable=False),
        sa.Column("genre_id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["movie_id"], ["movies.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["genre_id"], ["genres.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("movie_id", "genre_id"),
    )

    # movie_keywords
    op.create_table(
        "movie_keywords",
        sa.Column("movie_id", sa.Integer(), nullable=False),
        sa.Column("keyword_id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["movie_id"], ["movies.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["keyword_id"], ["keywords.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("movie_id", "keyword_id"),
    )

    # movie_cast (with additional columns)
    op.create_table(
        "movie_cast",
        sa.Column("movie_id", sa.Integer(), nullable=False),
        sa.Column("cast_id", sa.Integer(), nullable=False),
        sa.Column("character_name", sa.String(length=255), nullable=True),
        sa.Column("order_position", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["movie_id"], ["movies.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["cast_id"], ["cast.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("movie_id", "cast_id"),
    )

    # Index for top cast queries
    op.create_index(
        "idx_movie_cast_order", "movie_cast", ["movie_id", "order_position"], unique=False
    )


def downgrade() -> None:
    """Downgrade schema - drop all tables and indexes."""

    # Drop indexes first (before dropping tables)
    op.drop_index("idx_movie_cast_order", table_name="movie_cast")

    # Drop association tables (due to foreign key constraints)
    op.drop_table("movie_cast")
    op.drop_table("movie_keywords")
    op.drop_table("movie_genres")

    # Drop main tables
    op.drop_table("movies")
    op.drop_table("cast")
    op.drop_table("keywords")
    op.drop_table("genres")
