"""
Movie detail API endpoints
To be implemented
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.schemas.movie import MovieResponse

router = APIRouter()


@router.get("/{movie_id}", response_model=MovieResponse)
async def get_movie(
    movie_id: int,
    db: Session = Depends(get_db)
):
    """
    Get movie details by ID
    """
    # To be implemented
    raise HTTPException(status_code=501, detail="Not implemented yet")


@router.get("/trending", response_model=list[MovieResponse])
async def get_trending_movies(
    limit: int = 20,
    db: Session = Depends(get_db)
):
    """
    Get trending movies
    """
    # To be implemented
    raise HTTPException(status_code=501, detail="Not implemented yet")
