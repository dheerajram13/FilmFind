#!/usr/bin/env python
"""
Unified media ingestion script — idempotent, with Supabase image upload.

Features:
  - Upserts media rows (safe to re-run; updates mutable fields on conflict)
  - Bulk genre/keyword/cast inserts with ON CONFLICT DO NOTHING
  - Uploads poster + backdrop to Supabase Storage immediately after DB insert
  - Respects TMDB rate limit (~40 req / 10 s)
  - Sources: popular + top-rated (movies & TV), deduplicated in-memory

Usage:
    python scripts/ingest_media.py --movies 20 --tv 10
    python scripts/ingest_media.py --movies 5 --dry-run
"""
import argparse
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from loguru import logger
from sqlalchemy import text
from tqdm import tqdm

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.database import SessionLocal
from app.services.tmdb.tmdb_service import TMDBService
from app.core.storage import SupabaseStorageService

# TMDB rate limit: 40 req / 10 s → ~0.25 s/req safe floor
RATE_DELAY = 0.3


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _j(val) -> Optional[str]:
    """Serialize dicts/lists to JSON string for JSONB columns via psycopg2."""
    if val is None:
        return None
    if isinstance(val, (dict, list)):
        return json.dumps(val)
    return val


def _upsert_genres(db, genre_names: list[str]) -> dict[str, int]:
    """Insert genres, return {name: id} mapping."""
    if not genre_names:
        return {}
    for name in genre_names:
        db.execute(
            text("INSERT INTO genres (name, created_at, updated_at) VALUES (:n, NOW(), NOW()) ON CONFLICT (name) DO NOTHING"),
            {"n": name},
        )
    rows = db.execute(
        text("SELECT name, id FROM genres WHERE name = ANY(:names)"),
        {"names": genre_names},
    ).fetchall()
    return {r.name: r.id for r in rows}


def _upsert_keywords(db, kw_names: list[str]) -> dict[str, int]:
    """Insert keywords, return {name: id} mapping."""
    if not kw_names:
        return {}
    for name in kw_names:
        db.execute(
            text("INSERT INTO keywords (name, created_at, updated_at) VALUES (:n, NOW(), NOW()) ON CONFLICT (name) DO NOTHING"),
            {"n": name},
        )
    rows = db.execute(
        text("SELECT name, id FROM keywords WHERE name = ANY(:names)"),
        {"names": kw_names},
    ).fetchall()
    return {r.name: r.id for r in rows}


def _upsert_cast(db, cast_list: list[dict]) -> dict[int, int]:
    """Insert cast members, return {tmdb_id: id} mapping."""
    if not cast_list:
        return {}
    tmdb_ids = [c.get("tmdb_id") or c.get("id") for c in cast_list if c.get("tmdb_id") or c.get("id")]
    if not tmdb_ids:
        return {}

    for c in cast_list:
        tid = c.get("tmdb_id") or c.get("id")
        if not tid:
            continue
        db.execute(
            text("""
                INSERT INTO "cast" (tmdb_id, name, profile_path, popularity, created_at, updated_at)
                VALUES (:tid, :name, :profile_path, :popularity, NOW(), NOW())
                ON CONFLICT (tmdb_id) DO NOTHING
            """),
            {
                "tid": tid,
                "name": c.get("name", ""),
                "profile_path": c.get("profile_path"),
                "popularity": c.get("popularity"),
            },
        )

    rows = db.execute(
        text('SELECT tmdb_id, id FROM "cast" WHERE tmdb_id = ANY(:ids)'),
        {"ids": tmdb_ids},
    ).fetchall()
    return {r.tmdb_id: r.id for r in rows}


def _link_genres(db, media_id: int, genre_map: dict[str, int], genre_names: list[str]):
    for name in genre_names:
        gid = genre_map.get(name)
        if gid:
            db.execute(
                text("""
                    INSERT INTO media_genres (media_id, genre_id, created_at)
                    VALUES (:mid, :gid, NOW())
                    ON CONFLICT DO NOTHING
                """),
                {"mid": media_id, "gid": gid},
            )


