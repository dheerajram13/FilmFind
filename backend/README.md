# FilmFind Backend

AI-Powered Semantic Movie Discovery Engine - Backend API

## Tech Stack

- **Python 3.11+**
- **FastAPI** - Modern async web framework
- **PostgreSQL** - Primary database
- **SQLAlchemy** - ORM
- **FAISS** - Vector similarity search
- **Redis** - Caching layer
- **Sentence Transformers** - Embedding generation
- **Groq API** - LLM for query understanding and re-ranking

## Project Structure

```
backend/
├── app/
│   ├── api/
│   │   └── routes/          # API endpoints
│   ├── core/                # Core configuration
│   ├── models/              # Database models
│   ├── schemas/             # Pydantic schemas
│   └── services/            # Business logic
├── scripts/                 # Data processing scripts
├── tests/                   # Unit tests
└── requirements.txt
```

## Setup

### 1. Install Dependencies

```bash
cd backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Environment Configuration

Copy `.env.example` to `.env` and update with your credentials:

```bash
cp .env.example .env
```

Required API keys:
- TMDB_API_KEY - Get from https://www.themoviedb.org/settings/api
- GROQ_API_KEY - Get from https://console.groq.com

### 3. Database Setup

```bash
# Start PostgreSQL (or use Supabase)
docker run -d \
  --name filmfind-postgres \
  -e POSTGRES_PASSWORD=postgres \
  -e POSTGRES_DB=filmfind \
  -p 5432:5432 \
  postgres:14

# Run migrations (after implementing Module 1.2)
alembic upgrade head
```

### 4. Redis Setup

```bash
# Local Redis
docker run -d --name filmfind-redis -p 6379:6379 redis:7

# Or use Upstash free tier
```

### 5. Run the Application

```bash
uvicorn app.main:app --reload --port 8000
```

API will be available at:
- Docs: http://localhost:8000/api/docs
- ReDoc: http://localhost:8000/api/redoc

## Development Workflow

### Module Implementation Order (from plan.md)

**Phase 1: Data Foundation**
1. Module 1.1: TMDB Data Ingestion Service
2. Module 1.2: Database Schema & Setup
3. Module 1.3: Embedding Generation Pipeline
4. Module 1.4: Vector Database Setup

**Phase 2: Intelligence Layer**
5. Module 2.1: Query Understanding Service
6. Module 2.2: Semantic Retrieval Engine
7. Module 2.3: Multi-Signal Scoring Engine
8. Module 2.4: RAG Re-Ranking Service
9. Module 2.5: Filter & Constraint Handler

**Phase 3: API & Backend**
10. Module 3.1: FastAPI Application Setup ✓
11. Module 3.2: Search & Recommendation API
12. Module 3.3: Caching Layer
13. Module 3.4: Background Jobs & Data Updates

## Scripts

### Data Ingestion
```bash
# Fetch movies from TMDB (Module 1.1)
python scripts/ingest_tmdb.py --limit 10000

# Generate embeddings (Module 1.3)
python scripts/generate_embeddings.py

# Build FAISS index (Module 1.4)
python scripts/build_index.py
```

## Testing

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=app --cov-report=html

# Run specific test file
pytest tests/test_search.py
```

## Docker

```bash
# Build image
docker build -t filmfind-backend .

# Run container
docker run -d \
  --name filmfind-backend \
  -p 8000:8000 \
  --env-file .env \
  filmfind-backend
```

## API Endpoints (To be implemented)

### Search
- `POST /api/search` - Natural language movie search
- `POST /api/search/similar` - Find similar movies

### Movies
- `GET /api/movies/{movie_id}` - Get movie details
- `GET /api/movies/trending` - Get trending movies

### Health
- `GET /` - Root endpoint
- `GET /health` - Health check

## Free Tier Resources

- **TMDB API**: Free tier available
- **Groq API**: 30 requests/minute free
- **Upstash Redis**: 10,000 commands/day free
- **Supabase**: Free PostgreSQL database
- **Sentence Transformers**: Free, runs locally

## License

MIT
