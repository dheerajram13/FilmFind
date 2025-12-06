"""
Search API endpoints - Module 3.2
To be implemented
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.search import SearchRequest, SearchResponse, SimilarRequest


router = APIRouter()


@router.post("/", response_model=SearchResponse)
async def search_movies(request: SearchRequest, db: Session = Depends(get_db)):
    """
    Search movies using natural language query
    """
    # To be implemented in Module 3.2
    raise HTTPException(status_code=501, detail="Not implemented yet")


@router.post("/similar", response_model=SearchResponse)
async def find_similar_movies(request: SimilarRequest, db: Session = Depends(get_db)):
    """
    Find similar movies based on a reference movie
    """
    # To be implemented in Module 3.2
    raise HTTPException(status_code=501, detail="Not implemented yet")
