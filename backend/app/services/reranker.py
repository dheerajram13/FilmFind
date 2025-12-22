"""
LLM-based Re-Ranking Service - Module 2.4

This module takes top candidates from the multi-signal scoring engine
and uses an LLM to re-rank them based on deeper semantic understanding,
generating explanations for why each movie matches the user's query.

Architecture:
- Uses LLM (Groq/Ollama) to analyze query intent and candidate relevance
- Generates structured JSON output with rankings and explanations
- Applies conservative re-ranking (respects initial scoring while refining order)
- Includes caching to stay within free tier rate limits

Design Patterns:
- Strategy Pattern: Different prompt strategies for different query types
- Facade Pattern: Simple interface to complex LLM re-ranking
- Template Method: Prompt template composition
"""

from datetime import UTC, datetime
import hashlib
import json
from typing import Any

from loguru import logger

from app.schemas.query import ParsedQuery
from app.services.exceptions import LLMClientError, LLMRateLimitError
from app.services.llm_client import LLMClient


class PromptTemplate:
    """
    Prompt templates for re-ranking movies.

    Uses few-shot learning with examples to guide the LLM
    towards consistent, high-quality responses.
    """

    SYSTEM_PROMPT = """You are an expert movie recommendation system. \
Your task is to analyze a user's query and rank movies based on how \
well they match the user's intent, considering themes, tone, emotions, \
and constraints.

You will be given:
1. The user's original query
2. Parsed query intent (themes, tones, emotions, reference titles, constraints)
3. A list of candidate movies with metadata (plot, genres, cast, keywords, ratings)

Your job:
1. Understand the user's true intent and preferences
2. Rank the candidates by relevance (best matches first)
3. For each movie, generate a concise explanation of why it matches
4. Be honest - if a movie is a poor match, say so clearly

Guidelines:
- Focus on thematic similarity, emotional tone, and style
- Consider both desired and undesired elements
- Respect hard constraints (language, year, rating)
- Value quality and ratings, but prioritize thematic fit
- Keep explanations concise (1-2 sentences)
- Be specific about what makes each movie relevant"""

    @staticmethod
    def build_reranking_prompt(
        user_query: str,
        parsed_query: ParsedQuery,
        candidates: list[dict[str, Any]],
        top_k: int = 10,
    ) -> str:
        """
        Build prompt for re-ranking candidates.

        Args:
            user_query: Original user query
            parsed_query: Parsed query intent
            candidates: List of candidate movies with metadata
            top_k: Number of top results to return

        Returns:
            Formatted prompt string
        """
        # Build query context
        query_context = PromptTemplate._format_query_context(user_query, parsed_query)

        # Build candidates section
        candidates_section = PromptTemplate._format_candidates(candidates)

        # Build instructions
        instructions = f"""Based on the query and candidates above, please:

1. Rank the top {top_k} most relevant movies
2. For each ranked movie, provide a concise explanation (1-2 sentences) of why it matches the query
3. Consider themes, tone, emotions, and all constraints from the query

Respond with ONLY a valid JSON object in this exact format:
{{
  "ranked_movies": [
    {{
      "movie_index": 0,
      "relevance_score": 0.95,
      "explanation": "Perfect match because..."
    }},
    ...
  ],
  "reasoning": "Brief summary of ranking approach"
}}

Important:
- movie_index: The index from the candidates list above (0-based)
- relevance_score: Your assessment of match quality (0-1 scale)
- explanation: Specific reason why this movie matches the query
- Include ONLY the top {top_k} most relevant movies
- Sort by relevance (best matches first)"""

        return f"{query_context}\n\n{candidates_section}\n\n{instructions}"

    @staticmethod
    def _format_query_context(user_query: str, parsed_query: ParsedQuery) -> str:
        """Format the query context section."""
        context_parts = [
            "=== USER QUERY ===",
            f'"{user_query}"',
            "",
            "=== PARSED INTENT ===",
        ]

        # Access intent fields
        intent = parsed_query.intent

        if intent.reference_titles:
            context_parts.append(f"Reference Movies: {', '.join(intent.reference_titles)}")

        if parsed_query.constraints.genres:
            context_parts.append(f"Genres: {', '.join(parsed_query.constraints.genres)}")

        if intent.themes:
            context_parts.append(f"Themes: {', '.join(intent.themes)}")

        if intent.tones:
            tone_names = [tone.value if hasattr(tone, 'value') else str(tone) for tone in intent.tones]
            context_parts.append(f"Desired Tones: {', '.join(tone_names)}")

        if intent.emotions:
            emotion_names = [emotion.value if hasattr(emotion, 'value') else str(emotion) for emotion in intent.emotions]
            context_parts.append(f"Desired Emotions: {', '.join(emotion_names)}")

        if intent.undesired_themes:
            context_parts.append(f"Avoid Themes: {', '.join(intent.undesired_themes)}")

        if intent.undesired_tones:
            undesired_tone_names = [tone.value if hasattr(tone, 'value') else str(tone) for tone in intent.undesired_tones]
            context_parts.append(f"Avoid Tones: {', '.join(undesired_tone_names)}")

        # Add constraints
        constraints = []
        if parsed_query.constraints.year_min or parsed_query.constraints.year_max:
            year_min = parsed_query.constraints.year_min or "any"
            year_max = parsed_query.constraints.year_max or "any"
            constraints.append(f"Years: {year_min}-{year_max}")

        if parsed_query.constraints.rating_min:
            constraints.append(f"Min Rating: {parsed_query.constraints.rating_min}/10")

        if parsed_query.constraints.languages:
            constraints.append(f"Languages: {', '.join(parsed_query.constraints.languages)}")

        if constraints:
            context_parts.append(f"Constraints: {', '.join(constraints)}")

        return "\n".join(context_parts)

    @staticmethod
    def _format_candidates(candidates: list[dict[str, Any]]) -> str:
        """Format candidates section for the prompt."""
        lines = ["=== CANDIDATE MOVIES ===", ""]

        for idx, movie in enumerate(candidates):
            # Extract key metadata
            title = movie.get("title", "Unknown")
            release_date = movie.get("release_date", "")
            year = release_date[:4] if release_date else "N/A"
            overview = movie.get("overview") or movie.get(
                "plot_summary", "No description available"
            )

            # Truncate long overviews
            if len(overview) > 300:
                overview = overview[:297] + "..."

            # Get genres
            genres = movie.get("genres", [])
            genre_names = [g.get("name") if isinstance(g, dict) else str(g) for g in genres]

            # Get keywords (if available)
            keywords = movie.get("keywords", [])
            keyword_names = [k.get("name") if isinstance(k, dict) else str(k) for k in keywords[:5]]

            # Get cast (if available)
            cast = movie.get("cast_members", [])
            cast_names = [c.get("name") if isinstance(c, dict) else str(c) for c in cast[:5]]

            # Get ratings
            rating = movie.get("vote_average", "N/A")
            popularity = movie.get("popularity", "N/A")

            # Get existing scores
            similarity = movie.get("similarity_score", "N/A")
            final_score = movie.get("final_score", "N/A")

            # Format movie entry
            lines.append(f"[{idx}] {title} ({year})")
            lines.append(f"    Plot: {overview}")
            if genre_names:
                lines.append(f"    Genres: {', '.join(genre_names)}")
            if keyword_names:
                lines.append(f"    Keywords: {', '.join(keyword_names)}")
            if cast_names:
                lines.append(f"    Cast: {', '.join(cast_names)}")
            lines.append(f"    Rating: {rating}/10, Popularity: {popularity}")
            lines.append(f"    Scores: Similarity={similarity:.3f}, Final={final_score:.3f}")
            lines.append("")

        return "\n".join(lines)


