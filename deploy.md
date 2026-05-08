# FilmFind Production Deployment Plan

## Stack Summary
- **Backend**: FastAPI + sentence-transformers (420MB) + FAISS + Redis
- **Frontend**: Next.js 16
- **Database**: Supabase (already live)
- **Target**: 100% free tier

## Chosen Platforms
| Layer | Platform | Why |
|-------|----------|-----|
| Backend | Hugging Face Spaces (CPU Basic) | Only free tier with 16GB RAM — needed for ML model |
| Frontend | Vercel | Native Next.js, zero config |
| Redis | Upstash | 10K commands/day free, works with existing redis-py |
| Database | Supabase | Already live ✅ |

---

## Phase 1 — Prepare Backend for HF Spaces

### 1.1 Fix docker-compose.yml env var mismatch
`docker-compose.yml` passes `DATABASE_URL: ${SUPABASE_DB_URL}` but `.env` has `DATABASE_URL=...`
**Fix**: Change docker-compose.yml line to `DATABASE_URL: ${DATABASE_URL}`

### 1.2 Create production Dockerfile
HF Spaces requires port 7860. Create `backend/Dockerfile.prod`:
```dockerfile
FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y gcc g++ curl && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Pre-download sentence-transformers model into image (avoids cold-start re-downloads)
RUN python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('sentence-transformers/all-mpnet-base-v2')"

COPY . .
RUN mkdir -p data/embeddings data/raw data/processed logs

EXPOSE 7860

CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 7860"]
```

### 1.3 Set up Upstash Redis
1. Go to https://upstash.com → Create free Redis database (select region closest to Supabase: ap-southeast-2)
2. Copy connection URL: `rediss://:[password]@[host]:6379`
3. Add as `UPSTASH_REDIS_URL` in HF Space Secrets

---

## Phase 2 — Deploy Backend to Hugging Face Spaces

### 2.1 Create HF Space
1. https://huggingface.co → New Space
2. Name: `filmfind-api`
3. SDK: **Docker**
4. Hardware: **CPU Basic** (free, 16GB RAM)
5. Visibility: **Public** (required for free tier)

### 2.2 Add Space Secrets
Settings → Repository Secrets:
```
DATABASE_URL              = postgresql://postgres.[ref]:...@aws-1-ap-southeast-2.pooler.supabase.com:5432/postgres
SUPABASE_URL              = https://[ref].supabase.co
SUPABASE_ANON_KEY         = eyJ...
SUPABASE_SERVICE_ROLE_KEY = eyJ...
GEMINI_API_KEY            = AIza...
GROQ_API_KEY              = gsk_...
TMDB_API_KEY              = ...
SECRET_KEY                = (run: python -c "import secrets; print(secrets.token_urlsafe(32))")
ADMIN_SECRET              = (run same command)
UPSTASH_REDIS_URL         = rediss://:[password]@[host]:6379
CORS_ORIGINS              = https://your-app.vercel.app
LLM_PROVIDER              = gemini
CACHE_ENABLED             = true
ENVIRONMENT               = production
LOG_LEVEL                 = INFO
```

### 2.3 Push to HF Space
```bash
# From repo root — push backend/ as a standalone repo to HF Space
cd /Users/dheeraj/Desktop/work/FilmFind/backend

git init
git remote add space https://huggingface.co/spaces/YOUR_HF_USERNAME/filmfind-api

# Use Dockerfile.prod as the Space's Dockerfile
cp Dockerfile.prod Dockerfile.space
# HF Spaces looks for a file named "Dockerfile" in repo root
mv Dockerfile.space Dockerfile   # temporarily rename for push, keep Dockerfile.prod as backup

git add .
git commit -m "deploy: FilmFind backend to HF Spaces"
git push space main
```

Backend URL after deploy: `https://YOUR_HF_USERNAME-filmfind-api.hf.space`

---

## Phase 3 — Deploy Frontend to Vercel

### 3.1 Connect GitHub repo to Vercel
1. https://vercel.com → New Project → Import GitHub repo
2. **Root Directory**: `frontend/`
3. Framework: Next.js (auto-detected)

