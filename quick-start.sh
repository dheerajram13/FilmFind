#!/bin/bash

# FilmFind Quick Start Script
# This script helps you quickly set up and test the FilmFind application

set -e

echo "🎬 FilmFind Quick Start"
echo "======================="
echo ""

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Check if PostgreSQL is running
echo -e "${YELLOW}Checking PostgreSQL...${NC}"
if pg_isready > /dev/null 2>&1; then
    echo -e "${GREEN}✓ PostgreSQL is running${NC}"
else
    echo -e "${RED}✗ PostgreSQL is not running${NC}"
    echo "Starting PostgreSQL..."
    if command -v brew &> /dev/null; then
        brew services start postgresql@14 || brew services start postgresql
    else
        echo "Please start PostgreSQL manually and run this script again"
        exit 1
    fi
fi

echo ""

# Check backend setup
echo -e "${YELLOW}Checking backend setup...${NC}"
cd backend

if [ ! -f ".env" ]; then
    echo -e "${RED}✗ Backend .env file not found${NC}"
    echo "Please create backend/.env file with your API keys"
    echo "See backend/.env.example for reference"
    exit 1
else
    echo -e "${GREEN}✓ Backend .env file exists${NC}"
fi

# Activate virtual environment
if [ -d "venv" ]; then
    echo -e "${GREEN}✓ Virtual environment found${NC}"
    source venv/bin/activate
else
    echo -e "${RED}✗ Virtual environment not found${NC}"
    echo "Creating virtual environment..."
    python3 -m venv venv
    source venv/bin/activate
    pip install -r requirements.txt
fi

# Check if database has movies
echo ""
echo -e "${YELLOW}Checking database...${NC}"
MOVIE_COUNT=$(python -c "
from app.core.database import get_db
from app.models.movie import Movie
from sqlalchemy import func
try:
    db = next(get_db())
    count = db.query(func.count(Movie.id)).scalar()
    print(count)
except:
    print('0')
" 2>/dev/null || echo "0")

if [ "$MOVIE_COUNT" -eq "0" ]; then
    echo -e "${RED}✗ No movies in database${NC}"
    echo ""
    echo "Do you want to ingest sample data? This will:"
    echo "  1. Run database migrations"
    echo "  2. Fetch 200 popular movies from TMDB"
    echo "  3. Generate embeddings (~5-10 min)"
    echo "  4. Build vector index"
    echo ""
    read -p "Proceed? (y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo ""
        echo -e "${YELLOW}Step 1/4: Running migrations...${NC}"
        alembic upgrade head

        echo -e "${YELLOW}Step 2/4: Ingesting movies (this may take 2-3 minutes)...${NC}"
        python scripts/ingest_tmdb.py --popular --max-pages 10

        echo -e "${YELLOW}Step 3/4: Generating embeddings (this may take 5-10 minutes)...${NC}"
        python scripts/generate_embeddings.py

        echo -e "${YELLOW}Step 4/4: Building vector index...${NC}"
        python scripts/build_index.py

        echo -e "${GREEN}✓ Data setup complete!${NC}"
    else
        echo "Please set up data manually. See TESTING_GUIDE.md"
        exit 1
    fi
else
    echo -e "${GREEN}✓ Database has $MOVIE_COUNT movies${NC}"
fi

cd ..

# Check frontend setup
echo ""
echo -e "${YELLOW}Checking frontend setup...${NC}"
cd frontend

if [ ! -f ".env.local" ]; then
    echo -e "${YELLOW}Creating frontend .env.local file...${NC}"
    cat > .env.local << EOF
NEXT_PUBLIC_API_URL=http://localhost:8000
EOF
    echo -e "${GREEN}✓ Created .env.local${NC}"
else
    echo -e "${GREEN}✓ Frontend .env.local exists${NC}"
fi

if [ ! -d "node_modules" ]; then
    echo -e "${YELLOW}Installing frontend dependencies...${NC}"
    npm install
fi

cd ..

# Final instructions
echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}Setup Complete! Ready to start testing.${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo "To start the application, run these commands in separate terminals:"
echo ""
echo -e "${YELLOW}Terminal 1 - Backend:${NC}"
echo "  cd backend"
echo "  source venv/bin/activate"
echo "  uvicorn app.main:app --reload"
echo ""
echo -e "${YELLOW}Terminal 2 - Frontend:${NC}"
echo "  cd frontend"
echo "  npm run dev"
echo ""
echo -e "${YELLOW}Then open your browser:${NC}"
echo "  http://localhost:3000"
echo ""
echo "See TESTING_GUIDE.md for detailed testing scenarios."
echo ""