def _link_keywords(db, media_id: int, kw_map: dict[str, int], kw_names: list[str]):
    for name in kw_names:
        kid = kw_map.get(name)
        if kid:
            db.execute(
                text("""
                    INSERT INTO media_keywords (media_id, keyword_id, created_at)
                    VALUES (:mid, :kid, NOW())
                    ON CONFLICT DO NOTHING
                """),
                {"mid": media_id, "kid": kid},
            )


def _link_cast(db, media_id: int, cast_id_map: dict[int, int], cast_list: list[dict]):
    for order, c in enumerate(cast_list):
        tid = c.get("tmdb_id") or c.get("id")
        cid = cast_id_map.get(tid)
        if cid:
            db.execute(
                text("""
                    INSERT INTO media_cast (media_id, cast_id, character_name, order_position, created_at)
                    VALUES (:mid, :cid, :char, :order, NOW())
                    ON CONFLICT DO NOTHING
                """),
                {"mid": media_id, "cid": cid, "char": c.get("character"), "order": order},
            )


def _upload_images(storage: Optional[SupabaseStorageService], db, media_id: int, tmdb_id: int,
                   poster_path: Optional[str], backdrop_path: Optional[str]):
    """Upload images to Supabase and upsert rows into media_asset."""
    if not storage:
        return
    if poster_path:
        url = storage.upload_poster(tmdb_id, poster_path)
        if url:
            # Supabase poster is now primary; demote any existing TMDB poster
            db.execute(text("""
                UPDATE media_asset SET is_primary = FALSE
                WHERE media_id = :mid AND asset_type = 'poster'
            """), {"mid": media_id})
            db.execute(text("""
                INSERT INTO media_asset (media_id, asset_type, source, url, is_primary, display_order, created_at)
                VALUES (:mid, 'poster', 'supabase', :url, TRUE, 0, NOW())
                ON CONFLICT DO NOTHING
            """), {"mid": media_id, "url": url})
    if backdrop_path:
        url = storage.upload_backdrop(tmdb_id, backdrop_path)
        if url:
            db.execute(text("""
                UPDATE media_asset SET is_primary = FALSE
                WHERE media_id = :mid AND asset_type = 'backdrop'
            """), {"mid": media_id})
            db.execute(text("""
                INSERT INTO media_asset (media_id, asset_type, source, url, is_primary, display_order, created_at)
                VALUES (:mid, 'backdrop', 'supabase', :url, TRUE, 0, NOW())
                ON CONFLICT DO NOTHING
            """), {"mid": media_id, "url": url})


# ---------------------------------------------------------------------------
# Movie ingestion
# ---------------------------------------------------------------------------

