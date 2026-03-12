"""v4_supabase_image_columns

Adds poster_supabase_url and backdrop_supabase_url to the media table.

Dual-track design: the original TMDB relative paths (poster_path, backdrop_path)
are never modified. These new columns hold Supabase Storage CDN URLs once
the image migration script (scripts/migrate_images_to_supabase.py) runs.
The model's @property methods prefer Supabase URLs and fall back to TMDB CDN.

Revision ID: d4e5f6a7b8c9
Revises: c3d4e5f6a7b8
Create Date: 2026-03-11 00:01:00.000000
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = 'd4e5f6a7b8c9'
down_revision: Union[str, None] = 'c3d4e5f6a7b8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('media', sa.Column('poster_supabase_url', sa.String(500), nullable=True))
    op.add_column('media', sa.Column('backdrop_supabase_url', sa.String(500), nullable=True))


def downgrade() -> None:
    op.drop_column('media', 'backdrop_supabase_url')
    op.drop_column('media', 'poster_supabase_url')
