#!/usr/bin/env python
"""
Stage 1 ingestion — fetch movies and TV shows from TMDB via genre-based discovery.

Sources films using /discover/movie and /discover/tv per genre rather than flat
popular/top-rated lists, giving balanced coverage across all categories.

Usage:
    python scripts/ingest/ingest_media.py --movies --pages-per-genre 3
    python scripts/ingest/ingest_media.py --tv --pages-per-genre 5
    python scripts/ingest/ingest_media.py --movies --tv --pages-per-genre 3
    python scripts/ingest/ingest_media.py --movies --dry-run

Quality floors (overridable via CLI):
    --min-votes  300  (movies) / 100 (TV)
    --min-rating 6.0
"""
import argparse
import json
import sys
from pathlib import Path
from typing import Optional

from loguru import logger
from tqdm import tqdm
from sqlalchemy import text

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from app.core.database import SessionLocal
from app.core.storage import SupabaseStorageService
from app.services.tmdb import TMDBService

# ---------------------------------------------------------------------------
# Genre maps — TMDB genre IDs
# ---------------------------------------------------------------------------

MOVIE_GENRES: dict[str, int] = {
    "Action": 28,
    "Adventure": 12,
    "Animation": 16,
    "Comedy": 35,
    "Crime": 80,
    "Documentary": 99,
    "Drama": 18,
    "Fantasy": 14,
    "History": 36,
    "Horror": 27,
    "Mystery": 9648,
    "Romance": 10749,
    "Science Fiction": 878,
    "Thriller": 53,
    "Western": 37,
}

TV_GENRES: dict[str, int] = {
    "Action & Adventure": 10759,
    "Animation": 16,
    "Comedy": 35,
    "Crime": 80,
    "Documentary": 99,
    "Drama": 18,
    "Mystery": 9648,
    "Sci-Fi & Fantasy": 10765,
    "War & Politics": 10768,
    "Western": 37,
}

RATE_DELAY = 0.3  # seconds between requests


# ---------------------------------------------------------------------------
# DB helpers — genre / keyword / cast upserts and junction linking
# ---------------------------------------------------------------------------

def _j(val) -> Optional[str]:
    """Serialise dicts/lists to JSON string for JSONB columns via psycopg2."""
    if val is None:
        return None
    if isinstance(val, (dict, list)):
        return json.dumps(val)
    return val


def _upsert_genres(db, genre_names: list[str]) -> dict[str, int]:
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
    if not cast_list:
        return {}
    for c in cast_list:
        db.execute(
            text("""
                INSERT INTO "cast" (tmdb_id, name, profile_path, popularity, created_at, updated_at)
                VALUES (:tid, :name, :profile_path, :popularity, NOW(), NOW())
                ON CONFLICT (tmdb_id) DO NOTHING
            """),
            {
                "tid": c["tmdb_id"],
                "name": c["name"],
                "profile_path": c.get("profile_path"),
                "popularity": c.get("popularity"),
            },
        )
    tmdb_ids = [c["tmdb_id"] for c in cast_list]
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
                text("INSERT INTO media_genres (media_id, genre_id, created_at) VALUES (:mid, :gid, NOW()) ON CONFLICT DO NOTHING"),
                {"mid": media_id, "gid": gid},
            )


def _link_keywords(db, media_id: int, kw_map: dict[str, int], kw_names: list[str]):
    for name in kw_names:
        kid = kw_map.get(name)
        if kid:
            db.execute(
                text("INSERT INTO media_keywords (media_id, keyword_id, created_at) VALUES (:mid, :kid, NOW()) ON CONFLICT DO NOTHING"),
                {"mid": media_id, "kid": kid},
            )


def _link_cast(db, media_id: int, cast_id_map: dict[int, int], cast_list: list[dict]):
    for order, c in enumerate(cast_list):
        cid = cast_id_map.get(c["tmdb_id"])
        if cid:
            db.execute(
                text("INSERT INTO media_cast (media_id, cast_id, character_name, order_position, created_at) VALUES (:mid, :cid, :char, :order, NOW()) ON CONFLICT DO NOTHING"),
                {"mid": media_id, "cid": cid, "char": c.get("character"), "order": order},
            )


