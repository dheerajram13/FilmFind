"""
Single-film operations: LLM enrichment and embedding regeneration.
"""
from __future__ import annotations

import json
from typing import Optional

from sqlalchemy.orm import Session

from app.models.media import MediaEmbedding, MediaEnrichment, Movie, TVShow
from app.prompts import load_prompt
from app.services.embedding_service import EmbeddingService
from app.services.llm_client import LLMClient
from app.utils.logger import get_logger

logger = get_logger(__name__)

try:
    _ENRICH_SYSTEM = load_prompt("enrich", "1")
except FileNotFoundError:
    _ENRICH_SYSTEM = None


def _clamp(value: object, lo: int, hi: int) -> Optional[int]:
    if value is None:
        return None
    try:
        return max(lo, min(hi, int(value)))  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return None


class FilmEnrichmentService:
    """Runs Stage 2 LLM enrichment on a single Movie or TVShow record."""

    def __init__(self, llm_client: Optional[LLMClient] = None) -> None:
        self._llm = llm_client or LLMClient()

    def enrich(self, db: Session, film: Movie | TVShow) -> dict:
        """
        Run LLM enrichment and persist results to media_enrichment.

        Returns a dict with the updated field values.
        Raises ValueError if the LLM returns unparseable JSON.
        """
        anchor = film.media
        genres = (anchor.genres if anchor else []) or []
        genre_names = ", ".join(g.name for g in genres)
        overview = film.overview or "No overview available."

        prompt = (
            f'Title: "{film.title}"\n'
            f"Genres: {genre_names or 'unknown'}\n"
            f"Overview: {overview[:500]}\n\n"
            "Analyse this film and return the JSON enrichment data."
        )

        raw = self._llm.generate_completion(
            prompt=prompt,
            system_prompt=_ENRICH_SYSTEM,
            temperature=0.3,
            max_tokens=512,
            response_format={"type": "json_object"},
        )

        try:
            data = json.loads(raw)
        except Exception as exc:
            raise ValueError(f"LLM returned invalid JSON: {exc}") from exc

        enrich = anchor.enrichment if anchor else None
        if enrich is None:
            enrich = MediaEnrichment(media_id=film.media_id)
            db.add(enrich)

        enrich.narrative_dna = data.get("narrative_dna")
        enrich.themes = data.get("themes") or []
        enrich.tone_tags = data.get("tone_tags") or []
        enrich.darkness_score = _clamp(data.get("darkness_score"), 0, 10)
        enrich.complexity_score = _clamp(data.get("complexity_score"), 0, 10)
        enrich.energy_score = _clamp(data.get("energy_score"), 0, 10)
        db.commit()

        logger.info(f"Enriched film {film.media_id}: {film.title!r}")
        return {
            "narrative_dna": enrich.narrative_dna,
            "themes": enrich.themes,
            "tone_tags": enrich.tone_tags,
            "darkness_score": enrich.darkness_score,
            "complexity_score": enrich.complexity_score,
            "energy_score": enrich.energy_score,
        }


class EmbeddingRegenerationService:
    """Regenerates the vector embedding for a single Movie or TVShow record."""

    def regenerate(self, db: Session, film: Movie | TVShow) -> int:
        """
        Encode film text and persist new embedding to media_embedding.

        Returns the embedding dimension.
        """
        svc = EmbeddingService()
        anchor = film.media
        genres = (anchor.genres if anchor else []) or []
        genre_names = " ".join(g.name for g in genres)
        text = f"{film.title} {film.overview or ''} {genre_names}".strip()
        vector = svc.encode(text)
        vector_list = vector.tolist() if hasattr(vector, "tolist") else list(vector)

        emb = db.query(MediaEmbedding).filter(MediaEmbedding.media_id == film.media_id).first()
        if emb is None:
            emb = MediaEmbedding(media_id=film.media_id)
            db.add(emb)
        emb.embedding = vector_list
        emb.needs_rebuild = False
        db.commit()

        logger.info(f"Regenerated embedding for film {film.media_id}: {film.title!r}")
        return len(vector_list)
