"""
Configuration management for FilmFind backend
"""
from typing import ClassVar

from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings"""

    # Application
    APP_NAME: str = "FilmFind"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    API_PREFIX: str = "/api"

    # Server
    HOST: str = "0.0.0.0"
    PORT: int = 8000

    # Database
    DATABASE_URL: str = Field(
        default="postgresql://postgres:postgres@localhost:5432/filmfind",
        description="PostgreSQL database URL",
    )
    DB_ECHO: bool = False  # SQLAlchemy echo SQL queries

    # Redis Cache
    REDIS_HOST: str = Field(default="localhost", description="Redis host")
    REDIS_PORT: int = Field(default=6379, description="Redis port")
    REDIS_DB: int = Field(default=0, description="Redis database number")
    REDIS_PASSWORD: str | None = Field(default=None, description="Redis password (optional)")
    CACHE_ENABLED: bool = Field(default=True, description="Enable/disable caching")
    CACHE_TTL: int = 3600  # 1 hour default TTL

    # TMDB API
    TMDB_API_KEY: str = Field(default="", description="TMDB API key for fetching movie data")
    TMDB_BASE_URL: str = "https://api.themoviedb.org/3"
    TMDB_IMAGE_BASE_URL: str = "https://image.tmdb.org/t/p"
    TMDB_RATE_LIMIT: int = 40  # requests per 10 seconds

    # AI/ML Models
    VECTOR_MODEL: str = Field(
        default="sentence-transformers/all-mpnet-base-v2",
        description="Sentence transformer model for embeddings",
    )
    EMBEDDING_DIMENSION: int = 768  # all-mpnet-base-v2 dimension

    # Embedding Generation Settings
    MAX_KEYWORDS: int = 10  # Maximum keywords to include in embedding text
    MAX_CAST_MEMBERS: int = 5  # Maximum cast members to include in embedding text
    MIN_TEXT_LENGTH: int = 10  # Minimum text length for valid embedding
    DEFAULT_EMBEDDING_BATCH_SIZE: int = 32  # Batch size for embedding generation
    DEFAULT_DB_BATCH_SIZE: int = 100  # Batch size for database operations

    # LLM Provider
    LLM_PROVIDER: str = Field(default="groq", description="LLM provider: 'groq' or 'ollama'")

    # Groq API (Free Tier)
    GROQ_API_KEY: str = Field(default="", description="Groq API key for LLM inference")
    GROQ_MODEL: str = "llama-3.1-70b-versatile"
    GROQ_MAX_TOKENS: int = 1024
    GROQ_TEMPERATURE: float = 0.7

    # Ollama (Local LLM)
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OLLAMA_MODEL: str = "llama3.2"

    # Vector Database
    FAISS_INDEX_PATH: str = "data/embeddings/faiss_index.bin"
    FAISS_METADATA_PATH: str = "data/embeddings/metadata.pkl"

    # Search Settings
    SEARCH_TOP_K: int = 50  # Initial retrieval count
    RERANK_TOP_K: int = 10  # Final results after re-ranking
    MIN_SIMILARITY_SCORE: float = 0.5

    # Multi-Signal Scoring Weights
    WEIGHT_SEMANTIC: float = 0.5
    WEIGHT_GENRE: float = 0.2
    WEIGHT_POPULARITY: float = 0.1
    WEIGHT_RATING: float = 0.1
    WEIGHT_RECENCY: float = 0.1

    # CORS
    CORS_ORIGINS: ClassVar[list] = [
        "http://localhost:3000",
        "http://localhost:8000",
        "https://filmfind.com",
    ]

    # Security
    SECRET_KEY: str = Field(
        default="your-secret-key-change-in-production",
        description="Secret key for JWT token generation",
    )
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    # Rate Limiting
    RATE_LIMIT_PER_MINUTE: int = 60

    # Background Jobs
    ENABLE_BACKGROUND_JOBS: bool = False
    DATA_UPDATE_INTERVAL_HOURS: int = 24

    # Logging
    LOG_LEVEL: str = "INFO"
    LOG_FILE: str = "logs/filmfind.log"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True


# Global settings instance
settings = Settings()
