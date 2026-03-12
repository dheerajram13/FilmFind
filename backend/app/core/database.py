"""
Database connection and session management
"""
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import settings


def _engine_kwargs() -> dict:
    """
    Build SQLAlchemy engine kwargs based on the target database.

    Supabase free tier has a 60-connection limit — keep pool small.
    pool_recycle=300 handles Supabase's 5-minute idle connection timeout.
    Upgrading to Supabase Pro raises the limit to 200+; bump pool_size then.
    """
    is_supabase = "supabase.co" in settings.DATABASE_URL or "pooler.supabase.com" in settings.DATABASE_URL
    if is_supabase:
        return {
            "echo": settings.DB_ECHO,
            "pool_pre_ping": True,
            "pool_size": 5,
            "max_overflow": 5,
            "pool_recycle": 300,
            "connect_args": {
                "connect_timeout": 10,
                "application_name": "filmfind-backend",
            },
        }
    return {
        "echo": settings.DB_ECHO,
        "pool_pre_ping": True,
        "pool_size": 10,
        "max_overflow": 20,
    }


# Create database engine
engine = create_engine(settings.DATABASE_URL, **_engine_kwargs())

# Session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class for models
Base = declarative_base()


def get_db() -> Session:
    """
    Dependency to get database session
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
