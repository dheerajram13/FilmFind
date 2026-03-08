"""
Text preprocessing service for media embeddings.

Converts media metadata into a rich, structured text format optimised for
semantic embedding generation. Incorporates enrichment fields (narrative_dna,
tone_tags, themes) when available.
"""

import logging
from typing import TYPE_CHECKING

from app.core.config import settings

if TYPE_CHECKING:
    from app.models.media import Media


logger = logging.getLogger(__name__)


class TextPreprocessor:
    """
    Preprocessor for converting media data into embedding-ready text.

    Format:
        {title} ({year}) [{content_type}]
        {genres} | {tone_tags} | {themes}
        {original_language} production from {origin_country}
        {networks if TV} | {collection_name if movie in collection}
        {narrative_dna or overview}
        Director: {director} | Cast: {lead cast with character names}
    """

    @staticmethod
    def preprocess_movie(movie: "Media") -> str:
        """
        Preprocess a media item into structured text for embedding.

        Args:
            movie: Media entity (Movie or TVShow) with relationships loaded

        Returns:
            Cleaned, structured text ready for embedding
        """
        parts = []

        # 1. Title + year + content type header
        year = movie.release_date.year if movie.release_date else None
        content_type = "Movie" if getattr(movie, "media_type", "movie") == "movie" else "TV Series"
        year_str = f" ({year})" if year else ""
        parts.append(f"{movie.title.strip()}{year_str} [{content_type}]")

        # 2. Genres | tone_tags | themes
        genre_names = [g.name for g in movie.genres] if movie.genres else []
        tone_tags = getattr(movie, "tone_tags", None) or []
        themes = getattr(movie, "themes", None) or []
        category_parts = []
        if genre_names:
            category_parts.append(", ".join(genre_names))
        if tone_tags:
            category_parts.append(", ".join(tone_tags))
        if themes:
            category_parts.append(", ".join(themes))
        if category_parts:
            parts.append(" | ".join(category_parts))

        # 3. Language + country of origin
        lang = getattr(movie, "original_language", None)
        origin = getattr(movie, "origin_country", None) or []
        lang_line_parts = []
        if lang:
            lang_line_parts.append(f"{lang.upper()} production")
        if origin:
            countries = ", ".join(origin) if isinstance(origin, list) else str(origin)
            lang_line_parts.append(f"from {countries}")
        if lang_line_parts:
            parts.append(" ".join(lang_line_parts))

        # 4. Networks (TV) or collection (Movie)
        context_line = []
        if content_type == "TV Series":
            networks = getattr(movie, "networks", None) or []
            if networks:
                network_names = [n.get("name", "") for n in networks if isinstance(n, dict) and n.get("name")]
                if network_names:
                    context_line.append(f"Networks: {', '.join(network_names)}")
        else:
            collection = getattr(movie, "belongs_to_collection", None)
            if collection and isinstance(collection, dict) and collection.get("name"):
                context_line.append(f"Collection: {collection['name']}")
        if context_line:
            parts.append(" | ".join(context_line))

        # 5. Narrative DNA (enriched) or overview (fallback)
        narrative_dna = getattr(movie, "narrative_dna", None)
        if narrative_dna and narrative_dna.strip():
            parts.append(narrative_dna.strip())
        elif movie.overview:
            overview = movie.overview.strip()
            if overview:
                parts.append(overview)

        # 6. Tagline (if present and different from overview)
        if movie.tagline:
            tagline = movie.tagline.strip()
            if tagline:
                parts.append(f'"{tagline}"')

        # 7. Cast with character names
        if movie.cast_members:
            cast_list = movie.cast_members[: settings.MAX_CAST_MEMBERS]
            parts.append(f"Cast: {', '.join(c.name for c in cast_list)}")

        # 8. Keywords
        if movie.keywords:
            keyword_names = [k.name for k in movie.keywords[: settings.MAX_KEYWORDS]]
            if keyword_names:
                parts.append(f"Keywords: {', '.join(keyword_names)}")

        combined = "\n".join(parts)
        return TextPreprocessor._clean_text(combined)

    @staticmethod
    def _clean_text(text: str) -> str:
        """Clean text by removing excessive whitespace and normalizing."""
        lines = [" ".join(line.split()) for line in text.split("\n") if line.strip()]
        return "\n".join(lines).strip()

    @staticmethod
    def validate_text(text: str, min_length: int | None = None) -> bool:
        """Validate that text is suitable for embedding generation."""
        if not text or not isinstance(text, str):
            return False
        if min_length is None:
            min_length = settings.MIN_TEXT_LENGTH
        if len(text.strip()) < min_length:
            return False
        return any(c.isalnum() for c in text)

    @staticmethod
    def batch_preprocess(movies: list) -> list[tuple[int, str]]:
        """
        Preprocess multiple media items in batch.

        Returns:
            List of (media_id, preprocessed_text) tuples
        """
        results = []

        for movie in movies:
            if movie is None:
                logger.warning("Skipping None media item in batch preprocessing")
                continue

            try:
                text = TextPreprocessor.preprocess_movie(movie)
                if TextPreprocessor.validate_text(text):
                    results.append((movie.id, text))
            except Exception as e:
                title = getattr(movie, "title", "unknown")
                movie_id = getattr(movie, "id", "unknown")
                logger.warning(
                    f"Failed to preprocess media {movie_id} ('{title}'): {e}",
                    exc_info=True,
                )

        return results
