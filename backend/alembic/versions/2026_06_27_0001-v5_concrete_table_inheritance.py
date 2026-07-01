"""v5_concrete_table_inheritance

Migrate from joined-table inheritance to concrete-table + Media anchor pattern:

Before:
  media (id, media_type, title, overview, ..., embedding, narrative_dna, ...)
  movies (id FK→media.id, runtime, budget, revenue)
  tv_shows (id FK→media.id, seasons, ...)

After:
  media (id, created_at)  ← lightweight anchor only
  movies (id, media_id FK→media.id, title, overview, ..., runtime, budget, revenue)
  tv_shows (id, media_id FK→media.id, title, overview, ..., seasons, ...)
  media_enrichment (media_id PK FK, narrative_dna, mood_scores, ...)
  media_embedding  (media_id PK FK, embedding VECTOR(768), ...)
  media_asset      (id, media_id FK, asset_type, source, url, ...)

Data migration:
  - movies.media_id = old movies.id (= media.id in JTI, values are identical)
  - All Resource columns copied from media → movies / tv_shows
  - media.embedding → media_embedding
  - media enrichment columns → media_enrichment
  - poster/backdrop paths/urls → media_asset rows

Revision ID: f6a7b8c9d0e1
Revises: a412a545a5e9
Create Date: 2026-06-27 00:01:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import ARRAY, JSONB

revision: str = 'f6a7b8c9d0e1'
down_revision: Union[str, None] = 'a412a545a5e9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()

    # ── 0. Add content_type to media anchor + tmdb_id to genres ──────────────
    op.add_column('media', sa.Column('content_type', sa.String(20), nullable=True))
    conn.execute(sa.text("""
        UPDATE media SET content_type =
            CASE media_type
                WHEN 'movie' THEN 'Movie'
                WHEN 'tv'    THEN 'TV Show'
            END
        WHERE media_type IS NOT NULL
    """))
    op.alter_column('media', 'content_type', nullable=False)
    op.create_index('idx_media_content_type', 'media', ['content_type'])
    op.create_check_constraint(
        'chk_media_content_type',
        'media',
        "content_type IN ('Movie', 'TV Show')",
    )

    op.add_column('genres', sa.Column('tmdb_id', sa.Integer(), nullable=True))
    op.create_index('idx_genres_tmdb_id', 'genres', ['tmdb_id'], unique=True)

    # ── 1. Add Resource columns to movies ─────────────────────────────────────
    op.add_column('movies', sa.Column('media_id', sa.Integer(), nullable=True))
    op.add_column('movies', sa.Column('tmdb_id', sa.Integer(), nullable=True))
    op.add_column('movies', sa.Column('imdb_id', sa.String(20), nullable=True))
    op.add_column('movies', sa.Column('title', sa.String(500), nullable=True))
    op.add_column('movies', sa.Column('original_title', sa.String(500), nullable=True))
    op.add_column('movies', sa.Column('overview', sa.Text(), nullable=True))
    op.add_column('movies', sa.Column('tagline', sa.String(500), nullable=True))
    op.add_column('movies', sa.Column('release_date', sa.DateTime(), nullable=True))
    op.add_column('movies', sa.Column('status', sa.String(50), nullable=True))
    op.add_column('movies', sa.Column('adult', sa.Boolean(), nullable=True))
    op.add_column('movies', sa.Column('original_language', sa.String(10), nullable=True))
    op.add_column('movies', sa.Column('popularity', sa.Float(), nullable=True))
    op.add_column('movies', sa.Column('vote_average', sa.Float(), nullable=True))
    op.add_column('movies', sa.Column('vote_count', sa.Integer(), nullable=True))
    op.add_column('movies', sa.Column('belongs_to_collection', JSONB(), nullable=True))
    op.add_column('movies', sa.Column('production_countries', ARRAY(sa.Text()), nullable=True))
    op.add_column('movies', sa.Column('spoken_languages', ARRAY(sa.Text()), nullable=True))
    op.add_column('movies', sa.Column('origin_country', ARRAY(sa.Text()), nullable=True))
    op.add_column('movies', sa.Column('production_companies', JSONB(), nullable=True))
    op.add_column('movies', sa.Column('streaming_providers', JSONB(), nullable=True))
    op.add_column('movies', sa.Column('created_at', sa.DateTime(), nullable=True))
    op.add_column('movies', sa.Column('updated_at', sa.DateTime(), nullable=True))

    # ── 2. Add Resource columns to tv_shows ───────────────────────────────────
    op.add_column('tv_shows', sa.Column('media_id', sa.Integer(), nullable=True))
    op.add_column('tv_shows', sa.Column('tmdb_id', sa.Integer(), nullable=True))
    op.add_column('tv_shows', sa.Column('imdb_id', sa.String(20), nullable=True))
    op.add_column('tv_shows', sa.Column('title', sa.String(500), nullable=True))
    op.add_column('tv_shows', sa.Column('original_title', sa.String(500), nullable=True))
    op.add_column('tv_shows', sa.Column('overview', sa.Text(), nullable=True))
    op.add_column('tv_shows', sa.Column('tagline', sa.String(500), nullable=True))
    op.add_column('tv_shows', sa.Column('release_date', sa.DateTime(), nullable=True))
    op.add_column('tv_shows', sa.Column('status', sa.String(50), nullable=True))
    op.add_column('tv_shows', sa.Column('adult', sa.Boolean(), nullable=True))
    op.add_column('tv_shows', sa.Column('original_language', sa.String(10), nullable=True))
    op.add_column('tv_shows', sa.Column('popularity', sa.Float(), nullable=True))
    op.add_column('tv_shows', sa.Column('vote_average', sa.Float(), nullable=True))
    op.add_column('tv_shows', sa.Column('vote_count', sa.Integer(), nullable=True))
    op.add_column('tv_shows', sa.Column('belongs_to_collection', JSONB(), nullable=True))
    op.add_column('tv_shows', sa.Column('production_countries', ARRAY(sa.Text()), nullable=True))
    op.add_column('tv_shows', sa.Column('spoken_languages', ARRAY(sa.Text()), nullable=True))
    op.add_column('tv_shows', sa.Column('origin_country', ARRAY(sa.Text()), nullable=True))
    op.add_column('tv_shows', sa.Column('production_companies', JSONB(), nullable=True))
    op.add_column('tv_shows', sa.Column('streaming_providers', JSONB(), nullable=True))
    op.add_column('tv_shows', sa.Column('created_at', sa.DateTime(), nullable=True))
    op.add_column('tv_shows', sa.Column('updated_at', sa.DateTime(), nullable=True))

    # ── 3. Populate movies from media (JTI: movies.id = media.id) ────────────
    conn.execute(sa.text("""
        UPDATE movies m
        SET
            media_id              = med.id,
            tmdb_id               = med.tmdb_id,
            imdb_id               = med.imdb_id,
            title                 = med.title,
            original_title        = med.original_title,
            overview              = med.overview,
            tagline               = med.tagline,
            release_date          = med.release_date,
            status                = med.status,
            adult                 = med.adult,
            original_language     = med.original_language,
            popularity            = med.popularity,
            vote_average          = med.vote_average,
            vote_count            = med.vote_count,
            belongs_to_collection = med.belongs_to_collection,
            production_countries  = med.production_countries,
            spoken_languages      = med.spoken_languages,
            origin_country        = med.origin_country,
            production_companies  = med.production_companies,
            streaming_providers   = med.streaming_providers,
            created_at            = med.created_at,
            updated_at            = med.updated_at
        FROM media med
        WHERE m.id = med.id
    """))

    # ── 4. Populate tv_shows from media ───────────────────────────────────────
    conn.execute(sa.text("""
        UPDATE tv_shows t
        SET
            media_id              = med.id,
            tmdb_id               = med.tmdb_id,
            imdb_id               = med.imdb_id,
            title                 = med.title,
            original_title        = med.original_title,
            overview              = med.overview,
            tagline               = med.tagline,
            release_date          = COALESCE(med.release_date, t.first_air_date),
            status                = med.status,
            adult                 = med.adult,
            original_language     = med.original_language,
            popularity            = med.popularity,
            vote_average          = med.vote_average,
            vote_count            = med.vote_count,
            belongs_to_collection = med.belongs_to_collection,
            production_countries  = med.production_countries,
            spoken_languages      = med.spoken_languages,
            origin_country        = med.origin_country,
            production_companies  = med.production_companies,
            streaming_providers   = med.streaming_providers,
            created_at            = med.created_at,
            updated_at            = med.updated_at
        FROM media med
        WHERE t.id = med.id
    """))

    # ── 5. Create media_enrichment from media enrichment columns ──────────────
    conn.execute(sa.text("""
        CREATE TABLE media_enrichment (
            media_id         INTEGER PRIMARY KEY REFERENCES media(id) ON DELETE CASCADE,
            narrative_dna    TEXT,
            themes           TEXT[],
            tone_tags        TEXT[],
            darkness_score   INTEGER,
            complexity_score INTEGER,
            energy_score     INTEGER,
            mood_scores      JSONB,
            context_scores   JSONB,
            craving_scores   JSONB,
            is_fully_scored  BOOLEAN NOT NULL DEFAULT FALSE,
            enriched_at      TIMESTAMP
        )
    """))

    conn.execute(sa.text("""
        INSERT INTO media_enrichment (
            media_id, narrative_dna, themes, tone_tags,
            darkness_score, complexity_score, energy_score,
            mood_scores, context_scores, craving_scores,
            is_fully_scored, enriched_at
        )
        SELECT
            id, narrative_dna, themes, tone_tags,
            darkness_score, complexity_score, energy_score,
            mood_scores, context_scores, craving_scores,
            is_fully_scored, updated_at
        FROM media
        WHERE narrative_dna IS NOT NULL
           OR mood_scores IS NOT NULL
           OR is_fully_scored = TRUE
    """))

    op.create_index('idx_media_enrichment_fully_scored', 'media_enrichment', ['is_fully_scored'])

    # ── 6. Create media_embedding from media.embedding ────────────────────────
    conn.execute(sa.text("""
        CREATE TABLE media_embedding (
            media_id      INTEGER PRIMARY KEY REFERENCES media(id) ON DELETE CASCADE,
            embedding     VECTOR(768),
            model_name    VARCHAR(100) DEFAULT 'sentence-transformers/all-mpnet-base-v2',
            needs_rebuild BOOLEAN NOT NULL DEFAULT TRUE,
            updated_at    TIMESTAMP
        )
    """))

    conn.execute(sa.text("""
        INSERT INTO media_embedding (media_id, embedding, needs_rebuild, updated_at)
        SELECT id, embedding, embedding_needs_rebuild, updated_at
        FROM media
        WHERE embedding IS NOT NULL
    """))

    # Drop old HNSW index on media.embedding, create on media_embedding.embedding
    op.execute('DROP INDEX IF EXISTS idx_media_embedding_hnsw')
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_media_embedding_hnsw
        ON media_embedding
        USING hnsw (embedding vector_cosine_ops)
        WITH (m = 16, ef_construction = 64)
    """)

    # ── 7. Create media_asset from poster/backdrop columns ────────────────────
    conn.execute(sa.text("""
        CREATE TABLE media_asset (
            id            SERIAL PRIMARY KEY,
            media_id      INTEGER NOT NULL REFERENCES media(id) ON DELETE CASCADE,
            asset_type    VARCHAR(20) NOT NULL,
            source        VARCHAR(20) NOT NULL,
            url           VARCHAR(1000) NOT NULL,
            file_path     VARCHAR(500),
            language      VARCHAR(10),
            width         INTEGER,
            height        INTEGER,
            is_primary    BOOLEAN NOT NULL DEFAULT FALSE,
            display_order INTEGER NOT NULL DEFAULT 0,
            created_at    TIMESTAMP NOT NULL DEFAULT NOW()
        )
    """))

    # Supabase poster takes priority; fall back to TMDB path
    conn.execute(sa.text("""
        INSERT INTO media_asset (media_id, asset_type, source, url, file_path, is_primary, display_order)
        SELECT id, 'poster', 'supabase', poster_supabase_url, NULL, TRUE, 0
        FROM media
        WHERE poster_supabase_url IS NOT NULL
    """))
    conn.execute(sa.text("""
        INSERT INTO media_asset (media_id, asset_type, source, url, file_path, is_primary, display_order)
        SELECT id, 'poster', 'tmdb',
               'https://image.tmdb.org/t/p/w500' || poster_path, poster_path,
               (poster_supabase_url IS NULL), 0
        FROM media
        WHERE poster_path IS NOT NULL
    """))
    conn.execute(sa.text("""
        INSERT INTO media_asset (media_id, asset_type, source, url, file_path, is_primary, display_order)
        SELECT id, 'backdrop', 'supabase', backdrop_supabase_url, NULL, TRUE, 0
        FROM media
        WHERE backdrop_supabase_url IS NOT NULL
    """))
    conn.execute(sa.text("""
        INSERT INTO media_asset (media_id, asset_type, source, url, file_path, is_primary, display_order)
        SELECT id, 'backdrop', 'tmdb',
               'https://image.tmdb.org/t/p/original' || backdrop_path, backdrop_path,
               (backdrop_supabase_url IS NULL), 0
        FROM media
        WHERE backdrop_path IS NOT NULL
    """))

    op.create_index('idx_media_asset_media_type', 'media_asset', ['media_id', 'asset_type'])
    op.create_index('idx_media_asset_primary',    'media_asset', ['media_id', 'asset_type', 'is_primary'])

    # ── 8. Add FK + unique constraints for media_id on movies / tv_shows ──────
    op.create_foreign_key('fk_movies_media_id',   'movies',   'media', ['media_id'], ['id'], ondelete='CASCADE')
    op.create_foreign_key('fk_tv_shows_media_id', 'tv_shows', 'media', ['media_id'], ['id'], ondelete='CASCADE')
    op.create_unique_constraint('uq_movies_media_id',   'movies',   ['media_id'])
    op.create_unique_constraint('uq_tv_shows_media_id', 'tv_shows', ['media_id'])

    # Set NOT NULL now that data is populated
    op.alter_column('movies',   'media_id', nullable=False)
    op.alter_column('tv_shows', 'media_id', nullable=False)
    op.alter_column('movies',   'title',    nullable=False)
    op.alter_column('tv_shows', 'title',    nullable=False)
    op.alter_column('movies',   'tmdb_id',  nullable=False)
    op.alter_column('tv_shows', 'tmdb_id',  nullable=False)
    op.alter_column('movies',   'adult',    nullable=False)
    op.alter_column('tv_shows', 'adult',    nullable=False)
    op.alter_column('movies',   'created_at', nullable=False)
    op.alter_column('tv_shows', 'created_at', nullable=False)
    op.alter_column('movies',   'updated_at', nullable=False)
    op.alter_column('tv_shows', 'updated_at', nullable=False)

    # Unique on tmdb_id per table (was per-type via uq_media_tmdb_id_media_type)
    op.create_unique_constraint('uq_movies_tmdb_id',   'movies',   ['tmdb_id'])
    op.create_unique_constraint('uq_tv_shows_tmdb_id', 'tv_shows', ['tmdb_id'])

    # ── 9. Drop the old JTI FK from movies.id and tv_shows.id → media.id ─────
    # In JTI, movies.id was itself the FK to media.id — we're breaking that link.
    # The constraint name may vary by DB; use IF EXISTS via raw SQL.
    conn.execute(sa.text("""
        DO $$
        DECLARE
            r RECORD;
        BEGIN
            FOR r IN
                SELECT conname FROM pg_constraint
                WHERE conrelid = 'movies'::regclass AND contype = 'f'
                  AND conname != 'fk_movies_media_id'
            LOOP
                EXECUTE 'ALTER TABLE movies DROP CONSTRAINT ' || quote_ident(r.conname);
            END LOOP;
        END $$;
    """))
    conn.execute(sa.text("""
        DO $$
        DECLARE
            r RECORD;
        BEGIN
            FOR r IN
                SELECT conname FROM pg_constraint
                WHERE conrelid = 'tv_shows'::regclass AND contype = 'f'
                  AND conname != 'fk_tv_shows_media_id'
            LOOP
                EXECUTE 'ALTER TABLE tv_shows DROP CONSTRAINT ' || quote_ident(r.conname);
            END LOOP;
        END $$;
    """))

    # ── 10. Advance sequences so new inserts don't collide with existing IDs ──
    conn.execute(sa.text("""
        SELECT setval(pg_get_serial_sequence('movies', 'id'),
               COALESCE((SELECT MAX(id) FROM movies), 0) + 1, false)
    """))
    conn.execute(sa.text("""
        SELECT setval(pg_get_serial_sequence('tv_shows', 'id'),
               COALESCE((SELECT MAX(id) FROM tv_shows), 0) + 1, false)
    """))

    # ── 11. Strip media down to the anchor (id + created_at only) ─────────────
    for col in [
        'media_type', 'tmdb_id', 'imdb_id', 'title', 'original_title',
        'overview', 'tagline', 'release_date', 'status', 'adult',
        'original_language', 'popularity', 'vote_average', 'vote_count',
        'belongs_to_collection', 'production_countries', 'spoken_languages',
        'origin_country', 'production_companies', 'streaming_providers',
        'poster_path', 'backdrop_path', 'poster_supabase_url', 'backdrop_supabase_url',
        'embedding', 'embedding_needs_rebuild',
        'narrative_dna', 'themes', 'tone_tags',
        'darkness_score', 'complexity_score', 'energy_score',
        'mood_scores', 'context_scores', 'craving_scores', 'is_fully_scored',
        'updated_at',
    ]:
        try:
            op.drop_column('media', col)
        except Exception:
            pass  # column may not exist in all migration paths

    # Drop legacy composite indexes on media that referenced dropped columns
    for idx in [
        'uq_media_tmdb_id_media_type',
        'idx_media_language_popularity',
        'idx_media_release_rating',
        'idx_media_updated_at',
        'idx_media_adult_popularity',
        'idx_media_type_popularity',
    ]:
        op.execute(f'DROP INDEX IF EXISTS {idx}')


def downgrade() -> None:
    raise NotImplementedError(
        "Downgrade from v5 is not supported. Restore from a DB backup."
    )