def ingest_movies(max_pages: int, dry_run: bool = False):
    logger.info(f"Starting movie ingestion — {max_pages} pages (popular + top-rated)")

    tmdb = TMDBService()
    db = SessionLocal()
    storage = None if dry_run else SupabaseStorageService()

    # Collect tmdb_ids from both sources, deduplicated
    seen_ids: set[int] = set()
    items: list[dict] = []

    for source, fetch_fn in [
        ("popular", tmdb.client.get_popular_movies),
        ("top_rated", tmdb.client.get_top_rated_movies),
    ]:
        for page in range(1, max_pages + 1):
            resp = fetch_fn(page=page)
            if not resp or "results" not in resp:
                break
            for item in resp["results"]:
                if item["id"] not in seen_ids:
                    seen_ids.add(item["id"])
                    items.append(item)
            time.sleep(RATE_DELAY)

    logger.info(f"Fetched {len(items)} unique movie IDs — fetching full details")

    saved = skipped = failed = 0

    for item in tqdm(items, desc="Movies"):
        try:
            full = tmdb.client.get_movie(item["id"])
            time.sleep(RATE_DELAY)
            if not full or not tmdb.validator.validate_movie(full):
                skipped += 1
                continue

            cleaned = tmdb.validator.clean_movie_data(full)
            tid = cleaned["tmdb_id"]

            genre_names = cleaned.get("genres", [])
            kw_names = [k["name"] for k in cleaned.get("keywords", []) if k.get("name")]
            cast_list = cleaned.get("cast", [])

            genre_map = _upsert_genres(db, genre_names)
            kw_map = _upsert_keywords(db, kw_names)
            cast_id_map = _upsert_cast(db, cast_list)

            if dry_run:
                logger.info(f"[DRY RUN] Would upsert movie: {cleaned['title']} (tmdb_id={tid})")
                skipped += 1
                continue

            # Check if movie already exists
            existing = db.execute(
                text("SELECT id, media_id FROM movies WHERE tmdb_id = :tid"),
                {"tid": tid},
            ).fetchone()

            if existing:
                media_id = existing.media_id
                inserted = False
                db.execute(text("""
                    UPDATE movies SET
                        title = :title, original_title = :original_title,
                        overview = :overview, tagline = :tagline,
                        release_date = :release_date, status = :status,
                        adult = :adult, popularity = :popularity,
                        vote_average = :vote_average, vote_count = :vote_count,
                        original_language = :original_language,
                        imdb_id = :imdb_id,
                        belongs_to_collection = :belongs_to_collection,
                        production_countries = :production_countries,
                        spoken_languages = :spoken_languages,
                        origin_country = :origin_country,
                        production_companies = :production_companies,
                        streaming_providers = :streaming_providers,
                        runtime = :runtime, budget = :budget, revenue = :revenue,
                        updated_at = NOW()
                    WHERE tmdb_id = :tmdb_id
                """), {
                    "tmdb_id": tid,
                    "title": cleaned["title"],
                    "original_title": cleaned.get("original_title"),
                    "overview": cleaned.get("overview"),
                    "tagline": cleaned.get("tagline"),
                    "release_date": cleaned.get("release_date"),
                    "status": cleaned.get("status"),
                    "adult": cleaned.get("adult", False),
                    "popularity": cleaned.get("popularity"),
                    "vote_average": cleaned.get("vote_average"),
                    "vote_count": cleaned.get("vote_count"),
                    "original_language": cleaned.get("original_language"),
                    "imdb_id": cleaned.get("imdb_id"),
                    "belongs_to_collection": _j(cleaned.get("belongs_to_collection")),
                    "production_countries": cleaned.get("production_countries") or [],
                    "spoken_languages": cleaned.get("spoken_languages") or [],
                    "origin_country": cleaned.get("origin_country") or [],
                    "production_companies": _j(cleaned.get("production_companies") or []),
                    "streaming_providers": _j(cleaned.get("streaming_providers")),
                    "runtime": cleaned.get("runtime"),
                    "budget": cleaned.get("budget", 0),
                    "revenue": cleaned.get("revenue", 0),
                })
            else:
                # Create media anchor first
                anchor = db.execute(
                    text("INSERT INTO media (content_type, created_at) VALUES ('Movie', NOW()) RETURNING id"),
                ).fetchone()
                media_id = anchor.id
                inserted = True

                # Insert initial poster/backdrop as media_asset rows
                poster_path = cleaned.get("poster_path")
                backdrop_path = cleaned.get("backdrop_path")
                if poster_path:
                    db.execute(text("""
                        INSERT INTO media_asset (media_id, asset_type, source, url, file_path, is_primary, display_order, created_at)
                        VALUES (:mid, 'poster', 'tmdb', :url, :path, TRUE, 0, NOW())
                    """), {"mid": media_id, "url": f"https://image.tmdb.org/t/p/w500{poster_path}", "path": poster_path})
                if backdrop_path:
                    db.execute(text("""
                        INSERT INTO media_asset (media_id, asset_type, source, url, file_path, is_primary, display_order, created_at)
                        VALUES (:mid, 'backdrop', 'tmdb', :url, :path, TRUE, 0, NOW())
                    """), {"mid": media_id, "url": f"https://image.tmdb.org/t/p/original{backdrop_path}", "path": backdrop_path})

                db.execute(text("""
                    INSERT INTO movies (
                        media_id, tmdb_id, imdb_id, title, original_title, overview, tagline,
                        release_date, status, adult, popularity, vote_average, vote_count,
                        original_language, belongs_to_collection, production_countries,
                        spoken_languages, origin_country, production_companies,
                        streaming_providers, runtime, budget, revenue, created_at, updated_at
                    ) VALUES (
                        :media_id, :tmdb_id, :imdb_id, :title, :original_title, :overview, :tagline,
                        :release_date, :status, :adult, :popularity, :vote_average, :vote_count,
                        :original_language, :belongs_to_collection, :production_countries,
                        :spoken_languages, :origin_country, :production_companies,
                        :streaming_providers, :runtime, :budget, :revenue, NOW(), NOW()
                    )
                """), {
                    "media_id": media_id,
                    "tmdb_id": tid,
                    "imdb_id": cleaned.get("imdb_id"),
                    "title": cleaned["title"],
                    "original_title": cleaned.get("original_title"),
                    "overview": cleaned.get("overview"),
                    "tagline": cleaned.get("tagline"),
                    "release_date": cleaned.get("release_date"),
                    "status": cleaned.get("status"),
                    "adult": cleaned.get("adult", False),
                    "popularity": cleaned.get("popularity"),
                    "vote_average": cleaned.get("vote_average"),
                    "vote_count": cleaned.get("vote_count"),
                    "original_language": cleaned.get("original_language"),
                    "belongs_to_collection": _j(cleaned.get("belongs_to_collection")),
                    "production_countries": cleaned.get("production_countries") or [],
                    "spoken_languages": cleaned.get("spoken_languages") or [],
                    "origin_country": cleaned.get("origin_country") or [],
                    "production_companies": _j(cleaned.get("production_companies") or []),
                    "streaming_providers": _j(cleaned.get("streaming_providers")),
                    "runtime": cleaned.get("runtime"),
                    "budget": cleaned.get("budget", 0),
                    "revenue": cleaned.get("revenue", 0),
                })

            _link_genres(db, media_id, genre_map, genre_names)
            _link_keywords(db, media_id, kw_map, kw_names)
            _link_cast(db, media_id, cast_id_map, cast_list)

            # Upload to Supabase only for new rows (avoid redundant uploads)
            if inserted:
                _upload_images(storage, db, media_id, tid,
                               cleaned.get("poster_path"), cleaned.get("backdrop_path"))

            db.commit()
            saved += 1

        except Exception as e:
            logger.warning(f"Failed movie tmdb_id={item['id']}: {e}")
            db.rollback()
            failed += 1

    db.close()
    logger.success(f"Movies — saved/updated: {saved}, skipped: {skipped}, failed: {failed}")


