"""
One-time script: upload all TMDB poster/backdrop images to Supabase Storage.

Strategy (dual-track, safe to re-run):
- Reads poster_path / backdrop_path from the media table
- Downloads each image from TMDB CDN
- Uploads to Supabase Storage (posters/{tmdb_id}.jpg, backdrops/{tmdb_id}.jpg)
- Writes the resulting public URL into poster_supabase_url / backdrop_supabase_url
- Never modifies the original poster_path / backdrop_path — TMDB fallback always works

Usage:
    cd backend/
    DATABASE_URL=<supabase_db_url> \\
    SUPABASE_URL=https://[ref].supabase.co \\
    SUPABASE_SERVICE_ROLE_KEY=<key> \\
    python scripts/migrate_images_to_supabase.py

Flags:
    --dry-run       Print what would be uploaded, no actual changes
    --limit N       Only process N rows (useful for testing)
    --overwrite     Re-upload even if Supabase URL already set
    --tmdb-id N     Process a single media item by tmdb_id
"""
import argparse
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from loguru import logger
from sqlalchemy import text
from tqdm import tqdm

from app.core.database import SessionLocal
from app.core.storage import SupabaseStorageService


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Migrate TMDB images to Supabase Storage")
    p.add_argument("--dry-run", action="store_true", help="Print actions without uploading")
    p.add_argument("--limit", type=int, default=None, help="Max rows to process")
    p.add_argument("--overwrite", action="store_true", help="Re-upload even if URL already exists")
    p.add_argument("--tmdb-id", type=int, default=None, help="Process a single tmdb_id only")
    return p.parse_args()


def main() -> None:
    args = parse_args()
    storage = SupabaseStorageService()
    db = SessionLocal()

    # Build WHERE clause
    conditions = []
    if not args.overwrite:
        conditions.append("(poster_supabase_url IS NULL OR backdrop_supabase_url IS NULL)")
    if args.tmdb_id:
        conditions.append(f"tmdb_id = {args.tmdb_id}")

    where = ("WHERE " + " AND ".join(conditions)) if conditions else ""
    limit = f"LIMIT {args.limit}" if args.limit else ""

    rows = db.execute(text(f"""
        SELECT id, tmdb_id, poster_path, backdrop_path,
               poster_supabase_url, backdrop_supabase_url
        FROM media
        {where}
        ORDER BY id
        {limit}
    """)).fetchall()

    logger.info(f"Found {len(rows)} rows to process. dry_run={args.dry_run}")

    stats = {"posters_ok": 0, "posters_fail": 0, "backdrops_ok": 0, "backdrops_fail": 0, "skipped": 0}

    for row in tqdm(rows, desc="Uploading images"):
        media_id, tmdb_id, poster_path, backdrop_path, existing_poster, existing_backdrop = row

        poster_url: str | None = None
        backdrop_url: str | None = None

        # — Poster —
        if poster_path:
            if not args.overwrite and existing_poster:
                stats["skipped"] += 1
            elif args.dry_run:
                logger.info(f"[DRY RUN] Would upload poster for tmdb_id={tmdb_id}")
            else:
                poster_url = storage.upload_poster(tmdb_id, poster_path)
                stats["posters_ok" if poster_url else "posters_fail"] += 1
                time.sleep(0.15)  # TMDB rate limit headroom

        # — Backdrop —
        if backdrop_path:
            if not args.overwrite and existing_backdrop:
                stats["skipped"] += 1
            elif args.dry_run:
                logger.info(f"[DRY RUN] Would upload backdrop for tmdb_id={tmdb_id}")
            else:
                backdrop_url = storage.upload_backdrop(tmdb_id, backdrop_path)
                stats["backdrops_ok" if backdrop_url else "backdrops_fail"] += 1
                time.sleep(0.15)

        # — Persist URLs to DB —
        if not args.dry_run and (poster_url or backdrop_url):
            parts, params = [], {"id": media_id}
            if poster_url:
                parts.append("poster_supabase_url = :poster_url")
                params["poster_url"] = poster_url
            if backdrop_url:
                parts.append("backdrop_supabase_url = :backdrop_url")
                params["backdrop_url"] = backdrop_url
            db.execute(text(f"UPDATE media SET {', '.join(parts)} WHERE id = :id"), params)
            db.commit()

    db.close()

    logger.info(
        "\n--- Migration Complete ---\n"
        f"  Posters uploaded:   {stats['posters_ok']}\n"
        f"  Posters failed:     {stats['posters_fail']}\n"
        f"  Backdrops uploaded: {stats['backdrops_ok']}\n"
        f"  Backdrops failed:   {stats['backdrops_fail']}\n"
        f"  Skipped (exists):   {stats['skipped']}"
    )


if __name__ == "__main__":
    main()
