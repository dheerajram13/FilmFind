# FilmFind Backend

FastAPI backend for the FilmFind semantic movie discovery engine.

## Stack

- **Python 3.11+**, FastAPI, SQLAlchemy 2.0, Alembic
- **PostgreSQL** via Supabase with pgvector (HNSW cosine index)
- **FAISS** HNSW for local vector search
- **sentence-transformers/all-mpnet-base-v2** — 768-dim embeddings
- **Gemini 2.0 Flash** (primary LLM) → **Groq Llama 3.3 70B** (fallback) → rule-based
- **Redis** for caching and rate limiting

## Quick Start

All commands run inside Docker — no local Python setup needed.

```bash
# From repo root
docker compose up --build

# Run tests
docker compose exec backend python -m pytest

# Lint
docker compose exec backend ruff check app/

# Type check
docker compose exec backend mypy app/

# Migrations
docker compose exec backend alembic upgrade head
```

API available at http://localhost:8000  
Swagger docs (dev only): http://localhost:8000/api/docs

## Environment Variables

Copy `.env.example` to `.env`. Required:

| Variable | Description |
|----------|-------------|
| `DATABASE_URL` | Supabase PostgreSQL connection string |
| `SUPABASE_URL` | Supabase project URL |
| `SUPABASE_ANON_KEY` | Supabase anon key |
| `SUPABASE_SERVICE_ROLE_KEY` | Supabase service role key (backend only) |
| `GEMINI_API_KEY` | Google AI Studio key (primary LLM) |
| `GROQ_API_KEY` | Groq key (fallback LLM) |
| `TMDB_API_KEY` | TMDB API key |

Optional:

| Variable | Default | Description |
|----------|---------|-------------|
| `LLM_PROVIDER` | `gemini` | Primary LLM provider |
| `CACHE_ENABLED` | `true` | Enable Redis caching |
| `ADMIN_SECRET` | — | Bearer token for admin endpoints |
| `CORS_ORIGINS` | `http://localhost:3000` | Comma-separated allowed origins |
| `WEIGHT_SEMANTIC` | `0.5` | Semantic similarity scoring weight |
| `WEIGHT_GENRE` | `0.2` | Genre match scoring weight |

## Data Pipeline

Run once after setup, in order:

```bash
# 1. Ingest media from TMDB
docker compose exec backend python scripts/ingest/ingest_media.py

# 2. Generate 768-dim embeddings for all media
docker compose exec backend python scripts/ml/generate_embeddings.py

# 3. Build FAISS HNSW index
docker compose exec backend python scripts/ml/build_index.py

# 4. LLM enrichment (narrative_dna, themes, tone — needs Gemini key)
docker compose exec backend python scripts/enrich/enrich_films.py

# 5. Generate 60-second mode scoring matrices
docker compose exec backend python scripts/ml/score_films.py
```

## Scripts Layout

```
scripts/
├── ingest/     # TMDB ingestion, DB seeding
├── enrich/     # LLM narrative enrichment, streaming backfill
├── ml/         # Embeddings, FAISS index, sixty-mode scoring
├── migrate/    # One-time migrations (Supabase image upload)
└── utils/      # DB health check, query parser tester
```

## Key Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/health` | Health check |
| `POST` | `/api/search` | Natural language search |
| `GET` | `/api/movie/{id}` | Movie details |
| `GET` | `/api/movie/similar/{id}` | Similar movies |
| `POST` | `/api/sixty/pick` | 60-second mode pick |
| `POST` | `/api/sixty/{id}/action` | Log watch/share/retry |
| `GET` | `/api/admin/analytics/searches` | Search analytics (admin) |
| `POST` | `/api/admin/enrich/{id}` | Re-enrich a film (admin) |
| `POST` | `/api/admin/cache/sixty/refresh` | Rebuild sixty-mode cache (admin) |

## Production Dockerfile

`Dockerfile.prod` targets port 7860 (Hugging Face Spaces requirement) and bakes the sentence-transformers model into the image to avoid cold-start downloads.

```bash
docker build -f Dockerfile.prod -t filmfind-backend .
```