class ReRankingCache:
    """
    Simple in-memory cache for re-ranking results.

    Helps reduce LLM API calls by caching results for identical queries.
    Uses query hash as cache key.
    """

    def __init__(self, ttl_seconds: int = 3600) -> None:
        """
        Initialize cache.

        Args:
            ttl_seconds: Time-to-live for cache entries (default: 1 hour)
        """
        self._cache: dict[str, dict[str, Any]] = {}
        self._ttl_seconds = ttl_seconds

    def _generate_cache_key(
        self,
        user_query: str,
        candidate_ids: list[int],
        top_k: int,
    ) -> str:
        """Generate cache key from query and candidates."""
        # Create a deterministic string representation
        key_data = {
            "query": user_query.lower().strip(),
            "candidate_ids": sorted(candidate_ids),  # Sort for consistency
            "top_k": top_k,
        }
        key_str = json.dumps(key_data, sort_keys=True)
        return hashlib.sha256(key_str.encode()).hexdigest()

    def get(
        self,
        user_query: str,
        candidate_ids: list[int],
        top_k: int,
    ) -> dict[str, Any] | None:
        """Get cached result if available and not expired."""
        cache_key = self._generate_cache_key(user_query, candidate_ids, top_k)

        if cache_key not in self._cache:
            return None

        entry = self._cache[cache_key]
        timestamp = entry.get("timestamp", 0)

        # Check if expired
        age_seconds = datetime.now(UTC).timestamp() - timestamp
        if age_seconds > self._ttl_seconds:
            # Expired - remove from cache
            del self._cache[cache_key]
            return None

        logger.debug(f"Cache hit for re-ranking (age: {age_seconds:.1f}s)")
        return entry.get("result")

    def store(
        self,
        user_query: str,
        candidate_ids: list[int],
        top_k: int,
        result: dict[str, Any],
    ) -> None:
        """Store result in cache."""
        cache_key = self._generate_cache_key(user_query, candidate_ids, top_k)
        self._cache[cache_key] = {
            "result": result,
            "timestamp": datetime.now(UTC).timestamp(),
        }
        logger.debug(f"Cached re-ranking result (total entries: {len(self._cache)})")

    def clear(self) -> None:
        """Clear all cache entries."""
        self._cache.clear()
        logger.debug("Cleared re-ranking cache")


