#!/bin/bash

# FilmFind Data Initialization Script for Docker
# This script initializes the database with sample movies

set -e

echo "🎬 FilmFind Data Initialization"
echo "================================"
echo ""

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

# Check if backend container is running
if ! docker ps | grep -q filmfind-backend; then
    echo -e "${RED}✗ Backend container is not running${NC}"
    echo "Please start the containers first: docker-compose up -d"
    exit 1
fi

echo -e "${GREEN}✓ Backend container is running${NC}"
echo ""

# Function to run command in backend container
run_in_backend() {
    docker exec filmfind-backend "$@"
}

# Check if data already exists
MOVIE_COUNT=$(run_in_backend python -c "
from app.core.database import get_db
from app.models.movie import Movie
from sqlalchemy import func
try:
    db = next(get_db())
    count = db.query(func.count(Movie.id)).scalar()
    print(count or 0)
except Exception as e:
    print(0)
" 2>/dev/null || echo "0")

if [ "$MOVIE_COUNT" -gt "0" ]; then
    echo -e "${YELLOW}Database already has $MOVIE_COUNT movies${NC}"
    echo ""
    read -p "Do you want to reinitialize the data? This will clear existing data. (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "Keeping existing data. Exiting."
        exit 0
    fi
fi

echo ""
echo -e "${YELLOW}Starting data initialization...${NC}"
echo "This will take approximately 15-20 minutes."
echo ""

# Step 1: Ingest movies from TMDB
echo -e "${YELLOW}Step 1/4: Fetching movies from TMDB (2-3 minutes)...${NC}"
run_in_backend python scripts/ingest_tmdb.py --strategy popular --max-pages 10
echo -e "${GREEN}✓ Fetched ~200 popular movies${NC}"
echo ""

# Step 2: Seed database from JSON files
echo -e "${YELLOW}Step 2/4: Loading movies into database (1-2 minutes)...${NC}"
run_in_backend python scripts/seed_database.py
echo -e "${GREEN}✓ Loaded movies into database${NC}"
echo ""

# Step 3: Generate embeddings
echo -e "${YELLOW}Step 3/4: Generating embeddings (5-10 minutes)...${NC}"
echo "This will download the sentence-transformers model (~400MB) on first run."
run_in_backend python scripts/generate_embeddings.py
echo -e "${GREEN}✓ Generated embeddings for all movies${NC}"
echo ""

# Step 4: Build vector index
echo -e "${YELLOW}Step 4/4: Building FAISS vector index (30 seconds)...${NC}"
run_in_backend python scripts/build_index.py
echo -e "${GREEN}✓ Built vector search index${NC}"
echo ""

# Final count
FINAL_COUNT=$(run_in_backend python -c "
from app.core.database import get_db
from app.models.movie import Movie
from sqlalchemy import func
db = next(get_db())
print(db.query(func.count(Movie.id)).scalar())
" 2>/dev/null)

echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}✓ Data initialization complete!${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo "Database statistics:"
echo "  • Movies: $FINAL_COUNT"
echo "  • Embeddings: $FINAL_COUNT"
echo "  • Vector index: Ready"
echo ""
echo "You can now test the application at:"
echo "  http://localhost:3000"
echo ""
