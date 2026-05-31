"""add confidence_score to search_sessions

Revision ID: a412a545a5e9
Revises: d4e5f6a7b8c9
Create Date: 2026-05-31 09:39:16.405898

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'a412a545a5e9'
down_revision: Union[str, None] = 'd4e5f6a7b8c9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('search_sessions', sa.Column('confidence_score', sa.Float(), nullable=True))


def downgrade() -> None:
    op.drop_column('search_sessions', 'confidence_score')
