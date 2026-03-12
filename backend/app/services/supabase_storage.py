"""
Supabase Storage service for uploading and serving media images.

Images are downloaded from TMDB CDN and uploaded to the Supabase Storage
bucket `media-images` under the following naming convention:
  posters/{tmdb_id}.jpg
  backdrops/{tmdb_id}.jpg

The bucket is public — CDN URLs are deterministic and don't require signed URLs.
This service uses the SERVICE_ROLE key and is backend-only; never call from frontend.
"""
import logging
from typing import Optional

import httpx
from supabase import Client, create_client

from app.core.config import settings

logger = logging.getLogger(__name__)

TMDB_IMAGE_BASE = "https://image.tmdb.org/t/p"


def get_supabase_client() -> Client:
    """Return a Supabase client authenticated as service role (full access)."""
    return create_client(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_ROLE_KEY)


class SupabaseStorageService:
    """Upload TMDB poster/backdrop images to Supabase Storage."""

    def __init__(self) -> None:
        client = get_supabase_client()
        self.storage = client.storage.from_(settings.SUPABASE_STORAGE_BUCKET)

    def _public_url(self, storage_path: str) -> str:
        return (
            f"{settings.SUPABASE_URL}/storage/v1/object/public/"
            f"{settings.SUPABASE_STORAGE_BUCKET}/{storage_path}"
        )

    def _download(self, url: str) -> Optional[bytes]:
        try:
            r = httpx.get(url, timeout=15.0, follow_redirects=True)
            if r.status_code == 200:
                return r.content
            logger.warning("TMDB download failed %s — HTTP %s", url, r.status_code)
            return None
        except Exception as exc:
            logger.error("TMDB download error %s: %s", url, exc)
            return None

    def upload_poster(self, tmdb_id: int, poster_path: str) -> Optional[str]:
        """Download poster from TMDB (w500) and upload to Supabase. Returns public URL or None."""
        data = self._download(f"{TMDB_IMAGE_BASE}/w500{poster_path}")
        if not data:
            return None
        path = f"posters/{tmdb_id}.jpg"
        try:
            self.storage.upload(path, data, {"content-type": "image/jpeg", "upsert": "true"})
            return self._public_url(path)
        except Exception as exc:
            logger.error("Upload poster tmdb_id=%s failed: %s", tmdb_id, exc)
            return None

    def upload_backdrop(self, tmdb_id: int, backdrop_path: str) -> Optional[str]:
        """Download backdrop from TMDB (w1280) and upload to Supabase. Returns public URL or None."""
        data = self._download(f"{TMDB_IMAGE_BASE}/w1280{backdrop_path}")
        if not data:
            return None
        path = f"backdrops/{tmdb_id}.jpg"
        try:
            self.storage.upload(path, data, {"content-type": "image/jpeg", "upsert": "true"})
            return self._public_url(path)
        except Exception as exc:
            logger.error("Upload backdrop tmdb_id=%s failed: %s", tmdb_id, exc)
            return None
