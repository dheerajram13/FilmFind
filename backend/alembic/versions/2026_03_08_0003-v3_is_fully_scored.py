"""v3_is_fully_scored

Adds is_fully_scored boolean flag to media table.
Set to TRUE by score_films.py once all three JSONB score matrices are populated.
sixty/pick filters on this flag to exclude unenriched films.

Revision ID: c3d4e5f6a7b8
Revises: b2c3d4e5f6a7
Create Date: 2026-03-08 00:03:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'c3d4e5f6a7b8'
down_revision: Union[str, None] = 'b2c3d4e5f6a7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'media',
        sa.Column(
            'is_fully_scored',
            sa.Boolean(),
            nullable=False,
            server_default='false',
        ),
    )
    # Backfill: mark films that already have all three score matrices as scored
    op.execute(
        """
        UPDATE media
        SET is_fully_scored = TRUE
        WHERE mood_scores IS NOT NULL
          AND context_scores IS NOT NULL
          AND craving_scores IS NOT NULL
        """
    )
    op.create_index('idx_media_is_fully_scored', 'media', ['is_fully_scored'])


def downgrade() -> None:
    op.drop_index('idx_media_is_fully_scored', table_name='media')
    op.drop_column('media', 'is_fully_scored')
