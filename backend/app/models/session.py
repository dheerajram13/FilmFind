"""
Session models for search and 60-second mode analytics.
"""
import uuid
from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB

from app.core.database import Base


def _new_uuid() -> str:
    return str(uuid.uuid4())


class SearchSession(Base):
    """Records every search query for analytics."""

    __tablename__ = "search_sessions"

    id = Column(String(36), primary_key=True, default=_new_uuid)
    session_token = Column(String(255), nullable=True, index=True)
    query_text = Column(Text, nullable=True)
    query_parsed = Column(JSONB, nullable=True)
    results = Column(JSONB, nullable=True)
    result_clicked_id = Column(Integer, nullable=True)
    stream_clicked = Column(Boolean, default=False)
    response_ms = Column(Integer, nullable=True)
    confidence_score = Column(Float, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)


class SixtySession(Base):
    """Records every 60-second mode pick for analytics."""

    __tablename__ = "sixty_sessions"

    id = Column(String(36), primary_key=True, default=_new_uuid)
    session_token = Column(String(255), nullable=True, index=True)
    mood = Column(String(50), nullable=True)
    context = Column(String(50), nullable=True)
    craving = Column(String(50), nullable=True)
    film_picked_id = Column(Integer, ForeignKey("media.id", ondelete="SET NULL"), nullable=True)
    match_score = Column(Integer, nullable=True)
    seconds_taken = Column(Integer, nullable=True)
    watch_clicked = Column(Boolean, default=False)
    share_clicked = Column(Boolean, default=False)
    retry_clicked = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
