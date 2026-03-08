"""v1_score_columns_session_tables

Revision ID: a1b2c3d4e5f6
Revises: b3d41db74ccc
Create Date: 2026-03-08 00:01:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, ARRAY


# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, None] = 'b3d41db74ccc'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # --- Score / enrichment columns on media ---
    op.add_column('media', sa.Column('narrative_dna', sa.Text(), nullable=True))
    op.add_column('media', sa.Column('themes', ARRAY(sa.Text()), nullable=True))
    op.add_column('media', sa.Column('tone_tags', ARRAY(sa.Text()), nullable=True))
    op.add_column('media', sa.Column('darkness_score', sa.Integer(), nullable=True))
    op.add_column('media', sa.Column('complexity_score', sa.Integer(), nullable=True))
    op.add_column('media', sa.Column('energy_score', sa.Integer(), nullable=True))
    op.add_column('media', sa.Column('mood_scores', JSONB(), nullable=True))
    op.add_column('media', sa.Column('context_scores', JSONB(), nullable=True))
    op.add_column('media', sa.Column('craving_scores', JSONB(), nullable=True))

    op.create_check_constraint(
        'ck_media_darkness_score',
        'media',
        'darkness_score BETWEEN 0 AND 10',
    )
    op.create_check_constraint(
        'ck_media_complexity_score',
        'media',
        'complexity_score BETWEEN 0 AND 10',
    )
    op.create_check_constraint(
        'ck_media_energy_score',
        'media',
        'energy_score BETWEEN 0 AND 10',
    )

    # --- search_sessions table ---
    op.create_table(
        'search_sessions',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('session_token', sa.String(255), nullable=True, index=True),
        sa.Column('query_text', sa.Text(), nullable=True),
        sa.Column('query_parsed', JSONB(), nullable=True),
        sa.Column('results', JSONB(), nullable=True),
        sa.Column('result_clicked_id', sa.Integer(), nullable=True),
        sa.Column('stream_clicked', sa.Boolean(), default=False),
        sa.Column('response_ms', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )

    # --- sixty_sessions table ---
    op.create_table(
        'sixty_sessions',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('session_token', sa.String(255), nullable=True, index=True),
        sa.Column('mood', sa.String(50), nullable=True),
        sa.Column('context', sa.String(50), nullable=True),
        sa.Column('craving', sa.String(50), nullable=True),
        sa.Column('film_picked_id', sa.Integer(), sa.ForeignKey('media.id', ondelete='SET NULL'), nullable=True),
        sa.Column('match_score', sa.Integer(), nullable=True),
        sa.Column('seconds_taken', sa.Integer(), nullable=True),
        sa.Column('watch_clicked', sa.Boolean(), default=False),
        sa.Column('share_clicked', sa.Boolean(), default=False),
        sa.Column('retry_clicked', sa.Boolean(), default=False),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )

    # --- users scaffold (no endpoints yet) ---
    op.create_table(
        'users',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('email', sa.String(255), unique=True, nullable=False),
        sa.Column('display_name', sa.String(255), nullable=True),
        sa.Column('avatar_url', sa.String(500), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )

    # --- watchlist scaffold (no endpoints yet) ---
    op.create_table(
        'watchlist',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('user_id', sa.String(36), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('media_id', sa.Integer(), sa.ForeignKey('media.id', ondelete='CASCADE'), nullable=False),
        sa.Column('added_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table('watchlist')
    op.drop_table('users')
    op.drop_table('sixty_sessions')
    op.drop_table('search_sessions')

    op.drop_constraint('ck_media_energy_score', 'media', type_='check')
    op.drop_constraint('ck_media_complexity_score', 'media', type_='check')
    op.drop_constraint('ck_media_darkness_score', 'media', type_='check')

    op.drop_column('media', 'craving_scores')
    op.drop_column('media', 'context_scores')
    op.drop_column('media', 'mood_scores')
    op.drop_column('media', 'energy_score')
    op.drop_column('media', 'complexity_score')
    op.drop_column('media', 'darkness_score')
    op.drop_column('media', 'tone_tags')
    op.drop_column('media', 'themes')
    op.drop_column('media', 'narrative_dna')
