#!/usr/bin/env bash
# push_to_hf.sh — push the backend to Hugging Face Spaces
#
# Usage:
#   ./push_to_hf.sh <HF_USERNAME>
#
# Example:
#   ./push_to_hf.sh dheerajram13
#
# Prerequisites:
#   - HF account created at https://huggingface.co
#   - Space created: New Space → Name: filmfind-api → SDK: Docker → Hardware: CPU Basic → Public
#   - HF token with write access: https://huggingface.co/settings/tokens
#   - git-lfs installed: brew install git-lfs

set -e

HF_USERNAME="${1:?Usage: ./push_to_hf.sh <HF_USERNAME>}"
SPACE_NAME="filmfind-api"
HF_REPO="git@hf.co:spaces/${HF_USERNAME}/${SPACE_NAME}"
BACKEND_DIR="$(cd "$(dirname "$0")/backend" && pwd)"
WORK_DIR="/tmp/filmfind-hf-push"

echo "==> Pushing backend to HF Space: ${HF_REPO}"

# ── 1. Clean working dir ─────────────────────────────────────────────────────
rm -rf "$WORK_DIR"
mkdir -p "$WORK_DIR"

# ── 2. Clone the HF Space (creates an empty repo on first push) ──────────────
echo "==> Cloning HF Space..."
git clone "$HF_REPO" "$WORK_DIR" || {
  # Space may be brand-new with no commits — init manually
  cd "$WORK_DIR"
  git init
  git remote add origin "$HF_REPO"
}

cd "$WORK_DIR"
# Install git-lfs if available (not required for Python/text files)
git lfs install --local 2>/dev/null || true

# ── 3. Copy backend files ────────────────────────────────────────────────────
echo "==> Copying backend files..."
# Use rsync to respect .gitignore patterns
rsync -a --delete \
  --exclude='.git' \
  --exclude='__pycache__' \
  --exclude='*.pyc' \
  --exclude='.env' \
  --exclude='.env.*' \
  --exclude='logs/' \
  --exclude='data/raw/' \
  --exclude='data/processed/' \
  --exclude='data/embeddings/' \
  --exclude='.pytest_cache' \
  --exclude='*.egg-info' \
  "${BACKEND_DIR}/" .

# ── 4. HF Spaces requires a file named exactly "Dockerfile" ─────────────────
echo "==> Setting up Dockerfile..."
if [ -f Dockerfile.prod ]; then
  cp Dockerfile.prod Dockerfile
  echo "Copied Dockerfile.prod → Dockerfile"
fi

# ── 5. Commit and push ───────────────────────────────────────────────────────
echo "==> Committing..."
git add -A
git commit -m "deploy: FilmFind backend $(date -u +%Y-%m-%dT%H:%M:%SZ)" || echo "Nothing to commit"

echo "==> Pushing to HF Space..."
git push origin main

echo ""
echo "✅ Done! Your Space will build at:"
echo "   https://huggingface.co/spaces/${HF_USERNAME}/${SPACE_NAME}"
echo ""
echo "Next steps:"
echo "  1. Add Secrets in Space Settings:"
echo "     DATABASE_URL, SUPABASE_URL, SUPABASE_ANON_KEY, SUPABASE_SERVICE_ROLE_KEY"
echo "     GEMINI_API_KEY, GROQ_API_KEY, TMDB_API_KEY"
echo "     SECRET_KEY, ADMIN_SECRET (generate: python -c \"import secrets; print(secrets.token_urlsafe(32))\")"
echo "     UPSTASH_REDIS_URL, CORS_ORIGINS, LLM_PROVIDER=gemini"
echo "     CACHE_ENABLED=true, ENVIRONMENT=production, LOG_LEVEL=INFO"
echo "     ENABLE_BACKGROUND_JOBS=true"
echo "  2. Wait for build (~5-10 min on first run — model download is ~420MB)"
echo "  3. Run: ./push_to_hf.sh ${HF_USERNAME}  again to redeploy after any change"
