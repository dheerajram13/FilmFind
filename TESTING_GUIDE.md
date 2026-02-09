# FilmFind - Complete Testing Guide

This guide will help you test the entire FilmFind application (Frontend + Backend).

## Prerequisites

Before testing, ensure you have:
- PostgreSQL installed and running
- Python 3.11+ with virtual environment
- Node.js 18+ and npm
- TMDB API key (free from https://www.themoviedb.org/settings/api)
- Groq API key (free from https://console.groq.com) OR Ollama running locally

---

## Step 1: Start PostgreSQL Database

### Option A: Using Homebrew (macOS)
```bash
# Start PostgreSQL
brew services start postgresql@14

# Verify it's running
psql --version
```

### Option B: Using Docker
```bash
# Start PostgreSQL in Docker
docker run --name filmfind-db \
  -e POSTGRES_USER=filmfind \
  -e POSTGRES_PASSWORD=filmfind \
  -e POSTGRES_DB=filmfind \
  -p 5432:5432 \
  -d postgres:14

# Verify it's running
docker ps | grep filmfind-db
```

### Option C: Manual PostgreSQL
```bash
# Start PostgreSQL manually
pg_ctl -D /usr/local/var/postgres start

# Or check if it's already running
pg_isready
```

---

## Step 2: Setup Backend Environment

```bash
cd backend

# Activate virtual environment
source venv/bin/activate  # On macOS/Linux
# OR
venv\Scripts\activate  # On Windows

# Install dependencies (if not already installed)
pip install -r requirements.txt

# Create .env file
cat > .env << EOF
# Database
DATABASE_URL=postgresql://filmfind:filmfind@localhost:5432/filmfind

# TMDB API
TMDB_API_KEY=your_tmdb_api_key_here

# LLM Provider (choose one)
LLM_PROVIDER=groq  # or 'ollama' for local
GROQ_API_KEY=your_groq_api_key_here  # Only if using Groq

# Vector Model
VECTOR_MODEL=sentence-transformers/all-mpnet-base-v2

# Redis (optional - for caching)
REDIS_URL=redis://localhost:6379
CACHE_ENABLED=false  # Set to true if Redis is running

# Background Jobs
ENABLE_BACKGROUND_JOBS=false  # Set to true after initial setup
EOF
```

---

## Step 3: Initialize Database & Load Data

### 3.1: Create Database (if using local PostgreSQL)
```bash
# Create database
createdb filmfind

# Or using psql
psql -U postgres -c "CREATE DATABASE filmfind;"
```

### 3.2: Run Database Migrations
```bash
cd backend

# Run Alembic migrations
alembic upgrade head
```

### 3.3: Ingest TMDB Data
```bash
# Fetch popular movies (recommended for testing)
python scripts/ingest_tmdb.py --popular --max-pages 10

# This will fetch ~200 movies (20 per page)
# Takes ~2-3 minutes with rate limiting
```

### 3.4: Generate Embeddings
```bash
# Generate embeddings for all movies
python scripts/generate_embeddings.py

# This downloads the model (~400MB) on first run
# Then generates embeddings for all movies
# Takes ~5-10 minutes for 200 movies
```

### 3.5: Build Vector Index
```bash
# Build FAISS index
python scripts/build_index.py

# Creates index file in backend/data/embeddings/
# Takes ~10-30 seconds
```

### 3.6: Verify Data
```bash
# Check database
python scripts/check_database.py

# Should show:
# - Movies: ~200
# - Genres: ~19
# - Keywords: ~hundreds
# - Cast: ~thousands
# - Embeddings: ~200
```

---

## Step 4: Start Backend Server

```bash
cd backend

# Start FastAPI server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# You should see:
# INFO:     Uvicorn running on http://0.0.0.0:8000
# INFO:     Application startup complete
```

### Test Backend Endpoints

Open another terminal and test:

```bash
# Health check
curl http://localhost:8000/health

# Get trending movies
curl http://localhost:8000/api/trending?limit=10

# Search movies
curl -X POST http://localhost:8000/api/search \
  -H "Content-Type: application/json" \
  -d '{"query": "dark sci-fi movies like Blade Runner", "limit": 10}'

# Get movie details
curl http://localhost:8000/api/movie/550  # Fight Club

# Get similar movies
curl http://localhost:8000/api/movie/similar/550?limit=10
```

---

## Step 5: Setup Frontend Environment

```bash
cd frontend

# Install dependencies (if not already installed)
npm install

# Create .env.local file
cat > .env.local << EOF
NEXT_PUBLIC_API_URL=http://localhost:8000
EOF
```

---

## Step 6: Start Frontend Server

```bash
cd frontend

# Start Next.js dev server
npm run dev

# You should see:
# ▲ Next.js 16.1.1
# - Local:        http://localhost:3000
```

---

## Step 7: Test Complete Flow

### Open your browser to http://localhost:3000

### Test Scenarios:

#### 1. **Homepage (No Search)**
- ✅ Should see hero banner with featured movie
- ✅ Should see "Trending Now" carousel
- ✅ Should see "Discover with AI" section with 12 prompts
- ✅ Should see "Popular Movies" carousel

#### 2. **Search Functionality**
- Type: "dark sci-fi movies"
- ✅ Should switch to search results view
- ✅ Should show ~5-10 relevant movies
- ✅ Movies should have similarity scores
- Clear search → should return to homepage

#### 3. **Discovery Prompts**
- Click: "Dark sci-fi movies like Blade Runner"
- ✅ Should trigger search
- ✅ Should show relevant results

#### 4. **Advanced Filters**
- Click "Filters" button
- ✅ Filter panel should slide in from right
- Select genres: "Science Fiction", "Action"
- Select year range: 2010-2020
- Select min rating: 7+
- Click "Apply Filters"
- ✅ Results should update with filtered movies
- ✅ Filter button should show red dot (active filters)

#### 5. **Movie Detail Page**
- Click on any movie card
- ✅ Should navigate to /movie/[id]
- ✅ Should show backdrop image
- ✅ Should show movie metadata
- ✅ Should show cast carousel
- ✅ Should show similar movies section
- ✅ Back button should work

#### 6. **Movie Carousels**
- On homepage, hover over carousel
- ✅ Navigation arrows should appear
- ✅ Click left/right arrows → should scroll smoothly
- ✅ Cards should show posters, titles, ratings, genres

---

## Troubleshooting

### Backend Issues

#### PostgreSQL Connection Error
```bash
# Check if PostgreSQL is running
pg_isready

# Start PostgreSQL
brew services start postgresql@14
# OR
docker start filmfind-db
```

#### "No movies found" Error
```bash
# Re-run data ingestion
cd backend
python scripts/ingest_tmdb.py --popular --max-pages 10
python scripts/generate_embeddings.py
python scripts/build_index.py
```

#### Import Errors
```bash
# Reinstall dependencies
cd backend
pip install -r requirements.txt
```

#### FAISS Index Not Found
```bash
# Rebuild index
cd backend
python scripts/build_index.py
```

### Frontend Issues

#### API Connection Error
- Check `.env.local` has `NEXT_PUBLIC_API_URL=http://localhost:8000`
- Verify backend is running on port 8000
- Check browser console for CORS errors

#### Build Errors
```bash
# Clean and rebuild
cd frontend
rm -rf .next node_modules
npm install
npm run build
```

#### Type Errors
```bash
# Run type check
cd frontend
npm run type-check
```

---

## Quick Start (TL;DR)

```bash
# Terminal 1: Start PostgreSQL
brew services start postgresql@14

# Terminal 2: Backend Setup & Start
cd backend
source venv/bin/activate
alembic upgrade head
python scripts/ingest_tmdb.py --popular --max-pages 10
python scripts/generate_embeddings.py
python scripts/build_index.py
uvicorn app.main:app --reload

# Terminal 3: Frontend Start
cd frontend
npm run dev

# Open browser: http://localhost:3000
```

---

## Data Statistics

After full setup, you should have:
- **Movies**: ~200 (from 10 pages of popular movies)
- **Genres**: ~19
- **Keywords**: ~500-1000
- **Cast Members**: ~2000-3000
- **Embeddings**: ~200 (768-dimensional vectors)
- **FAISS Index**: 1 file (~2-5 MB)

---

## Performance Expectations

- **Search Response Time**: 200-500ms
- **Movie Detail Load**: 100-300ms
- **Trending Movies**: 50-150ms
- **Similar Movies**: 150-400ms
- **Filter Application**: 200-500ms

---

## Next Steps

After testing:
1. Ingest more data: `--max-pages 50` for ~1000 movies
2. Enable Redis caching for faster responses
3. Enable background jobs for automatic data updates
4. Deploy to production (see DEPLOYMENT.md)

---

## Support

If you encounter issues:
1. Check logs in `backend/logs/`
2. Check browser console (F12)
3. Verify all environment variables are set
4. Ensure all services (PostgreSQL, Backend, Frontend) are running

Happy testing! 🎬