class LLMReRanker:
    """
    LLM-based re-ranking service.

    Takes scored candidates and uses LLM to refine rankings based on
    deeper semantic understanding of the query and candidates.
    """

    def __init__(
        self,
        llm_client: LLMClient | None = None,
        enable_cache: bool = True,
        cache_ttl_seconds: int = 3600,
    ) -> None:
        """
        Initialize re-ranker.

        Args:
            llm_client: LLM client (default: creates new Groq client)
            enable_cache: Whether to enable caching (default: True)
            cache_ttl_seconds: Cache TTL in seconds (default: 1 hour)
        """
        self._llm_client = llm_client or LLMClient()
        self._cache = ReRankingCache(ttl_seconds=cache_ttl_seconds) if enable_cache else None

    def rerank(
        self,
        candidates: list[dict[str, Any]],
        user_query: str,
        parsed_query: ParsedQuery,
        top_k: int = 10,
        temperature: float = 0.3,
        max_candidates: int = 30,
    ) -> list[dict[str, Any]]:
        """
        Re-rank candidates using LLM.

        Args:
            candidates: List of scored candidates from scoring engine
            user_query: Original user query
            parsed_query: Parsed query intent
            top_k: Number of top results to return
            temperature: LLM temperature (lower = more deterministic)
            max_candidates: Maximum candidates to send to LLM (to stay within token limits)

        Returns:
            Re-ranked list of candidates with 'match_explanation' field added

        Raises:
            LLMClientError: If LLM request fails
            LLMRateLimitError: If rate limit is exceeded
        """
        if not candidates:
            logger.warning("No candidates to re-rank")
            return []

        # Limit candidates to stay within token limits
        candidates_to_rerank = candidates[:max_candidates]

        logger.info(
            f"Re-ranking {len(candidates_to_rerank)} candidates (top_k={top_k}, "
            f"temperature={temperature})"
        )

        # Check cache
        if self._cache:
            candidate_ids = [c.get("id") or c.get("tmdb_id", 0) for c in candidates_to_rerank]
            cached_result = self._cache.get(user_query, candidate_ids, top_k)
            if cached_result:
                logger.info("Using cached re-ranking result")
                return cached_result

        # Build prompt
        prompt = PromptTemplate.build_reranking_prompt(
            user_query=user_query,
            parsed_query=parsed_query,
            candidates=candidates_to_rerank,
            top_k=top_k,
        )

        # Call LLM
        try:
            response = self._llm_client.generate_json(
                prompt=prompt,
                system_prompt=PromptTemplate.SYSTEM_PROMPT,
                temperature=temperature,
                max_tokens=2048,
            )

            # Parse and apply rankings
            reranked = self._apply_rankings(candidates_to_rerank, response, top_k)

            # Cache result
            if self._cache:
                candidate_ids = [c.get("id") or c.get("tmdb_id", 0) for c in candidates_to_rerank]
                self._cache.store(user_query, candidate_ids, top_k, reranked)

            logger.info(f"Successfully re-ranked {len(reranked)} candidates")
            return reranked

        except LLMRateLimitError:
            logger.warning("Rate limit hit - returning original scoring order")
            # Fallback: return top_k from original scoring
            return candidates[:top_k]

        except LLMClientError as e:
            logger.error(f"LLM re-ranking failed: {e}")
            # Fallback: return top_k from original scoring
            logger.info("Falling back to original scoring order")
            return candidates[:top_k]

    def _apply_rankings(
        self,
        candidates: list[dict[str, Any]],
        llm_response: dict[str, Any],
        top_k: int,
    ) -> list[dict[str, Any]]:
        """
        Apply LLM rankings to candidates.

        Args:
            candidates: Original candidate list
            llm_response: Parsed JSON response from LLM
            top_k: Number of results to return

        Returns:
            Re-ranked candidates with explanations
        """
        ranked_movies = llm_response.get("ranked_movies", [])

        if not ranked_movies:
            logger.warning("LLM returned empty rankings - using original order")
            return candidates[:top_k]

        # Apply rankings
        reranked = []
        for item in ranked_movies[:top_k]:
            idx = item.get("movie_index")

            # Validate index
            if idx is None or idx < 0 or idx >= len(candidates):
                logger.warning(f"Invalid movie index {idx} in LLM response - skipping")
                continue

            # Get candidate and enrich with LLM output
            candidate = candidates[idx].copy()
            candidate["match_explanation"] = item.get("explanation", "")
            candidate["llm_relevance_score"] = item.get("relevance_score", 0.5)

            reranked.append(candidate)

        # If we got fewer results than expected, log warning
        if len(reranked) < top_k:
            logger.warning(
                f"LLM returned {len(reranked)} valid results, expected {top_k}. "
                f"Filling remaining slots with original order."
            )

            # Add remaining candidates from original list (without explanations)
            reranked_indices = {item.get("movie_index") for item in ranked_movies}
            for idx, cand in enumerate(candidates):
                if len(reranked) >= top_k:
                    break
                if idx not in reranked_indices:
                    cand_copy = cand.copy()
                    cand_copy["match_explanation"] = "Additional match based on scoring signals"
                    cand_copy["llm_relevance_score"] = None
                    reranked.append(cand_copy)

        return reranked

    def clear_cache(self) -> None:
        """Clear the re-ranking cache."""
        if self._cache:
            self._cache.clear()


# Convenience function for simple usage
def rerank_candidates(
    candidates: list[dict[str, Any]],
    user_query: str,
    parsed_query: ParsedQuery,
    top_k: int = 10,
    llm_client: LLMClient | None = None,
) -> list[dict[str, Any]]:
    """
    Convenience function to re-rank candidates.

    Args:
        candidates: Scored candidates from scoring engine
        user_query: Original user query
        parsed_query: Parsed query intent
        top_k: Number of results to return
        llm_client: Optional LLM client (creates default if None)

    Returns:
        Re-ranked candidates with explanations
    """
    reranker = LLMReRanker(llm_client=llm_client)
    return reranker.rerank(
        candidates=candidates,
        user_query=user_query,
        parsed_query=parsed_query,
        top_k=top_k,
    )
