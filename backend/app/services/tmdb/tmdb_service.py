"""TMDBService — facade that bundles the client and validator."""
from app.services.tmdb.client import TMDBClient
from app.services.tmdb.validator import TMDBValidator


class TMDBService:
    """Used by ingestion scripts and the TMDB sync job."""

    def __init__(self) -> None:
        self.client = TMDBClient()
        self.validator = TMDBValidator()
