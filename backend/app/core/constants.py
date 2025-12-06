"""
Application Constants
Centralized location for all constants, magic numbers, and configuration values
"""

# ============================================================================
# TMDB API Constants
# ============================================================================

TMDB_BASE_URL = "https://api.themoviedb.org/3"
TMDB_IMAGE_BASE_URL = "https://image.tmdb.org/t/p"
TMDB_DEFAULT_RATE_LIMIT = 40  # requests per 10 seconds
TMDB_RATE_WINDOW = 10  # seconds

# TMDB Image Sizes
TMDB_IMAGE_SIZES = {
    "poster": ["w92", "w154", "w185", "w342", "w500", "w780", "original"],
    "backdrop": ["w300", "w780", "w1280", "original"],
    "profile": ["w45", "w185", "h632", "original"],
    "logo": ["w45", "w92", "w154", "w185", "w300", "w500", "original"],
}

# TMDB Endpoints
TMDB_ENDPOINTS = {
    "movie_detail": "/movie/{movie_id}",
    "movie_popular": "/movie/popular",
    "movie_top_rated": "/movie/top_rated",
    "movie_now_playing": "/movie/now_playing",
    "movie_upcoming": "/movie/upcoming",
    "movie_keywords": "/movie/{movie_id}/keywords",
    "movie_credits": "/movie/{movie_id}/credits",
    "movie_similar": "/movie/{movie_id}/similar",
    "movie_recommendations": "/movie/{movie_id}/recommendations",
    "discover_movie": "/discover/movie",
    "discover_tv": "/discover/tv",
    "genre_movie_list": "/genre/movie/list",
    "genre_tv_list": "/genre/tv/list",
    "search_movie": "/search/movie",
    "search_tv": "/search/tv",
    "trending": "/trending/{media_type}/{time_window}",
}

# ============================================================================
# LLM Provider Constants
# ============================================================================

# Groq API
GROQ_BASE_URL = "https://api.groq.com/openai/v1"
GROQ_DEFAULT_MODEL = "llama-3.1-70b-versatile"
GROQ_DEFAULT_MAX_TOKENS = 1024
GROQ_DEFAULT_TEMPERATURE = 0.7
GROQ_FREE_TIER_RATE_LIMIT = 30  # requests per minute

# Groq Available Models
GROQ_MODELS = {
    "llama-3.1-70b": "llama-3.1-70b-versatile",
    "llama-3.1-8b": "llama-3.1-8b-instant",
    "llama-3.2-1b": "llama-3.2-1b-preview",
    "llama-3.2-3b": "llama-3.2-3b-preview",
    "mixtral-8x7b": "mixtral-8x7b-32768",
}

# Ollama API
OLLAMA_DEFAULT_BASE_URL = "http://localhost:11434"
OLLAMA_DEFAULT_MODEL = "llama3.2"

# Ollama Available Models
OLLAMA_MODELS = {
    "llama3.2": "llama3.2",
    "llama3.1": "llama3.1",
    "mistral": "mistral",
    "mixtral": "mixtral",
    "codellama": "codellama",
    "phi": "phi",
}

# ============================================================================
# Embedding Model Constants
# ============================================================================

# Sentence Transformers
EMBEDDING_MODEL_DEFAULT = "sentence-transformers/all-mpnet-base-v2"
EMBEDDING_DIMENSION_DEFAULT = 768

EMBEDDING_MODELS = {
    "all-mpnet-base-v2": {
        "name": "sentence-transformers/all-mpnet-base-v2",
        "dimension": 768,
        "description": "Best quality, slower"
    },
    "all-MiniLM-L6-v2": {
        "name": "sentence-transformers/all-MiniLM-L6-v2",
        "dimension": 384,
        "description": "Fast and good quality"
    },
    "paraphrase-multilingual": {
        "name": "sentence-transformers/paraphrase-multilingual-mpnet-base-v2",
        "dimension": 768,
        "description": "Multilingual support"
    },
}

# ============================================================================
# Vector Search Constants
# ============================================================================

FAISS_INDEX_TYPES = {
    "flat": "Flat (exact search)",
    "ivf": "IVF (inverted file index)",
    "hnsw": "HNSW (hierarchical navigable small world)",
}

FAISS_DEFAULT_INDEX_TYPE = "flat"
FAISS_DEFAULT_NLIST = 100  # Number of clusters for IVF
FAISS_DEFAULT_NPROBE = 10  # Number of clusters to search

# Vector search defaults
VECTOR_SEARCH_TOP_K = 50
VECTOR_RERANK_TOP_K = 10
VECTOR_MIN_SIMILARITY = 0.5

# ============================================================================
# Scoring Weights Constants
# ============================================================================

# Multi-signal scoring weights
SCORING_WEIGHTS = {
    "semantic": 0.5,
    "genre": 0.2,
    "popularity": 0.1,
    "rating": 0.1,
    "recency": 0.1,
}

# Emotional scoring dimensions
EMOTION_DIMENSIONS = [
    "joy",
    "fear",
    "sadness",
    "awe",
    "thrill",
    "hopefulness",
    "dark_tone",
    "romance_tone",
]

# ============================================================================
# Cache Constants
# ============================================================================

