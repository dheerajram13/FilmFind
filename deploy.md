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

## Pre-Deploy Checklist

### Code changes needed NOW (before any deploy)
- [ ] Create `backend/Dockerfile.prod` (port 7860, model baked in)
- [ ] Fix `docker-compose.yml`: `DATABASE_URL: ${DATABASE_URL}` (was `${SUPABASE_DB_URL}`)
- [ ] Build + verify frontend: `docker compose exec frontend npm run build`

### Accounts to create
- [ ] Hugging Face account at https://huggingface.co
- [ ] Upstash account at https://upstash.com
- [ ] Vercel account at https://vercel.com (or log in with GitHub)

### Secrets to generate
- [ ] `SECRET_KEY` — `python -c "import secrets; print(secrets.token_urlsafe(32))"`
- [ ] `ADMIN_SECRET` — same command

### After deploy
- [ ] CORS_ORIGINS updated to Vercel URL
- [ ] Smoke tests pass
- [ ] Run enrichment pipeline to score more films for sixty-mode:
  ```bash
  # On HF Space terminal or locally against Supabase:
  docker compose exec backend python scripts/ml/generate_embeddings.py
  docker compose exec backend python scripts/ml/build_index.py
  # LLM enrichment (rate-limited to 1500/day on Gemini free tier):
  docker compose exec backend python scripts/ml/score_films.py
  ```

---

## Free Tier Limits to Know

| Limit | Impact |
|-------|--------|
| HF Space sleeps after 48hr inactivity | First request takes ~60s (model reload) |
| Upstash 10K commands/day | ~3K requests/day with caching |
| Gemini 15 RPM / 1500 RPD | LLM calls degrade under heavy load |
| Only 18 scored films | 60-second mode limited until enrichment runs |