### 3.2 Set Environment Variables in Vercel Dashboard
Project Settings → Environment Variables:
```
NEXT_PUBLIC_API_URL       = https://YOUR_HF_USERNAME-filmfind-api.hf.space
NEXT_PUBLIC_SUPABASE_URL  = https://[ref].supabase.co
```

### 3.3 Deploy
Vercel auto-deploys on every push to `main`.
Frontend URL: `https://filmfind.vercel.app` (or your chosen name)

---

## Phase 4 — Wire Together

### 4.1 Update CORS on backend
In HF Space Secrets, set:
```
CORS_ORIGINS = https://filmfind.vercel.app
```
Trigger a redeploy (push a commit or click "Restart Space").

### 4.2 Smoke tests
```bash
BACKEND=https://YOUR_HF_USERNAME-filmfind-api.hf.space

# Health
curl $BACKEND/health

# Search
curl -X POST $BACKEND/api/search \
  -H "Content-Type: application/json" \
  -d '{"query": "sci-fi time travel thriller", "limit": 5}'

# Sixty mode
curl -X POST $BACKEND/api/sixty/pick \
  -H "Content-Type: application/json" \
  -d '{"mood": "happy", "context": "solo-night", "craving": "laugh"}'
```

---

## Phase 5 — Production Cron Pipeline

The backend scheduler (`ENABLE_BACKGROUND_JOBS=true`) runs a full pipeline every **Sunday at 02:00 UTC**:

| Stage | Script | What it does |
|-------|--------|-------------|
| `ingest` | `scripts/ingest/ingest_media.py` | Fetch new movies/TV from TMDB, upsert DB, upload images to Supabase Storage |
| `embed` | `scripts/ml/generate_embeddings.py` | Generate 768-dim embeddings for rows that lack them |
| `index` | `scripts/ml/build_index.py` | Rebuild FAISS HNSW index |
| `enrich` | `scripts/enrich/enrich_films.py` | Gemini LLM enrichment (narrative_dna, themes, tone) |
| `score` | `scripts/ml/score_films.py` | Generate 60-second mode scoring matrices |

All stages are idempotent — safe to re-run. If a stage fails, the chain stops and the next weekly run picks up where it left off.

### Enable on HF Spaces

Add to Space Secrets:
```
ENABLE_BACKGROUND_JOBS = true
```

### Trigger manually (first run after deploy)

```bash
curl -X POST https://YOUR_HF_USERNAME-filmfind-api.hf.space/api/admin/jobs/weekly_pipeline/run \
  -H "Authorization: Bearer $ADMIN_SECRET"
```

---

## Pre-Deploy Checklist

### Already done ✅
- [x] `backend/Dockerfile.prod` created (port 7860, model baked in)
- [x] `docker-compose.yml` fixed: `DATABASE_URL: ${DATABASE_URL}`
- [x] CORS made env-configurable
- [x] Weekly pipeline cron job registered in scheduler

### Still needed
- [ ] `docker compose exec frontend npm run build` — verify no build errors
- [ ] Create Hugging Face account → New Space (Docker, CPU Basic, Public)
- [ ] Create Upstash Redis database (ap-southeast-2 region)
- [ ] Connect GitHub repo to Vercel

### Generate secrets
```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
# Run twice — once for SECRET_KEY, once for ADMIN_SECRET
```

### After deploy
- [ ] Set `CORS_ORIGINS` in HF Space Secrets to your Vercel URL
- [ ] Set `ENABLE_BACKGROUND_JOBS=true` in HF Space Secrets
- [ ] Smoke tests pass (Phase 4.2)
- [ ] Trigger first pipeline run via admin endpoint to populate data

---

## Free Tier Limits to Know

| Limit | Impact |
|-------|--------|
| HF Space sleeps after 48hr inactivity | First request takes ~60s (model reload) |
| Upstash 10K commands/day | ~3K requests/day with caching |
| Gemini 15 RPM / 1500 RPD | Enrich/score pipeline is rate-limited; large datasets take multiple days |
| Only 18 scored films currently | 60-second mode works but is limited — trigger pipeline manually after first deploy |
