# FilmFind — AI-Powered Semantic Movie Discovery

> **Describe what you want to watch. FilmFind finds it.**

FilmFind is a semantic movie and TV show discovery engine that understands natural language. Ask for *"dark sci-fi movies like Interstellar with less romance"* and get back ranked, explained recommendations — not just keyword matches.

[![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.104+-green.svg)](https://fastapi.tiangolo.com/)
[![Next.js](https://img.shields.io/badge/Next.js-16-black.svg)](https://nextjs.org/)

---

## How It Works

A search request flows through a multi-stage AI pipeline:

```
Query → LLM Parse → Embed (768-dim) → FAISS HNSW → Filter → Score → LLM Re-rank → Results
```

1. **QueryParser** — Gemini extracts themes, genres, year/language constraints, reference titles
2. **EmbeddingService** — sentence-transformers (`all-mpnet-base-v2`) encodes the query to a 768-dim vector
3. **SemanticRetrievalEngine** — FAISS HNSW finds top-k candidates by cosine similarity
4. **FilterEngine** — applies hard filters (genre, year, rating, language, streaming provider)
5. **MultiSignalScoringEngine** — re-ranks by semantic 50% + genre 20% + popularity/rating/recency 10% each
6. **LLMReRanker** — Gemini writes a natural-language explanation for each result

**60-Second Mode**: user picks mood/context/craving → SQL scoring across all enriched films → weighted random pick → LLM generates why-reasons.

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | FastAPI, Python 3.11, SQLAlchemy, Alembic |
| Database | PostgreSQL via Supabase (pgvector HNSW index) |
| ML | sentence-transformers/all-mpnet-base-v2 (768-dim), FAISS |
| LLM | Gemini 2.0 Flash (primary) → Groq Llama 3.3 70B (fallback) → rule-based |
| Cache | Redis (local dev) / Upstash (production) |
| Frontend | Next.js 16, React 19, TypeScript, TailwindCSS 4, Framer Motion |
| Images | Supabase Storage (poster/backdrop CDN) |

---

## Getting Started

All services run via Docker Compose — no local Python or Node setup required.

### 1. Clone and configure

```bash
git clone https://github.com/dheerajram13/FilmFind.git
cd FilmFind
cp .env.example .env
# Fill in your API keys (see .env.example for all required vars)
```

### 2. Required API keys

| Key | Where to get |
|-----|-------------|
| `DATABASE_URL` | Supabase project → Settings → Database |
| `SUPABASE_URL` / `SUPABASE_ANON_KEY` / `SUPABASE_SERVICE_ROLE_KEY` | Supabase project → Settings → API |
| `GEMINI_API_KEY` | [Google AI Studio](https://aistudio.google.com/) (free) |
| `GROQ_API_KEY` | [Groq Console](https://console.groq.com/) (free) |
| `TMDB_API_KEY` | [TMDB Settings](https://www.themoviedb.org/settings/api) (free) |

### 3. Start

```bash
docker compose up --build
```

- Frontend: http://localhost:3000
- Backend API: http://localhost:8000
- API docs: http://localhost:8000/api/docs (development only)

### 4. Run the data pipeline (first time)

```bash
# Ingest media from TMDB
docker compose exec backend python scripts/ingest/ingest_media.py

# Generate embeddings
docker compose exec backend python scripts/ml/generate_embeddings.py

# Build FAISS index
docker compose exec backend python scripts/ml/build_index.py

# LLM enrichment for 60-second mode (uses Gemini free tier)
docker compose exec backend python scripts/enrich/enrich_films.py
docker compose exec backend python scripts/ml/score_films.py
```

---

## Project Structure

```
FilmFind/
├── backend/
│   ├── app/
│   │   ├── api/
│   │   │   ├── routes/           # search, sixty, admin, health
│   │   │   ├── dependencies.py   # DB session, auth, rate limiting, injection guard
│   │   │   └── exceptions.py     # Custom exception hierarchy
│   │   ├── core/
│   │   │   ├── config.py         # Pydantic settings (all env vars)
│   │   │   ├── database.py       # SQLAlchemy engine + session
│   │   │   ├── cache_manager.py  # Redis wrapper
│   │   │   ├── middleware.py     # Security headers, error handling, logging
│   │   │   ├── scheduler.py      # APScheduler background jobs
│   │   │   └── scoring.py        # 60-sec mode valid enums + profiles
│   │   ├── models/
│   │   │   ├── media.py          # Media base + Movie/TVShow subclasses (STI)
│   │   │   └── session.py        # SearchSession, SixtySession analytics
│   │   ├── schemas/
│   │   │   ├── movie.py          # MovieResponse, MovieSearchResult (Pydantic v2)
│   │   │   ├── query.py          # QueryIntent, QueryConstraints, ParsedQuery
│   │   │   └── search.py         # SearchRequest, SearchResponse
│   │   ├── services/
│   │   │   ├── query_parser.py   # LLM query → structured intent
│   │   │   ├── embedding_service.py  # sentence-transformers wrapper
│   │   │   ├── retrieval_engine.py   # FAISS HNSW search
│   │   │   ├── filter_engine.py      # Hard filter application
│   │   │   ├── scoring_engine.py     # Multi-signal scoring weights
│   │   │   ├── reranker.py           # LLM re-ranking + explanations
│   │   │   ├── sixty_scorer.py       # SQL scoring for 60-sec mode
│   │   │   ├── film_admin_service.py # Enrich / embed / cache refresh
│   │   │   └── llm_client.py         # Gemini → Groq → rule-based fallback
│   │   ├── repositories/
│   │   │   ├── movie_repository.py   # Full DB query repository
│   │   │   └── query_utils.py        # Lightweight query helpers
│   │   ├── db/
│   │   │   └── sessions.py       # Fire-and-forget analytics logging
│   │   └── main.py               # FastAPI app + middleware stack
│   ├── scripts/
│   │   ├── ingest/               # TMDB ingestion + DB seeding
│   │   ├── enrich/               # LLM narrative enrichment + streaming backfill
│   │   ├── ml/                   # Embeddings, FAISS index, sixty-mode scoring
│   │   ├── migrate/              # One-time migrations (Supabase image upload)
│   │   └── utils/                # DB health check, query parser tester
│   ├── tests/                    # pytest suite (500+ tests)
│   ├── alembic/                  # DB migrations
│   ├── Dockerfile.prod           # Production image (port 7860 for HF Spaces)
│   └── requirements.txt
│
├── frontend/
│   ├── app/
│   │   ├── page.tsx              # Entry point — renders FilmfindHome
│   │   ├── layout.tsx            # Root layout + metadata
│   │   └── globals.css           # Global styles
│   ├── components/home/
│   │   ├── FilmfindHome.tsx      # Top-level state orchestrator
│   │   ├── HomeScreen.tsx        # Landing / search input
│   │   ├── ResultsScreen.tsx     # Search results list
│   │   ├── DetailScreen.tsx      # Movie detail view
│   │   ├── ResultCard.tsx        # Individual result card
│   │   ├── FiltersSidebar.tsx    # Genre/year/streaming filters
│   │   └── SixtySecondMode.tsx   # 60-second pick mode
│   ├── hooks/
│   │   ├── useSearch.ts          # Search state + AbortController
│   │   └── useFilters.ts         # Client-side filter state
│   ├── lib/
│   │   ├── api-client.ts         # Typed fetch wrapper (AbortSignal support)
│   │   ├── movie-formatters.ts   # Pure formatting helpers
│   │   ├── streaming-providers.ts # Provider name normalisation
│   │   └── image-utils.ts        # TMDB/Supabase image URL helpers
│   └── types/
│       └── api.ts                # TypeScript interfaces matching backend schemas
│
├── .env.example                  # All required env vars with descriptions
├── docker-compose.yml            # 3-service dev stack (backend, frontend, redis)
├── plan.md                       # Deployment plan (HF Spaces + Vercel + Upstash)
└── deploy.md                     # Step-by-step deployment guide
```

---

## API Reference

### Search

```http
POST /api/search
Content-Type: application/json

{
  "query": "dark sci-fi movies like Interstellar with less romance",
  "limit": 10,
  "filters": {
    "year_min": 2010,
    "language": "en"
  }
}
```

### 60-Second Mode

```http
POST /api/sixty/pick
Content-Type: application/json

{
  "mood": "chill",
  "context": "solo-night",
  "craving": "mind-blown"
}
```

Valid values:
- `mood`: `happy` `sad` `charged` `chill` `adventurous` `romantic`
- `context`: `family` `date-night` `solo-night` `friends` `movie-night` `background`
- `craving`: `laugh` `cry` `mind-blown` `thrilled` `inspired` `scared` `comforted` `wowed`

### Health

```http
GET /health
GET /health/detailed
```

---

## Security

- Rate limiting: 20 req/min (search), 10 req/min (sixty/pick) per IP — sliding window via Redis
- Prompt injection guard on all queries
- Admin endpoints require `Authorization: Bearer <ADMIN_SECRET>`
- Security headers: HSTS, CSP, X-Frame-Options, Permissions-Policy
- CORS restricted to configured origins only

---

## Development Commands

```bash
# Run tests
docker compose exec backend python -m pytest

# Linting
docker compose exec backend ruff check app/
docker compose exec frontend npm run lint

# Type checking
docker compose exec backend mypy app/
docker compose exec frontend npm run type-check

# DB migrations
docker compose exec backend alembic upgrade head

# Restart a single service
docker compose restart backend
```

---

## Deployment

See [deploy.md](deploy.md) for the full guide. Target stack (100% free tier):

| Service | Platform |
|---------|----------|
| Backend | Hugging Face Spaces (CPU Basic, 16GB RAM) |
| Frontend | Vercel |
| Database | Supabase (already live) |
| Cache | Upstash Redis |

---

## Author

**Dheeraj Srirama**
- GitHub: [@dheerajram13](https://github.com/dheerajram13)
- LinkedIn: [dheerajsrirama](https://linkedin.com/in/dheerajsrirama)
- Email: sriramadheeraj@gmail.com

---

## License

MIT
