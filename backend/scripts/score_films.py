#!/usr/bin/env python
"""
Stage 3: Generate mood/context/craving score matrices for 60-Second Mode.

Queries media where mood_scores IS NULL AND narrative_dna IS NOT NULL,
calls Gemini to generate structured score matrices, then stores them as JSONB.

Run Stage 2 (enrich_films.py) first to populate narrative_dna.

Usage:
    python scripts/score_films.py
    python scripts/score_films.py --batch 50
    python scripts/score_films.py --batch 10 --offset 0
"""
import argparse
import json
import re
import sys
import time
from pathlib import Path

from loguru import logger

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.database import SessionLocal
from app.core.scoring import VALID_CONTEXTS, VALID_CRAVINGS, VALID_MOODS
from app.models.media import Media
from app.services.llm_client import LLMClient


_VALID_MOODS_STR = ", ".join(sorted(VALID_MOODS))
_VALID_CONTEXTS_STR = ", ".join(sorted(VALID_CONTEXTS))
_VALID_CRAVINGS_STR = ", ".join(sorted(VALID_CRAVINGS))

_SYSTEM_PROMPT = (
    "You are a film scoring expert for a recommendation engine. "
    "Given a film's metadata, generate numeric scores (0.0–1.0) for how well "
    "this film serves each mood, context, and craving category.\n\n"
    "Respond ONLY with valid JSON:\n"
    "{\n"
    '  "mood_scores": {<mood_key>: <0.0-1.0>, ...},\n'
    '  "context_scores": {<context_key>: <0.0-1.0>, ...},\n'
    '  "craving_scores": {<craving_key>: <0.0-1.0>, ...}\n'
    "}\n\n"
    f"Valid mood keys: {_VALID_MOODS_STR}\n"
    f"Valid context keys: {_VALID_CONTEXTS_STR}\n"
    f"Valid craving keys: {_VALID_CRAVINGS_STR}\n\n"
    "Score 1.0 = perfect match, 0.0 = terrible match. "
    "Be specific — not every film scores high on everything."
)


def score_batch(batch_size: int, offset: int = 0) -> None:
    db = SessionLocal()
    client = LLMClient()

    try:
        films = (
            db.query(Media)
            .filter(
                Media.mood_scores.is_(None),
                Media.narrative_dna.isnot(None),
            )
            .order_by(Media.popularity.desc())
            .offset(offset)
            .limit(batch_size)
            .all()
        )

        if not films:
            # Also process films without narrative_dna if none are waiting
            films = (
                db.query(Media)
                .filter(Media.mood_scores.is_(None))
                .order_by(Media.popularity.desc())
                .offset(offset)
                .limit(batch_size)
                .all()
            )

        if not films:
            logger.info("No films need scoring (mood_scores already set for all).")
            return

        logger.info(f"Scoring {len(films)} films (offset={offset})")

        scored = 0
        failed = 0

        for film in films:
            try:
                genre_names = ", ".join(g.name for g in (film.genres or []))
                overview = film.overview or "No overview available."
                narrative = film.narrative_dna or ""
                tone_str = ", ".join(film.tone_tags or [])

                prompt = (
                    f'Title: "{film.title}"\n'
                    f"Genres: {genre_names or 'unknown'}\n"
                    f"Overview: {overview[:400]}\n"
                    f"Narrative DNA: {narrative[:300]}\n"
                    f"Tone tags: {tone_str or 'unknown'}\n"
                    f"darkness_score: {film.darkness_score}\n"
                    f"complexity_score: {film.complexity_score}\n"
                    f"energy_score: {film.energy_score}\n\n"
                    "Generate mood/context/craving score matrices for this film."
                )

                raw = client.generate_completion(
                    prompt=prompt,
                    system_prompt=_SYSTEM_PROMPT,
                    temperature=0.2,
                    max_tokens=512,
                    response_format={"type": "json_object"},
                )

                data = _parse_scores(raw)
                if not data:
                    logger.warning(f"[{film.id}] {film.title!r}: failed to parse LLM response")
                    failed += 1
                    continue

                film.mood_scores = data.get("mood_scores") or {}
                film.context_scores = data.get("context_scores") or {}
                film.craving_scores = data.get("craving_scores") or {}

                db.commit()
                scored += 1
                logger.info(f"[{film.id}] {film.title!r}: scored ✓")

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

        logger.info(f"Done. scored={scored} failed={failed}")

    finally:
        db.close()


def _parse_scores(raw: str) -> dict | None:
    try:
        return json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        pass

    match = re.search(r'\{.*\}', raw, re.DOTALL)
    if match:
        try:
            return json.loads(match.group())
        except (json.JSONDecodeError, TypeError):
            pass

    return None


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Stage 3: Generate mood/context/craving score matrices")
    parser.add_argument("--batch", type=int, default=50, help="Number of films to process")
    parser.add_argument("--offset", type=int, default=0, help="Row offset to start from")
    args = parser.parse_args()

    score_batch(batch_size=args.batch, offset=args.offset)
