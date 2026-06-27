#!/usr/bin/env python
"""
Stage 2 enrichment: Populate narrative_dna, themes, tone_tags, and dimension scores.

Queries media where narrative_dna IS NULL, calls Gemini via LLMClient to
extract structured enrichment data, then stores it back into the DB.

Usage:
    python scripts/enrich_films.py
    python scripts/enrich_films.py --batch 50
    python scripts/enrich_films.py --batch 10 --offset 0
"""
import argparse
import json
import sys
import time
from pathlib import Path

from loguru import logger

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.database import SessionLocal
from app.models.media import Media, MediaEnrichment, Movie, TVShow
from app.services.llm_client import LLMClient


_SYSTEM_PROMPT = (
    "You are a film analysis expert. Given a film's title, overview, and genres, "
    "extract structured metadata. Respond ONLY with valid JSON matching this schema exactly:\n"
    "{\n"
    '  "narrative_dna": "<2-3 sentence description of narrative structure, themes, and emotional arc>",\n'
    '  "themes": ["theme1", "theme2", "theme3"],\n'
    '  "tone_tags": ["tone1", "tone2"],\n'
    '  "darkness_score": <integer 0-10>,\n'
    '  "complexity_score": <integer 0-10>,\n'
    '  "energy_score": <integer 0-10>\n'
    "}\n"
    "darkness_score: 0=pure family-friendly, 10=very dark/disturbing.\n"
    "complexity_score: 0=very simple plot, 10=highly complex/cerebral.\n"
    "energy_score: 0=slow/meditative, 10=high-octane/intense."
)


def enrich_batch(batch_size: int, offset: int = 0) -> None:
    db = SessionLocal()
    client = LLMClient()

    try:
        from sqlalchemy.orm import selectinload, outerjoin

        # Find movies and TV shows that have no enrichment row yet
        movies_to_enrich = (
            db.query(Movie)
            .outerjoin(Movie.media).outerjoin(Media.enrichment)
            .filter(MediaEnrichment.media_id.is_(None))
            .options(
                selectinload(Movie.media).selectinload(Media.genres),
                selectinload(Movie.media).selectinload(Media.enrichment),
            )
            .order_by(Movie.popularity.desc())
            .offset(offset)
            .limit(batch_size)
            .all()
        )
        remaining = batch_size - len(movies_to_enrich)
        shows_to_enrich = (
            db.query(TVShow)
            .outerjoin(TVShow.media).outerjoin(Media.enrichment)
            .filter(MediaEnrichment.media_id.is_(None))
            .options(
                selectinload(TVShow.media).selectinload(Media.genres),
                selectinload(TVShow.media).selectinload(Media.enrichment),
            )
            .order_by(TVShow.popularity.desc())
            .limit(remaining)
            .all()
        ) if remaining > 0 else []

        films = movies_to_enrich + shows_to_enrich

        if not films:
            logger.info("No films need enrichment.")
            return

        logger.info(f"Enriching {len(films)} films (offset={offset})")

        enriched = 0
        failed = 0

        for film in films:
            try:
                genres = film.media.genres if film.media else []
                genre_names = ", ".join(g.name for g in genres)
                overview = film.overview or "No overview available."

                prompt = (
                    f'Title: "{film.title}"\n'
                    f"Genres: {genre_names or 'unknown'}\n"
                    f"Overview: {overview[:500]}\n\n"
                    "Analyse this film and return the JSON enrichment data."
                )

                raw = client.generate_completion(
                    prompt=prompt,
                    system_prompt=_SYSTEM_PROMPT,
                    temperature=0.3,
                    max_tokens=512,
                    response_format={"type": "json_object"},
                )

                data = _parse_enrichment(raw)
                if not data:
                    logger.warning(f"[{film.media_id}] {film.title!r}: failed to parse LLM response")
                    failed += 1
                    continue

                # Upsert into media_enrichment (satellite table)
                enrich = film.media.enrichment if film.media else None
                if enrich is None:
                    enrich = MediaEnrichment(media_id=film.media_id)
                    db.add(enrich)

                enrich.narrative_dna    = data.get("narrative_dna") or None
                enrich.themes           = data.get("themes") or []
                enrich.tone_tags        = data.get("tone_tags") or []
                enrich.darkness_score   = _clamp(data.get("darkness_score"), 0, 10)
                enrich.complexity_score = _clamp(data.get("complexity_score"), 0, 10)
                enrich.energy_score     = _clamp(data.get("energy_score"), 0, 10)

                db.commit()
                enriched += 1
                logger.info(
                    f"[{film.media_id}] {film.title!r}: darkness={enrich.darkness_score} "
                    f"complexity={enrich.complexity_score} energy={enrich.energy_score}"
                )

                # Respect Gemini free tier rate limits (15 RPM)
                time.sleep(0.5)

            except KeyboardInterrupt:
                logger.info("Interrupted — committing progress so far.")
                break
            except Exception as exc:
                logger.error(f"[{film.id}] {film.title!r}: {exc}")
                failed += 1
                try:
                    db.rollback()
                except Exception:
                    pass

        logger.info(f"Done. enriched={enriched} failed={failed}")

    finally:
        db.close()


def _parse_enrichment(raw: str) -> dict | None:
    try:
        return json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        pass

    import re
    match = re.search(r'\{.*\}', raw, re.DOTALL)
    if match:
        try:
            return json.loads(match.group())
        except (json.JSONDecodeError, TypeError):
            pass

    return None


def _clamp(value, lo: int, hi: int) -> int | None:
    if value is None:
        return None
    try:
        return max(lo, min(hi, int(value)))
    except (TypeError, ValueError):
        return None


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Stage 2: Enrich films with narrative DNA and dimension scores")
    parser.add_argument("--batch", type=int, default=50, help="Number of films to process")
    parser.add_argument("--offset", type=int, default=0, help="Row offset to start from")
    args = parser.parse_args()

    enrich_batch(batch_size=args.batch, offset=args.offset)