# ---------------------------------------------------------------------------
# TV show ingestion
# ---------------------------------------------------------------------------

def ingest_tv(max_pages: int, dry_run: bool = False):
    logger.info(f"Starting TV ingestion — {max_pages} pages (popular + top-rated)")

    tmdb = TMDBService()
    db = SessionLocal()
    storage = None if dry_run else SupabaseStorageService()

    seen_ids: set[int] = set()
    items: list[dict] = []

    for source, fetch_fn in [
        ("popular", tmdb.client.get_popular_tv_shows),
        ("top_rated", tmdb.client.get_top_rated_tv_shows),
    ]:
        for page in range(1, max_pages + 1):
            resp = fetch_fn(page=page)
            if not resp or "results" not in resp:
                break
            for item in resp["results"]:
                if item["id"] not in seen_ids:
                    seen_ids.add(item["id"])
                    items.append(item)
            time.sleep(RATE_DELAY)

    logger.info(f"Fetched {len(items)} unique TV IDs — fetching full details")

    saved = skipped = failed = 0

    for item in tqdm(items, desc="TV Shows"):
        try:
            full = tmdb.client.get_tv_show(item["id"])
            time.sleep(RATE_DELAY)
            if not full or not tmdb.validator.validate_tv_show(full):
                skipped += 1
                continue

            cleaned = tmdb.validator.clean_tv_show_data(full)
            tid = cleaned["tmdb_id"]

            genre_names = cleaned.get("genres", [])
            kw_names = [k["name"] for k in cleaned.get("keywords", []) if k.get("name")]
            cast_list = cleaned.get("cast", [])

            genre_map = _upsert_genres(db, genre_names)
            kw_map = _upsert_keywords(db, kw_names)
            cast_id_map = _upsert_cast(db, cast_list)

            if dry_run:
                logger.info(f"[DRY RUN] Would upsert TV: {cleaned['title']} (tmdb_id={tid})")
                skipped += 1
                continue

            existing = db.execute(
                text("SELECT id, media_id FROM tv_shows WHERE tmdb_id = :tid"),
                {"tid": tid},
            ).fetchone()

            if existing:
                media_id = existing.media_id
                inserted = False
                db.execute(text("""
                    UPDATE tv_shows SET
                        title = :title, original_title = :original_title,
                        overview = :overview, tagline = :tagline,
                        release_date = :release_date, status = :status,
                        adult = :adult, popularity = :popularity,
                        vote_average = :vote_average, vote_count = :vote_count,
                        original_language = :original_language,
                        imdb_id = :imdb_id,
                        production_countries = :production_countries,
                        spoken_languages = :spoken_languages,
                        origin_country = :origin_country,
                        production_companies = :production_companies,
                        streaming_providers = :streaming_providers,
                        number_of_seasons = :seasons, number_of_episodes = :episodes,
                        episode_run_time = :run_time, last_air_date = :last_air,
                        in_production = :in_production, networks = :networks,
                        created_by = :created_by, show_type = :show_type,
                        updated_at = NOW()
                    WHERE tmdb_id = :tmdb_id
                """), {
                    "tmdb_id": tid,
                    "title": cleaned["title"],
                    "original_title": cleaned.get("original_title"),
                    "overview": cleaned.get("overview"),
                    "tagline": cleaned.get("tagline"),
                    "release_date": cleaned.get("release_date"),
                    "status": cleaned.get("status"),
                    "adult": cleaned.get("adult", False),
                    "popularity": cleaned.get("popularity"),
                    "vote_average": cleaned.get("vote_average"),
                    "vote_count": cleaned.get("vote_count"),
                    "original_language": cleaned.get("original_language"),
                    "imdb_id": cleaned.get("imdb_id"),
                    "production_countries": cleaned.get("production_countries") or [],
                    "spoken_languages": cleaned.get("spoken_languages") or [],
                    "origin_country": cleaned.get("origin_country") or [],
                    "production_companies": _j(cleaned.get("production_companies") or []),
                    "streaming_providers": _j(cleaned.get("streaming_providers")),
                    "seasons": full.get("number_of_seasons"),
                    "episodes": full.get("number_of_episodes"),
                    "run_time": _j(full.get("episode_run_time")),
                    "last_air": tmdb.validator._parse_date(full.get("last_air_date")),
                    "in_production": full.get("in_production", False),
                    "networks": _j(cleaned.get("networks") or []),
                    "created_by": _j(cleaned.get("created_by") or []),
                    "show_type": cleaned.get("show_type"),
                })
            else:
                anchor = db.execute(
                    text("INSERT INTO media (content_type, created_at) VALUES ('TV Show', NOW()) RETURNING id"),
                ).fetchone()
                media_id = anchor.id
                inserted = True

                poster_path = cleaned.get("poster_path")
                backdrop_path = cleaned.get("backdrop_path")
                if poster_path:
                    db.execute(text("""
                        INSERT INTO media_asset (media_id, asset_type, source, url, file_path, is_primary, display_order, created_at)
                        VALUES (:mid, 'poster', 'tmdb', :url, :path, TRUE, 0, NOW())
                    """), {"mid": media_id, "url": f"https://image.tmdb.org/t/p/w500{poster_path}", "path": poster_path})
                if backdrop_path:
                    db.execute(text("""
                        INSERT INTO media_asset (media_id, asset_type, source, url, file_path, is_primary, display_order, created_at)
                        VALUES (:mid, 'backdrop', 'tmdb', :url, :path, TRUE, 0, NOW())
                    """), {"mid": media_id, "url": f"https://image.tmdb.org/t/p/original{backdrop_path}", "path": backdrop_path})

                db.execute(text("""
                    INSERT INTO tv_shows (
                        media_id, tmdb_id, imdb_id, title, original_title, overview, tagline,
                        release_date, status, adult, popularity, vote_average, vote_count,
                        original_language, production_countries, spoken_languages,
                        origin_country, production_companies, streaming_providers,
                        number_of_seasons, number_of_episodes, episode_run_time,
                        last_air_date, in_production, networks, created_by, show_type,
                        created_at, updated_at
                    ) VALUES (
                        :media_id, :tmdb_id, :imdb_id, :title, :original_title, :overview, :tagline,
                        :release_date, :status, :adult, :popularity, :vote_average, :vote_count,
                        :original_language, :production_countries, :spoken_languages,
                        :origin_country, :production_companies, :streaming_providers,
                        :seasons, :episodes, :run_time,
                        :last_air, :in_production, :networks, :created_by, :show_type,
                        NOW(), NOW()
                    )
                """), {
                    "media_id": media_id,
                    "tmdb_id": tid,
                    "imdb_id": cleaned.get("imdb_id"),
                    "title": cleaned["title"],
                    "original_title": cleaned.get("original_title"),
                    "overview": cleaned.get("overview"),
                    "tagline": cleaned.get("tagline"),
                    "release_date": cleaned.get("release_date"),
                    "status": cleaned.get("status"),
                    "adult": cleaned.get("adult", False),
                    "popularity": cleaned.get("popularity"),
                    "vote_average": cleaned.get("vote_average"),
                    "vote_count": cleaned.get("vote_count"),
                    "original_language": cleaned.get("original_language"),
                    "production_countries": cleaned.get("production_countries") or [],
                    "spoken_languages": cleaned.get("spoken_languages") or [],
                    "origin_country": cleaned.get("origin_country") or [],
                    "production_companies": _j(cleaned.get("production_companies") or []),
                    "streaming_providers": _j(cleaned.get("streaming_providers")),
                    "seasons": full.get("number_of_seasons"),
                    "episodes": full.get("number_of_episodes"),
                    "run_time": _j(full.get("episode_run_time")),
                    "last_air": tmdb.validator._parse_date(full.get("last_air_date")),
                    "in_production": full.get("in_production", False),
                    "networks": _j(cleaned.get("networks") or []),
                    "created_by": _j(cleaned.get("created_by") or []),
                    "show_type": cleaned.get("show_type"),
                })

            _link_genres(db, media_id, genre_map, genre_names)
            _link_keywords(db, media_id, kw_map, kw_names)
            _link_cast(db, media_id, cast_id_map, cast_list)

            if inserted:
                _upload_images(storage, db, media_id, tid,
                               cleaned.get("poster_path"), cleaned.get("backdrop_path"))

            db.commit()
            saved += 1

        except Exception as e:
            logger.warning(f"Failed TV tmdb_id={item['id']}: {e}")
            db.rollback()
            failed += 1

    db.close()
    logger.success(f"TV Shows — saved/updated: {saved}, skipped: {skipped}, failed: {failed}")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Ingest movies and TV shows into Supabase")
    parser.add_argument("--movies", type=int, default=0, help="Pages of movies to fetch (popular + top-rated)")
    parser.add_argument("--tv", type=int, default=0, help="Pages of TV shows to fetch (popular + top-rated)")
    parser.add_argument("--dry-run", action="store_true", help="Print what would be ingested, no DB writes")
    args = parser.parse_args()

    if args.movies == 0 and args.tv == 0:
        parser.error("Specify --movies N and/or --tv N")

    logger.info("=" * 60)
    logger.info("FilmFind Media Ingestion (idempotent + Supabase images)")
    logger.info("=" * 60)

    if args.movies > 0:
        ingest_movies(args.movies, dry_run=args.dry_run)

    if args.tv > 0:
        ingest_tv(args.tv, dry_run=args.dry_run)


if __name__ == "__main__":
    main()
