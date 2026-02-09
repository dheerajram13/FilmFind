# FilmFind - Docker Quick Start Guide 🐳

This guide shows you how to run FilmFind using Docker - the easiest way to test the entire application!

## Prerequisites

- **Docker Desktop** installed (https://www.docker.com/products/docker-desktop)
- **TMDB API Key** (free from https://www.themoviedb.org/settings/api)
- **Groq API Key** (free from https://console.groq.com) OR Ollama running locally

---

## 🚀 Quick Start (3 Simple Steps)

### Step 1: Configure Environment

```bash
# Copy the example environment file
cp .env.example .env

# Edit .env and add your API keys
nano .env  # or use your favorite editor
```

Required values in `.env`:
```bash
TMDB_API_KEY=your_tmdb_api_key_here
GROQ_API_KEY=your_groq_api_key_here
LLM_PROVIDER=groq
```

### Step 2: Start All Services

```bash
# Start all containers (PostgreSQL, Redis, Backend, Frontend)
docker-compose up -d

# This will:
# - Pull Docker images (~2-3 min first time)
# - Build backend and frontend images (~5-10 min first time)
# - Start all 4 services
# - Run database migrations automatically

# Check if all services are running
docker-compose ps
```

You should see:
```
NAME                  STATUS              PORTS
filmfind-backend      Up                  0.0.0.0:8000->8000/tcp
filmfind-frontend     Up                  0.0.0.0:3000->3000/tcp
filmfind-postgres     Up (healthy)        0.0.0.0:5432->5432/tcp
filmfind-redis        Up (healthy)        0.0.0.0:6379->6379/tcp
```

### Step 3: Initialize Data

```bash
# Run the data initialization script
./init-data.sh

# This will:
# - Fetch 200 popular movies from TMDB (~2-3 min)
# - Generate embeddings (~5-10 min)
# - Build vector search index (~30 sec)
# Total time: ~15-20 minutes
```

### Step 4: Test the Application! 🎉

Open your browser to: **http://localhost:3000**

---

## 📋 What Gets Installed

### Services Running:
1. **PostgreSQL** (port 5432) - Main database
2. **Redis** (port 6379) - Cache layer
3. **Backend API** (port 8000) - FastAPI server
4. **Frontend** (port 3000) - Next.js app

### Data Volumes:
- `postgres_data` - Persistent database storage
- `redis_data` - Cache storage
- `backend_data` - Movie data and embeddings
- `backend_models` - Sentence-transformer models

---

## 🎯 Common Commands

### View Logs
```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f backend
docker-compose logs -f frontend
docker-compose logs -f postgres
```

### Stop Services
```bash
# Stop all services (keeps data)
docker-compose stop

# Stop and remove containers (keeps data)
docker-compose down

# Stop and remove everything including data volumes
docker-compose down -v
```

### Restart Services
```bash
# Restart all
docker-compose restart

# Restart specific service
docker-compose restart backend
```

### Access Container Shell
```bash
# Backend shell
docker exec -it filmfind-backend /bin/bash

# PostgreSQL shell
docker exec -it filmfind-postgres psql -U filmfind -d filmfind

# Frontend shell
docker exec -it filmfind-frontend /bin/sh
```

### Run Backend Commands
```bash
# Run any backend script
docker exec filmfind-backend python scripts/check_database.py

# Run migrations
docker exec filmfind-backend alembic upgrade head

# Fetch more movies
docker exec filmfind-backend python scripts/ingest_tmdb.py --popular --max-pages 50
```

---

## 🧪 Testing Scenarios

Once running, try these:

### 1. Homepage Discovery
- Visit http://localhost:3000
- ✅ See hero banner with featured movie
- ✅ See trending movies carousel
- ✅ See "Discover with AI" section

### 2. Search
- Type: "dark sci-fi movies"
- ✅ Should show AI-powered search results
- ✅ Results have similarity scores

### 3. Filters
- Click "Filters" button
- Select genres, year range, rating
- Click "Apply"
- ✅ Results update with filters

### 4. Movie Details
- Click any movie card
- ✅ See full movie details
- ✅ See cast carousel
- ✅ See similar movies

### 5. API Directly
```bash
# Test backend API
curl http://localhost:8000/health
curl http://localhost:8000/api/trending?limit=10
curl -X POST http://localhost:8000/api/search \
  -H "Content-Type: application/json" \
  -d '{"query": "action movies", "limit": 10}'
```

---

## 🔧 Troubleshooting

### Services Not Starting

**Check logs:**
```bash
docker-compose logs backend
```

**Common issues:**
- Missing API keys in `.env`
- Ports already in use (3000, 8000, 5432, 6379)
- Docker Desktop not running

**Solution:**
```bash
# Stop conflicting services
lsof -ti:3000 | xargs kill
lsof -ti:8000 | xargs kill

# Restart Docker Desktop
# Then retry: docker-compose up -d
```

### Backend Can't Connect to Database

**Wait for health checks:**
```bash
# PostgreSQL takes ~10 seconds to be ready
docker-compose ps

# Wait until postgres shows "healthy"
# Then restart backend
docker-compose restart backend
```

### Embeddings Generation Fails

**Check disk space:**
```bash
# Model download requires ~400MB
# Embeddings require ~50-100MB
df -h
```

**Re-run manually:**
```bash
docker exec -it filmfind-backend /bin/bash
python scripts/generate_embeddings.py
```

### Frontend Build Errors

**Rebuild frontend:**
```bash
docker-compose build frontend --no-cache
docker-compose up -d frontend
```

### Out of Memory

**Increase Docker memory:**
- Docker Desktop → Settings → Resources
- Increase Memory to at least 4GB
- Click "Apply & Restart"

---

## 🔄 Updating Code

### Backend Changes
```bash
# Code changes auto-reload with --reload flag
# Just edit Python files, changes apply immediately

# For dependency changes:
docker-compose build backend
docker-compose up -d backend
```

### Frontend Changes
```bash
# Code changes auto-reload in dev mode
# Just edit TypeScript/React files

# For dependency changes:
docker exec filmfind-frontend npm install
docker-compose restart frontend
```

### Database Schema Changes
```bash
# Create migration
docker exec filmfind-backend alembic revision --autogenerate -m "description"

# Apply migration
docker exec filmfind-backend alembic upgrade head
```

---

## 📊 Monitoring

### Check Service Health
```bash
# All services status
docker-compose ps

# Backend health
curl http://localhost:8000/health

# Detailed health with dependencies
curl http://localhost:8000/health/detailed
```

### Database Statistics
```bash
docker exec filmfind-backend python scripts/check_database.py
```

### Cache Statistics
```bash
curl http://localhost:8000/api/cache/stats
```

---

## 🧹 Cleanup

### Remove All Data and Start Fresh
```bash
# Stop and remove everything
docker-compose down -v

# Remove images
docker rmi filmfind-backend filmfind-frontend

# Start fresh
docker-compose up -d
./init-data.sh
```

### Remove Only Data (Keep Images)
```bash
# Stop services
docker-compose down -v

# Restart (migrations run automatically)
docker-compose up -d
./init-data.sh
```

---

## 🚀 Production Mode

### Build for Production
```bash
# Use production docker-compose
docker-compose -f docker-compose.prod.yml up -d

# Or build production images
docker-compose build --no-cache
```

### Environment for Production
```bash
# Update .env
ENVIRONMENT=production
LOG_LEVEL=WARNING
CACHE_ENABLED=true
ENABLE_BACKGROUND_JOBS=true
```

---

## 📈 Performance Tips

### 1. Enable Redis Caching
Already enabled in docker-compose! Provides:
- 70%+ cache hit rate
- 3-5x faster repeat queries
- Reduced LLM API calls

### 2. Increase Workers
```bash
# In docker-compose.yml, update backend command:
command: uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
```

### 3. Pre-load More Data
```bash
# Fetch 1000 movies instead of 200
docker exec filmfind-backend python scripts/ingest_tmdb.py --popular --max-pages 50
docker exec filmfind-backend python scripts/generate_embeddings.py
docker exec filmfind-backend python scripts/build_index.py
```

---

## ✨ Benefits of Docker Setup

✅ **Zero Local Dependencies** - Everything runs in containers
✅ **Consistent Environment** - Same setup on any machine
✅ **Easy Cleanup** - Remove everything with one command
✅ **Automatic Migrations** - Database auto-updates on start
✅ **Health Checks** - Services auto-restart if unhealthy
✅ **Hot Reload** - Code changes apply without restart
✅ **Persistent Data** - Data survives container restarts
✅ **Isolated Network** - Services communicate internally

---

## 🎬 Ready to Test!

```bash
# TL;DR - Complete setup in 3 commands:
cp .env.example .env  # Then add your API keys
docker-compose up -d
./init-data.sh

# Open http://localhost:3000
# Enjoy! 🍿
```

---

## Need Help?

- Check logs: `docker-compose logs -f`
- View running containers: `docker ps`
- Check volumes: `docker volume ls`
- System cleanup: `docker system prune -a`

For more detailed testing scenarios, see [TESTING_GUIDE.md](TESTING_GUIDE.md)