# Cache TTL (seconds)
CACHE_TTL = {
    "search_results": 3600,      # 1 hour
    "movie_details": 86400,      # 24 hours
    "embeddings": -1,            # Permanent
    "llm_rerank": 21600,         # 6 hours
    "trending": 1800,            # 30 minutes
    "genres": 604800,            # 7 days
}

# Cache key prefixes
CACHE_KEYS = {
    "search": "search:",
    "movie": "movie:",
    "embedding": "embedding:",
    "rerank": "rerank:",
    "trending": "trending:",
    "genre": "genre:",
}

# ============================================================================
# HTTP Client Constants
# ============================================================================

HTTP_TIMEOUT_DEFAULT = 30  # seconds
HTTP_MAX_RETRIES = 3
HTTP_RETRY_DELAY = 1.0  # seconds
HTTP_RETRY_BACKOFF = 2.0  # multiplier

# ============================================================================
# Database Constants
# ============================================================================

# Pagination
DB_PAGE_SIZE_DEFAULT = 20
DB_PAGE_SIZE_MAX = 100

# Query limits
DB_BULK_INSERT_BATCH_SIZE = 1000
DB_MAX_QUERY_RESULTS = 10000

# ============================================================================
# Validation Constants
# ============================================================================

# Movie validation
MOVIE_TITLE_MIN_LENGTH = 1
MOVIE_TITLE_MAX_LENGTH = 500
MOVIE_OVERVIEW_MAX_LENGTH = 5000

# Search validation
SEARCH_QUERY_MIN_LENGTH = 2
SEARCH_QUERY_MAX_LENGTH = 500
SEARCH_RESULTS_MIN = 1
SEARCH_RESULTS_MAX = 50

# ============================================================================
# File Paths
# ============================================================================

DATA_DIR = "data"
DATA_RAW_DIR = f"{DATA_DIR}/raw"
DATA_PROCESSED_DIR = f"{DATA_DIR}/processed"
DATA_EMBEDDINGS_DIR = f"{DATA_DIR}/embeddings"

LOG_DIR = "logs"
LOG_FILE_DEFAULT = f"{LOG_DIR}/filmfind.log"

# ============================================================================
# Genre Constants
# ============================================================================

# TMDB Genre IDs (for reference)
TMDB_GENRE_IDS = {
    28: "Action",
    12: "Adventure",
    16: "Animation",
    35: "Comedy",
    80: "Crime",
    99: "Documentary",
    18: "Drama",
    10751: "Family",
    14: "Fantasy",
    36: "History",
    27: "Horror",
    10402: "Music",
    9648: "Mystery",
    10749: "Romance",
    878: "Science Fiction",
    10770: "TV Movie",
    53: "Thriller",
    10752: "War",
    37: "Western",
}

# ============================================================================
# Language Constants
# ============================================================================

SUPPORTED_LANGUAGES = {
    "en": "English",
    "es": "Spanish",
    "fr": "French",
    "de": "German",
    "it": "Italian",
    "ja": "Japanese",
    "ko": "Korean",
    "zh": "Chinese",
    "hi": "Hindi",
    "te": "Telugu",
    "ta": "Tamil",
    "pt": "Portuguese",
    "ru": "Russian",
    "ar": "Arabic",
}

# ============================================================================
# Status Codes
# ============================================================================

HTTP_STATUS = {
    "OK": 200,
    "CREATED": 201,
    "NO_CONTENT": 204,
    "BAD_REQUEST": 400,
    "UNAUTHORIZED": 401,
    "FORBIDDEN": 403,
    "NOT_FOUND": 404,
    "TOO_MANY_REQUESTS": 429,
    "INTERNAL_SERVER_ERROR": 500,
    "SERVICE_UNAVAILABLE": 503,
}

# ============================================================================
# Date/Time Constants
# ============================================================================

DATE_FORMAT_ISO = "%Y-%m-%d"
DATE_FORMAT_DISPLAY = "%B %d, %Y"
DATETIME_FORMAT_ISO = "%Y-%m-%dT%H:%M:%S"
DATETIME_FORMAT_LOG = "%Y-%m-%d %H:%M:%S"

# ============================================================================
# Regular Expressions
# ============================================================================

# Patterns for query parsing
PATTERN_YEAR = r"\b(19|20)\d{2}\b"
PATTERN_REFERENCE_MOVIE = r"(?:like|similar to)\s+([^,]+)"
PATTERN_EXCLUDE = r"(?:no|without|less)\s+(\w+)"

# ============================================================================
# Error Messages
# ============================================================================

ERROR_MESSAGES = {
    "api_key_missing": "API key is required",
    "invalid_query": "Search query is too short or invalid",
    "movie_not_found": "Movie not found",
    "rate_limit_exceeded": "Rate limit exceeded. Please try again later.",
    "database_error": "Database error occurred",
    "external_api_error": "External API error",
    "validation_error": "Validation error",
}

# ============================================================================
# Success Messages
# ============================================================================

SUCCESS_MESSAGES = {
    "search_completed": "Search completed successfully",
    "movie_fetched": "Movie details fetched successfully",
    "embedding_generated": "Embedding generated successfully",
    "cache_hit": "Result found in cache",
}