def _upload_images(
    storage: Optional[SupabaseStorageService],
    db,
    media_id: int,
    tmdb_id: int,
    poster_path: Optional[str],
    backdrop_path: Optional[str],
):
    if not storage:
        return
    if poster_path:
        url = storage.upload_poster(tmdb_id, poster_path)
        if url:
            db.execute(text("UPDATE media_asset SET is_primary = FALSE WHERE media_id = :mid AND asset_type = 'poster'"), {"mid": media_id})
            db.execute(text("""
                INSERT INTO media_asset (media_id, asset_type, source, url, is_primary, display_order, created_at)
                VALUES (:mid, 'poster', 'supabase', :url, TRUE, 0, NOW()) ON CONFLICT DO NOTHING
            """), {"mid": media_id, "url": url})
    if backdrop_path:
        url = storage.upload_backdrop(tmdb_id, backdrop_path)
        if url:
            db.execute(text("UPDATE media_asset SET is_primary = FALSE WHERE media_id = :mid AND asset_type = 'backdrop'"), {"mid": media_id})
            db.execute(text("""
                INSERT INTO media_asset (media_id, asset_type, source, url, is_primary, display_order, created_at)
                VALUES (:mid, 'backdrop', 'supabase', :url, TRUE, 0, NOW()) ON CONFLICT DO NOTHING
            """), {"mid": media_id, "url": url})


# ---------------------------------------------------------------------------
# Discovery helpers
# ---------------------------------------------------------------------------

def _collect_ids_from_discover(
    client,
    genre_map: dict[str, int],
    pages_per_genre: int,
    is_tv: bool,
    min_vote_count: int,
    min_vote_average: float,
) -> list[int]:
    """
    Page through /discover/movie or /discover/tv for each genre.
    Returns a deduplicated list of TMDB IDs.
    """
    discover_fn = client.discover_tv if is_tv else client.discover_movies
    seen: set[int] = set()

    for genre_name, genre_id in genre_map.items():
        for page in range(1, pages_per_genre + 1):
            resp = discover_fn(genre_id, page, min_vote_count, min_vote_average)
            if not resp or not resp.get("results"):
                break
            for item in resp["results"]:
                seen.add(item["id"])
            # Stop early if we've reached the last page for this genre
            if page >= resp.get("total_pages", 1):
                break

        logger.info(f"  {genre_name}: {len(seen)} unique IDs collected so far")

    return list(seen)


# ---------------------------------------------------------------------------
# Movie ingestion
# ---------------------------------------------------------------------------

