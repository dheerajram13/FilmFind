"""
Backfill streaming provider data for all films in the DB.

Calls TMDB's /movie/{id}/watch/providers and /tv/{id}/watch/providers,
stores the result in media.streaming_providers as:
  {
    "AU": { "flatrate": [...], "rent": [...], "buy": [...] },
    "US": { ... },
    ...
  }

Usage:
  python scripts/backfill_streaming.py [--batch 50] [--region AU] [--all-regions]
"""
import argparse
import sys
import time
from pathlib import Path

# Allow running from repo root or scripts/
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.config import settings
from app.core.database import SessionLocal
from app.models.media import Media
from app.services.TMDB.tmdb_client import TMDBAPIClient

# Regions to fetch — default is just the configured region.
# Pass --all-regions to fetch a broader set.
DEFAULT_REGIONS = [settings.DEFAULT_REGION or "AU"]
ALL_REGIONS = ["AU", "US", "GB", "CA", "NZ", "IN", "DE", "FR", "JP"]


def fetch_providers(client: TMDBAPIClient, tmdb_id: int, media_type: str) -> dict:
    """
    Fetch watch providers from TMDB and return a region-keyed dict.
    e.g. { "AU": { "flatrate": [...], "rent": [...], "buy": [...] } }
    """
    if media_type == "tv":
        endpoint = f"/tv/{tmdb_id}/watch/providers"
    else:
        endpoint = f"/movie/{tmdb_id}/watch/providers"

    data = client._make_request(endpoint)
    if not data or "results" not in data:
        return {}

    results = data["results"]
    # Strip the 'link' key from each region — not needed
    cleaned = {}
    for region, info in results.items():
        entry = {}
        for key in ("flatrate", "rent", "buy", "free", "ads"):
            if key in info:
                entry[key] = [
                    {"provider_id": p.get("provider_id"), "provider_name": p.get("provider_name"), "logo_path": p.get("logo_path")}
                    for p in info[key]
                ]
        if entry:
            cleaned[region] = entry
    return cleaned


def backfill(batch: int, regions: list[str], force: bool):
    db = SessionLocal()
    client = TMDBAPIClient(api_key=settings.TMDB_API_KEY)

    try:
        from sqlalchemy import text as sa_text

        if not force:
            # IDs that already have real (non-null JSON) provider data
            rows = db.execute(
                sa_text("SELECT id FROM media WHERE streaming_providers IS NOT NULL AND streaming_providers::text != 'null'")
            ).fetchall()
            done_ids = [r[0] for r in rows]
            query = db.query(Media)
            if done_ids:
                query = query.filter(~Media.id.in_(done_ids))
        else:
            query = db.query(Media)

        total = query.count()
        print(f"Films to process: {total} (batch size: {batch}, regions: {regions})")

        if total == 0:
            print("Nothing to do. Use --force to re-fetch all films.")
            return

        processed = 0
        updated = 0
        errors = 0

        offset = 0
        while offset < total:
            films = query.order_by(Media.id).offset(offset).limit(batch).all()
            if not films:
                break

            for film in films:
                try:
                    providers = fetch_providers(client, film.tmdb_id, film.media_type)

                    # Filter to requested regions only (unless empty — store all)
                    if regions:
                        filtered = {r: providers[r] for r in regions if r in providers}
                    else:
                        filtered = providers

                    film.streaming_providers = filtered if filtered else None
                    processed += 1
                    if filtered:
                        updated += 1
                        provider_names = set()
                        for region_data in filtered.values():
                            for entry in region_data.get("flatrate", []):
                                provider_names.add(entry["provider_name"])
                        print(f"  [{processed}/{total}] {film.title} ({film.tmdb_id}) — {list(provider_names) or 'no flatrate'}")
                    else:
                        print(f"  [{processed}/{total}] {film.title} ({film.tmdb_id}) — no providers found")

                except Exception as e:
                    errors += 1
                    print(f"  ERROR {film.title} ({film.tmdb_id}): {e}")

            db.commit()
            offset += batch
            # Small pause between batches to be nice to TMDB rate limits
            if offset < total:
                time.sleep(0.5)

        print(f"\nDone. Processed: {processed}, With providers: {updated}, Errors: {errors}")

    finally:
        db.close()
        client.close()


def main():
    parser = argparse.ArgumentParser(description="Backfill TMDB streaming provider data")
    parser.add_argument("--batch", type=int, default=50, help="Films per DB batch (default: 50)")
    parser.add_argument("--region", type=str, default=None, help="Single region code, e.g. AU (default: from config)")
    parser.add_argument("--all-regions", action="store_true", help="Fetch all major regions")
    parser.add_argument("--force", action="store_true", help="Re-fetch even if data already exists")
    args = parser.parse_args()

    if not settings.TMDB_API_KEY:
        print("ERROR: TMDB_API_KEY is not set in .env")
        sys.exit(1)

    if args.all_regions:
        regions = ALL_REGIONS
    elif args.region:
        regions = [args.region.upper()]
    else:
        regions = DEFAULT_REGIONS

    backfill(batch=args.batch, regions=regions, force=args.force)


if __name__ == "__main__":
    main()
