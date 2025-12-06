# 🎬 FilmFind - AI-Powered Semantic Movie Discovery Engine

> **Discover movies that match your mood, not just your keywords.**

FilmFind is a cutting-edge AI-powered movie and TV series recommendation system that understands natural language queries, interprets emotional intent, and delivers personalized recommendations using semantic search, hybrid embeddings, and LLM-powered re-ranking.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.104+-green.svg)](https://fastapi.tiangolo.com/)
[![Next.js](https://img.shields.io/badge/Next.js-14+-black.svg)](https://nextjs.org/)

---

## 📖 Table of Contents

- [Overview](#-overview)
- [Key Features](#-key-features)
- [What Makes FilmFind Unique](#-what-makes-filmfind-unique)
- [Architecture](#-architecture)
- [System Diagrams](#-system-diagrams)
- [Tech Stack](#-tech-stack)
- [Getting Started](#-getting-started)
- [Project Structure](#-project-structure)
- [API Documentation](#-api-documentation)
- [Roadmap](#-roadmap)
- [Contributing](#-contributing)
- [License](#-license)

---

## 🎯 Overview

FilmFind goes beyond traditional movie recommendation systems by:

- **Understanding Natural Language**: Ask in plain English like *"dark sci-fi movies like Interstellar with less romance"*
- **Semantic Search**: Uses vector embeddings to understand themes, tones, and emotions
- **Hybrid Intelligence**: Combines semantic similarity, metadata filtering, and LLM reasoning
- **Explainable AI**: Each recommendation comes with reasoning and match scores
- **Multi-Signal Scoring**: Balances semantic similarity, popularity, ratings, and recency

### Example Queries

```
"Shows like Stranger Things but with more horror elements"
"Movies about F1 racing with intense competition and personal rivalries"
"Mystery and magical adventures like Harry Potter with school settings"
"Lighthearted sitcoms like Friends about group of friends navigating life and relationships"
```

---

## ✨ Key Features

### 🧠 **Intelligent Query Understanding**
- Natural language processing (NLP) to extract intent, themes, and constraints
- Emotion-aware classification across 8 emotional dimensions
- Reference title detection and similarity matching
- Multi-language support (English, Hindi, Korean, Telugu, etc.)

### 🔍 **Advanced Search & Retrieval**
- **Semantic Vector Search**: FAISS-powered similarity search
- **Hybrid Embeddings**: Combines plot, themes, genres, cast, and emotional vectors
- **Multi-Signal Ranking**: Balances semantic similarity, popularity, ratings, and metadata
- **Smart Filtering**: Year range, language, genre, streaming services, runtime

### 🤖 **LLM-Powered Re-Ranking**
- Uses Groq API (Llama 3.1 70B) or Ollama for intelligent re-ranking
- Contextual understanding of nuanced queries
- Generates human-readable explanations for each recommendation
- Cost-optimized with caching and free tier APIs

### 📊 **Rich Metadata Integration**
- 10,000+ movies and TV shows from TMDB
- Cast, crew, keywords, genres, ratings, popularity
- Streaming availability (Netflix, Prime, Disney+, etc.)
- Posters, backdrops, trailers

---

## 🌟 What Makes FilmFind Unique

### Comparison with Existing Platforms

| Feature | Letterboxd | FilmCrave | MOVIERECS.AI | **FilmFind** |
|---------|-----------|-----------|--------------|--------------|
| **Natural Language Queries** | ❌ Basic search | ❌ No | ⚠️ Simple prompts | ✅ **Deep intent extraction** |
| **Semantic Vector Search** | ❌ | ❌ | ❌ | ✅ **FAISS-powered** |
| **Emotion-Aware Matching** | ⚠️ User tags only | ❌ | ❌ | ✅ **8-dimensional emotion vectors** |
| **LLM Re-Ranking** | ❌ | ❌ | ❌ | ✅ **RAG with Llama 3.1** |
| **Complex Multi-Condition Queries** | ❌ | ❌ | ❌ | ✅ **Fully supported** |
| **Explainable Recommendations** | ❌ | ❌ | ❌ | ✅ **XAI with reasoning** |
| **Multi-Language Support** | ❌ | ❌ | ❌ | ✅ **10+ languages** |
| **Streaming Provider Filters** | ⚠️ Limited | ❌ | ❌ | ✅ **Full integration** |
| **Cost** | Social only | Paid | Limited free | ✅ **100% Free Tier** |

### Core Differentiators

1. **Emotion-Aware Engine**: Scores movies across 8 emotional dimensions (Joy, Fear, Sadness, Awe, Thrill, Hope, Dark tone, Romance)
2. **Hybrid Vector Embeddings**: Combines semantic, emotional, genre, and cast vectors into a unified representation
3. **LLM Query Rewrite**: Transforms queries into optimized search vectors with theme extraction
4. **Multi-Agent System**: Specialized agents for intent, emotion, filtering, retrieval, and re-ranking
5. **Explainable AI**: Every recommendation includes thematic similarity %, emotional match %, and reasoning

---

## 🏗️ Architecture

FilmFind uses a **multi-layered AI pipeline** with the following components:

```
User Query → NLP Understanding → Semantic Retrieval → Multi-Signal Scoring → LLM Re-Ranking → Explainable Output
```

### High-Level Architecture

![System Architecture](images/System%20Archeitecture.png)

### Key Components

1. **Data Pipeline**
   - TMDB API integration for movie metadata
   - Embedding generation using sentence-transformers
   - Vector database (FAISS) for similarity search
   - PostgreSQL/Supabase for metadata storage

2. **Intelligence Layer**
   - NLP Engine: Query parsing and intent extraction
   - Embedding Service: Semantic vector generation
   - Vector Search: FAISS similarity retrieval
   - Scoring Engine: Multi-signal ranking
   - LLM Re-Ranker: Contextual re-ranking with Groq/Ollama

3. **API & Backend**
   - FastAPI REST API
   - Redis caching (Upstash)
   - Background jobs for data updates
   - Rate limiting and monitoring

4. **Frontend**
   - Next.js 14+ with App Router
   - TailwindCSS + ShadCN UI
   - Real-time search with debouncing
   - Responsive design

5. **Infrastructure**
   - AWS ECS (Docker) for backend
   - Vercel for frontend
   - AWS RDS PostgreSQL
   - AWS S3 + CloudFront
   - Upstash Redis

---

## 📊 System Diagrams

### 1. System Architecture
Complete end-to-end architecture showing all components and data flow.

![System Architecture](images/System%20Archeitecture.png)

### 2. Flow Diagram
High-level flow of data through the system from query to recommendations.

![Flow Diagram](images/Flow%20Diagram.png)

### 3. Detailed Flow Chart
Step-by-step processing pipeline with all validation and filtering stages.

![Flow Chart](images/Flow%20Chart.png)

### 4. Sequence Diagram
Interaction sequence between all system components during a search request.

![Sequence Diagram](images/Sequence-diagram.png)

---

## 🛠️ Tech Stack

### **Backend**
- **Python 3.11+**: Core language
- **FastAPI**: High-performance async API framework
- **SQLAlchemy**: ORM for database operations
- **PostgreSQL**: Primary database (AWS RDS or Supabase)
- **FAISS**: Vector similarity search (Facebook AI)
- **Redis**: Caching layer (Upstash free tier)
- **APScheduler**: Background job scheduling

### **AI/ML**
- **sentence-transformers/all-mpnet-base-v2**: Semantic embeddings (768-dim)
- **Groq API**: LLM for query understanding and re-ranking (free tier: 30 req/min)
- **Ollama**: Local LLM alternative (Llama 3.2, unlimited)
- **spaCy**: NLP for text processing and entity extraction

### **Frontend**
- **Next.js 14+**: React framework with App Router
- **TypeScript**: Type-safe JavaScript
- **TailwindCSS**: Utility-first CSS framework
- **ShadCN UI**: Beautiful accessible components
- **Zustand**: Lightweight state management

### **DevOps & Infrastructure (FREE Tier)**
- **Docker**: Containerization
- **GitHub Actions**: CI/CD pipeline (2,000 min/month free)
- **AWS ECS**: Container orchestration (750 hours/month free for 12 months)
- **Vercel**: Frontend hosting (free forever for hobby projects)
- **AWS RDS**: Database (t3.micro, 750 hours/month free for 12 months)
- **AWS S3**: Object storage (5GB free)
- **AWS CloudFront**: CDN (1TB transfer/month free)
- **Sentry**: Error monitoring (5k events/month free)

### **Data Sources**
- **TMDB API**: Movie metadata, cast, crew, keywords (free tier)
- **IMDb Datasets**: Additional ratings and metadata (free on Kaggle)

---

## 🚀 Getting Started

### Prerequisites

- Python 3.11 or higher
- Node.js 18+ and npm/yarn
- PostgreSQL 14+ (or Supabase account)
- Redis (local or Upstash account)
- TMDB API key (free)
- Groq API key (free tier)

### Installation

#### 1. Clone the Repository

```bash
git clone https://github.com/yourusername/filmfind.git
cd filmfind
```

#### 2. Backend Setup

```bash
cd backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Create .env file
cat > .env << EOF
TMDB_API_KEY=your_tmdb_key
GROQ_API_KEY=your_groq_key
DATABASE_URL=postgresql://user:password@localhost:5432/filmfind
REDIS_URL=redis://localhost:6379
VECTOR_MODEL=sentence-transformers/all-mpnet-base-v2
LLM_PROVIDER=groq
EOF
```

#### 3. Frontend Setup

```bash
cd ../frontend

# Install dependencies
npm install

# Create .env.local file
cat > .env.local << EOF
NEXT_PUBLIC_API_URL=http://localhost:8000
EOF
```

#### 4. Database Setup

```bash
cd ../backend

# Run migrations
alembic upgrade head

# Optional: Seed with sample data
python scripts/seed_data.py
```

#### 5. Data Ingestion

```bash
# Fetch movies from TMDB
python scripts/ingest_tmdb.py --limit 10000

# Generate embeddings
python scripts/generate_embeddings.py

# Build vector index
python scripts/build_index.py
```

#### 6. Run the Application

```bash
# Terminal 1: Start backend
cd backend
uvicorn app.main:app --reload --port 8000

# Terminal 2: Start frontend
cd frontend
npm run dev
```

Open [http://localhost:3000](http://localhost:3000) in your browser.

---

## 📁 Project Structure

```
filmfind/
├── backend/
│   ├── app/
│   │   ├── api/
│   │   │   ├── routes/
│   │   │   │   ├── search.py          # Search endpoints
│   │   │   │   ├── movies.py          # Movie detail endpoints
│   │   │   │   └── filters.py         # Filter endpoints
│   │   │   └── dependencies.py        # Dependency injection
│   │   ├── core/
│   │   │   ├── config.py              # Configuration management
│   │   │   ├── database.py            # Database connection
│   │   │   └── cache.py               # Redis cache wrapper
│   │   ├── models/
│   │   │   ├── movie.py               # Movie ORM models
│   │   │   └── user.py                # User models (optional)
│   │   ├── services/
│   │   │   ├── tmdb_service.py        # TMDB API client
│   │   │   ├── embedding_service.py   # Embedding generation
│   │   │   ├── vector_search.py       # FAISS vector search
│   │   │   ├── query_parser.py        # NLP query parsing
│   │   │   ├── reranker.py            # LLM re-ranking
│   │   │   └── scoring_engine.py      # Multi-signal scoring
│   │   ├── schemas/
│   │   │   ├── search.py              # Search request/response schemas
│   │   │   └── movie.py               # Movie schemas
│   │   └── main.py                    # FastAPI app entry point
│   ├── scripts/
│   │   ├── ingest_tmdb.py             # Data ingestion script
│   │   ├── generate_embeddings.py     # Embedding generation
│   │   └── build_index.py             # Vector index builder
│   ├── tests/
│   │   ├── test_search.py
│   │   └── test_embeddings.py
│   ├── requirements.txt
│   └── Dockerfile
│
├── frontend/
│   ├── app/
│   │   ├── page.tsx                   # Home page
│   │   ├── search/
│   │   │   └── page.tsx               # Search page
│   │   ├── movie/[id]/
│   │   │   └── page.tsx               # Movie detail page
│   │   └── layout.tsx                 # Root layout
│   ├── components/
│   │   ├── SearchBar.tsx              # Search input component
│   │   ├── MovieCard.tsx              # Movie card component
│   │   ├── FilterPanel.tsx            # Filter sidebar
│   │   └── ui/                        # ShadCN UI components
│   ├── lib/
│   │   ├── api.ts                     # API client
│   │   └── utils.ts                   # Utility functions
│   ├── hooks/
│   │   └── useSearch.ts               # Search hook
│   ├── package.json
│   └── next.config.js
│
├── images/                            # Architecture diagrams
│   ├── System Archeitecture.png
│   ├── Flow Diagram.png
│   ├── Flow Chart.png
│   └── Sequence-diagram.png
│
├── docs/
│   ├── architecture.md                # Architecture documentation
│   ├── api.md                         # API documentation
│   └── deployment.md                  # Deployment guide
│
├── .github/
│   └── workflows/
│       └── ci-cd.yml                  # GitHub Actions workflow
│
├── docker-compose.yml                 # Docker compose configuration
├── plan.md                            # Implementation plan
├── Project Overview                   # Technical design doc
└── README.md                          # This file
```

---

## 📚 API Documentation

### Base URL
```
Development: http://localhost:8000
Production: https://api.filmfind.com
```

### Endpoints

#### 1. Search Movies

```http
POST /api/search
Content-Type: application/json

{
  "query": "dark sci-fi movies like Interstellar with less romance",
  "limit": 10,
  "filters": {
    "year_min": 2010,
    "year_max": 2024,
    "language": "en",
    "genres": ["Science Fiction"]
  }
}
```

**Response:**
```json
{
  "results": [
    {
      "id": 157336,
      "title": "Interstellar",
      "overview": "The adventures of a group of explorers...",
      "rating": 8.4,
      "match_score": 0.95,
      "similarity_explanation": "Strong thematic match: space exploration, time dilation...",
      "poster_url": "https://image.tmdb.org/...",
      "genres": ["Science Fiction", "Drama"],
      "release_date": "2014-11-07"
    }
  ],
  "count": 10,
  "query_interpretation": {
    "themes": ["space", "dark", "science fiction"],
    "excluded": ["romance"],
    "reference_movies": ["Interstellar"]
  }
}
```

#### 2. Get Similar Movies

```http
GET /api/similar/{movie_id}?limit=10
```

#### 3. Get Movie Details

```http
GET /api/movie/{movie_id}
```

#### 4. Filter Movies

```http
POST /api/filter
Content-Type: application/json

{
  "genres": ["Thriller", "Mystery"],
  "year_min": 2015,
  "rating_min": 7.0,
  "language": "en",
  "streaming_providers": ["Netflix", "Prime Video"]
}
```

#### 5. Trending Movies

```http
GET /api/trending?limit=20&time_window=week
```

For complete API documentation, see [docs/api.md](docs/api.md) or visit `/docs` (Swagger UI) when running the backend.

---

## 🗓️ Future Enhancements
- [ ] Mobile app (React Native)
- [ ] Episode-level recommendations for TV shows
- [ ] Real-time collaborative filtering
- [ ] Multi-user social recommendations
- [ ] Integration with more streaming services
- [ ] Podcast and documentary support

---

## 🎯 Success Metrics

- ✅ Search response time < 500ms
- ✅ 90%+ relevant results for test queries
- ✅ Frontend Lighthouse score > 90
- ✅ API uptime > 99%
- ✅ 10,000+ movies indexed
- ✅ Support for 10+ languages
- ✅ Zero monthly costs (within free tier limits)
- ✅ Cache hit rate > 70%
- ✅ LLM calls within Groq free tier (30 req/min)

---

## 💡 Usage Examples

### Example 1: Reference-Based Search
```
Query: "Shows like Stranger Things but with more horror elements"
```
**FilmFind understands:**
- Reference: Stranger Things
- Enhancement: More horror/darker tone
- Themes: Supernatural, group of kids, 80s setting
- Recommended: The Twilight Zone, Locke & Key, Dark, Archive 81

### Example 2: Sports Drama Search
```
Query: "Movies about F1 racing with intense competition and personal rivalries"
```
**FilmFind understands:**
- Themes: Formula 1, racing, competition, rivalry
- Tone: Intense, dramatic
- Sport: Motorsport/F1
- Recommended: Rush, Ford v Ferrari, Senna, Grand Prix, Days of Thunder

### Example 3: Fantasy Mystery Search
```
Query: "Mystery and magical adventures like Harry Potter with school settings"
```
**FilmFind understands:**
- Reference: Harry Potter
- Themes: Magic, mystery, coming-of-age
- Setting: School/academy
- Genre: Fantasy + Mystery
- Recommended: The Chronicles of Narnia, Percy Jackson, His Dark Materials, The Magicians, A Discovery of Witches

### Example 4: Sitcom Search
```
Query: "Lighthearted sitcoms like Friends about group of friends navigating life and relationships"
```
**FilmFind understands:**
- Reference: Friends
- Themes: Friendship, relationships, comedy of life
- Tone: Lighthearted, feel-good
- Genre: Sitcom
- Recommended: How I Met Your Mother, New Girl, Brooklyn Nine-Nine, The Big Bang Theory, Modern Family

---

## 🤝 Contributing

We welcome contributions! Here's how you can help:

### Getting Started
1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

### Development Guidelines
- Write clear, commented code
- Follow PEP 8 for Python code
- Use TypeScript for frontend code
- Write tests for new features
- Update documentation as needed

### Areas for Contribution
- 🐛 Bug fixes
- ✨ New features
- 📝 Documentation improvements
- 🎨 UI/UX enhancements
- 🔧 Performance optimizations
- 🧪 Test coverage
- 🌍 Internationalization

---

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## 👨‍💻 Author

**Dheeraj Srirama**

- GitHub: [@dheerajsrirama](https://github.com/dheerajsrirama)
- LinkedIn: [Dheeraj Srirama](https://linkedin.com/in/dheerajsrirama)
- Email: sriramadheeraj@gmail.com

---

## 🙏 Acknowledgments

- [TMDB](https://www.themoviedb.org/) for the comprehensive movie database API
- [Groq](https://groq.com/) for providing free tier LLM API access
- [Sentence Transformers](https://www.sbert.net/) for excellent embedding models
- [FastAPI](https://fastapi.tiangolo.com/) for the amazing Python framework
- [Next.js](https://nextjs.org/) for the powerful React framework
- [ShadCN UI](https://ui.shadcn.com/) for beautiful UI components

---

## 📞 Support

If you have any questions, issues, or suggestions:
- 🐛 Issues: [GitHub Issues](https://github.com/yourusername/filmfind/issues)

---

## ⭐ Show Your Support

If you find FilmFind useful, please consider:
- Giving it a ⭐ on GitHub
- Sharing it with others
- Contributing to the project
- Reporting bugs and suggesting features

---