def ingest_movies(
    pages_per_genre: int,
    min_votes: int,
    min_rating: float,
    dry_run: bool = False,
) -> None:
    logger.info(f"Movie ingestion — {pages_per_genre} pages/genre, min_votes={min_votes}, min_rating={min_rating}")
    tmdb = TMDBService()
    db = SessionLocal()
    storage = None if dry_run else SupabaseStorageService()

    try:
        # Phase 1: collect unique TMDB IDs across all genres
        logger.info("Phase 1: collecting IDs via discover...")
        tmdb_ids = _collect_ids_from_discover(
            tmdb.client, MOVIE_GENRES, pages_per_genre, is_tv=False,
            min_vote_count=min_votes, min_vote_average=min_rating,
        )
        logger.info(f"Collected {len(tmdb_ids)} unique movie IDs — fetching full details")

        # Phase 2: fetch full details and upsert
        saved = skipped = failed = 0

        for tmdb_id in tqdm(tmdb_ids, desc="Movies"):
            try:
                full = tmdb.client.get_movie(tmdb_id)
                if not full or not tmdb.validator.validate_movie(full):
                    skipped += 1
                    continue

                cleaned = tmdb.validator.clean_movie_data(full)

                if dry_run:
                    logger.info(f"[DRY RUN] {cleaned['title']!r} ({tmdb_id})")
                    skipped += 1
                    continue

                # Resolve media anchor: check by tmdb_id (indexed), create if missing
                row = db.execute(
                    text("SELECT media_id FROM movies WHERE tmdb_id = :tid"),
                    {"tid": tmdb_id},
                ).fetchone()

                if row:
                    media_id = row.media_id
                    is_new = False
                else:
                    anchor = db.execute(
                        text("INSERT INTO media (content_type, created_at) VALUES ('Movie', NOW()) RETURNING id")
                    ).fetchone()
                    media_id = anchor.id
                    is_new = True

                    # Seed initial TMDB asset rows for new films
                    if cleaned["poster_path"]:
                        db.execute(text("""
                            INSERT INTO media_asset (media_id, asset_type, source, url, file_path, is_primary, display_order, created_at)
                            VALUES (:mid, 'poster', 'tmdb', :url, :path, TRUE, 0, NOW())
                        """), {
                            "mid": media_id,
                            "url": f"https://image.tmdb.org/t/p/w500{cleaned['poster_path']}",
                            "path": cleaned["poster_path"],
                        })
                    if cleaned["backdrop_path"]:
                        db.execute(text("""
                            INSERT INTO media_asset (media_id, asset_type, source, url, file_path, is_primary, display_order, created_at)
                            VALUES (:mid, 'backdrop', 'tmdb', :url, :path, TRUE, 0, NOW())
                        """), {
                            "mid": media_id,
                            "url": f"https://image.tmdb.org/t/p/original{cleaned['backdrop_path']}",
                            "path": cleaned["backdrop_path"],
                        })

                # Upsert movie row — ON CONFLICT updates all mutable fields
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
                    ON CONFLICT (tmdb_id) DO UPDATE SET
                        title                 = EXCLUDED.title,
                        original_title        = EXCLUDED.original_title,
                        overview              = EXCLUDED.overview,
                        tagline               = EXCLUDED.tagline,
                        release_date          = EXCLUDED.release_date,
                        status                = EXCLUDED.status,
                        adult                 = EXCLUDED.adult,
                        popularity            = EXCLUDED.popularity,
                        vote_average          = EXCLUDED.vote_average,
                        vote_count            = EXCLUDED.vote_count,
                        original_language     = EXCLUDED.original_language,
                        imdb_id               = EXCLUDED.imdb_id,
                        belongs_to_collection = EXCLUDED.belongs_to_collection,
                        production_countries  = EXCLUDED.production_countries,
                        spoken_languages      = EXCLUDED.spoken_languages,
                        origin_country        = EXCLUDED.origin_country,
                        production_companies  = EXCLUDED.production_companies,
                        streaming_providers   = EXCLUDED.streaming_providers,
                        runtime               = EXCLUDED.runtime,
                        budget                = EXCLUDED.budget,
                        revenue               = EXCLUDED.revenue,
                        updated_at            = NOW()
                """), {
                    "media_id": media_id,
                    "tmdb_id": cleaned["tmdb_id"],
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

                # Link relational data
                genre_map = _upsert_genres(db, cleaned["genres"])
                kw_map = _upsert_keywords(db, [k["name"] for k in cleaned["keywords"]])
                cast_id_map = _upsert_cast(db, cleaned["cast"])
                _link_genres(db, media_id, genre_map, cleaned["genres"])
                _link_keywords(db, media_id, kw_map, [k["name"] for k in cleaned["keywords"]])
                _link_cast(db, media_id, cast_id_map, cleaned["cast"])

                # Upload images to Supabase only for new records
                if is_new:
                    _upload_images(storage, db, media_id, tmdb_id, cleaned["poster_path"], cleaned["backdrop_path"])

                db.commit()
                saved += 1

            except KeyboardInterrupt:
                logger.info("Interrupted — progress committed so far.")
                break
            except Exception as exc:
                logger.warning(f"Failed tmdb_id={tmdb_id}: {exc}")
                db.rollback()
                failed += 1

        logger.success(f"Movies — saved/updated: {saved}, skipped: {skipped}, failed: {failed}")

    finally:
        db.close()


# ---------------------------------------------------------------------------
# TV show ingestion
# ---------------------------------------------------------------------------

def ingest_tv(
    pages_per_genre: int,
    min_votes: int,
    min_rating: float,
    dry_run: bool = False,
) -> None:
    logger.info(f"TV ingestion — {pages_per_genre} pages/genre, min_votes={min_votes}, min_rating={min_rating}")
    tmdb = TMDBService()
    db = SessionLocal()
    storage = None if dry_run else SupabaseStorageService()

    try:
        logger.info("Phase 1: collecting IDs via discover...")
        tmdb_ids = _collect_ids_from_discover(
            tmdb.client, TV_GENRES, pages_per_genre, is_tv=True,
            min_vote_count=min_votes, min_vote_average=min_rating,
        )
        logger.info(f"Collected {len(tmdb_ids)} unique TV IDs — fetching full details")

        saved = skipped = failed = 0

        for tmdb_id in tqdm(tmdb_ids, desc="TV Shows"):
            try:
                full = tmdb.client.get_tv_show(tmdb_id)
                if not full or not tmdb.validator.validate_tv_show(full):
                    skipped += 1
                    continue

                cleaned = tmdb.validator.clean_tv_show_data(full)

                if dry_run:
                    logger.info(f"[DRY RUN] {cleaned['title']!r} ({tmdb_id})")
                    skipped += 1
                    continue

                row = db.execute(
                    text("SELECT media_id FROM tv_shows WHERE tmdb_id = :tid"),
                    {"tid": tmdb_id},
                ).fetchone()

                if row:
                    media_id = row.media_id
                    is_new = False
                else:
                    anchor = db.execute(
                        text("INSERT INTO media (content_type, created_at) VALUES ('TV Show', NOW()) RETURNING id")
                    ).fetchone()
                    media_id = anchor.id
                    is_new = True

                    if cleaned["poster_path"]:
                        db.execute(text("""
                            INSERT INTO media_asset (media_id, asset_type, source, url, file_path, is_primary, display_order, created_at)
                            VALUES (:mid, 'poster', 'tmdb', :url, :path, TRUE, 0, NOW())
                        """), {
                            "mid": media_id,
                            "url": f"https://image.tmdb.org/t/p/w500{cleaned['poster_path']}",
                            "path": cleaned["poster_path"],
                        })
                    if cleaned["backdrop_path"]:
                        db.execute(text("""
                            INSERT INTO media_asset (media_id, asset_type, source, url, file_path, is_primary, display_order, created_at)
                            VALUES (:mid, 'backdrop', 'tmdb', :url, :path, TRUE, 0, NOW())
                        """), {
                            "mid": media_id,
                            "url": f"https://image.tmdb.org/t/p/original{cleaned['backdrop_path']}",
                            "path": cleaned["backdrop_path"],
                        })

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
                    ON CONFLICT (tmdb_id) DO UPDATE SET
                        title                = EXCLUDED.title,
                        original_title       = EXCLUDED.original_title,
                        overview             = EXCLUDED.overview,
                        tagline              = EXCLUDED.tagline,
                        release_date         = EXCLUDED.release_date,
                        status               = EXCLUDED.status,
                        adult                = EXCLUDED.adult,
                        popularity           = EXCLUDED.popularity,
                        vote_average         = EXCLUDED.vote_average,
                        vote_count           = EXCLUDED.vote_count,
                        original_language    = EXCLUDED.original_language,
                        imdb_id              = EXCLUDED.imdb_id,
                        production_countries = EXCLUDED.production_countries,
                        spoken_languages     = EXCLUDED.spoken_languages,
                        origin_country       = EXCLUDED.origin_country,
                        production_companies = EXCLUDED.production_companies,
                        streaming_providers  = EXCLUDED.streaming_providers,
                        number_of_seasons    = EXCLUDED.number_of_seasons,
                        number_of_episodes   = EXCLUDED.number_of_episodes,
                        episode_run_time     = EXCLUDED.episode_run_time,
                        last_air_date        = EXCLUDED.last_air_date,
                        in_production        = EXCLUDED.in_production,
                        networks             = EXCLUDED.networks,
                        created_by           = EXCLUDED.created_by,
                        show_type            = EXCLUDED.show_type,
                        updated_at           = NOW()
                """), {
                    "media_id": media_id,
                    "tmdb_id": cleaned["tmdb_id"],
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
                    "seasons": cleaned.get("number_of_seasons"),
                    "episodes": cleaned.get("number_of_episodes"),
                    "run_time": _j(cleaned.get("episode_run_time") or []),
                    "last_air": cleaned.get("last_air_date"),
                    "in_production": cleaned.get("in_production", False),
                    "networks": _j(cleaned.get("networks") or []),
                    "created_by": _j(cleaned.get("created_by") or []),
                    "show_type": cleaned.get("show_type"),
                })

                genre_map = _upsert_genres(db, cleaned["genres"])
                kw_map = _upsert_keywords(db, [k["name"] for k in cleaned["keywords"]])
                cast_id_map = _upsert_cast(db, cleaned["cast"])
                _link_genres(db, media_id, genre_map, cleaned["genres"])
                _link_keywords(db, media_id, kw_map, [k["name"] for k in cleaned["keywords"]])
                _link_cast(db, media_id, cast_id_map, cleaned["cast"])

                if is_new:
                    _upload_images(storage, db, media_id, tmdb_id, cleaned["poster_path"], cleaned["backdrop_path"])

                db.commit()
                saved += 1

            except KeyboardInterrupt:
                logger.info("Interrupted — progress committed so far.")
                break
            except Exception as exc:
                logger.warning(f"Failed tmdb_id={tmdb_id}: {exc}")
                db.rollback()
                failed += 1

        logger.success(f"TV Shows — saved/updated: {saved}, skipped: {skipped}, failed: {failed}")

    finally:
        db.close()


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Ingest movies and TV shows via TMDB genre discovery"
    )
    parser.add_argument("--movies", action="store_true", help="Ingest movies")
    parser.add_argument("--tv", action="store_true", help="Ingest TV shows")
    parser.add_argument("--pages-per-genre", type=int, default=3,
                        help="Pages to fetch per genre from /discover (default: 3 ≈ 60 films/genre)")
    parser.add_argument("--min-votes", type=int, default=300,
                        help="Minimum vote count floor (default: 300; use 100 for TV/documentaries)")
    parser.add_argument("--min-rating", type=float, default=6.0,
                        help="Minimum vote average floor (default: 6.0)")
    parser.add_argument("--dry-run", action="store_true",
                        help="Print what would be ingested without writing to DB")
    args = parser.parse_args()

    if not args.movies and not args.tv:
        parser.error("Specify --movies and/or --tv")

    if args.movies:
        ingest_movies(args.pages_per_genre, args.min_votes, args.min_rating, args.dry_run)

    if args.tv:
        # TV shows typically have fewer votes — default to lower floor
        min_votes = args.min_votes if args.min_votes != 300 else 100
        ingest_tv(args.pages_per_genre, min_votes, args.min_rating, args.dry_run)


if __name__ == "__main__":
    main()
