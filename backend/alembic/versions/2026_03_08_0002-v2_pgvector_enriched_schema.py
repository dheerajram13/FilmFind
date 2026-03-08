"""v2_pgvector_enriched_schema

Adds pgvector extension, converts embedding_vector JSONB → VECTOR(768),
adds all enrichment columns (collection, countries, languages, companies,
networks, created_by, show_type), adds character_name to media_cast join table,
adds embedding_needs_rebuild flag for batch re-processing.

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
Create Date: 2026-03-08 00:02:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, ARRAY

revision: str = 'b2c3d4e5f6a7'
down_revision: Union[str, None] = 'a1b2c3d4e5f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Enable pgvector extension
    op.execute('CREATE EXTENSION IF NOT EXISTS vector')

    # 2. Convert embedding_vector from JSONB to VECTOR(768)
    #    - Add the new typed column alongside the old one
    #    - Migrate data: cast JSONB array → vector
    #    - Drop old column, rename new one
    op.execute('ALTER TABLE media ADD COLUMN embedding VECTOR(768)')
    op.execute("""
        UPDATE media
        SET embedding = (
            SELECT array_agg(v::float4)::vector(768)
            FROM jsonb_array_elements_text(embedding_vector) AS v
        )
        WHERE embedding_vector IS NOT NULL
          AND jsonb_typeof(embedding_vector) = 'array'
    """)
    op.drop_column('media', 'embedding_vector')
    op.drop_column('media', 'embedding_model')
    op.drop_column('media', 'embedding_dimension')

    # 3. Add embedding_needs_rebuild flag (marks rows needing re-embedding after text format change)
    op.add_column('media', sa.Column('embedding_needs_rebuild', sa.Boolean(),
                                      nullable=False, server_default='true'))

    # 4. New metadata columns on media
    op.add_column('media', sa.Column('belongs_to_collection', JSONB(), nullable=True))
    op.add_column('media', sa.Column('production_countries', ARRAY(sa.Text()), nullable=True))
    op.add_column('media', sa.Column('spoken_languages', ARRAY(sa.Text()), nullable=True))
    op.add_column('media', sa.Column('origin_country', ARRAY(sa.Text()), nullable=True))
    op.add_column('media', sa.Column('production_companies', JSONB(), nullable=True))

    # 5. TV-specific columns on tv_shows
    op.add_column('tv_shows', sa.Column('networks', JSONB(), nullable=True))
    op.add_column('tv_shows', sa.Column('created_by', JSONB(), nullable=True))
    op.add_column('tv_shows', sa.Column('show_type', sa.String(50), nullable=True))

    # 6. character_name already exists on media_cast from the original schema — no-op

    # 7. pgvector HNSW index for cosine similarity (build after data is loaded)
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_media_embedding_hnsw
        ON media
        USING hnsw (embedding vector_cosine_ops)
        WITH (m = 16, ef_construction = 64)
    """)


def downgrade() -> None:
    op.execute('DROP INDEX IF EXISTS idx_media_embedding_hnsw')

    op.drop_column('tv_shows', 'show_type')
    op.drop_column('tv_shows', 'created_by')
    op.drop_column('tv_shows', 'networks')

    op.drop_column('media', 'production_companies')
    op.drop_column('media', 'origin_country')
    op.drop_column('media', 'spoken_languages')
    op.drop_column('media', 'production_countries')
    op.drop_column('media', 'belongs_to_collection')
    op.drop_column('media', 'embedding_needs_rebuild')

    # Restore old JSONB embedding column
    op.execute('ALTER TABLE media ADD COLUMN embedding_vector JSONB')
    op.add_column('media', sa.Column('embedding_model', sa.String(100), nullable=True))
    op.add_column('media', sa.Column('embedding_dimension', sa.Integer(), nullable=True))
    op.drop_column('media', 'embedding')
