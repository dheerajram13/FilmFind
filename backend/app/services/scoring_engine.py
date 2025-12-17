"""
Multi-Signal Scoring Engine - Composite ranking with weighted signals.

This module combines multiple ranking signals to produce final scores:
1. Extract individual signals from candidates
2. Normalize each signal to [0, 1]
3. Apply configurable weights
4. Compute weighted composite scores
5. Rank candidates by final score

Design Patterns:
- Strategy Pattern: Different scoring strategies for different query types
- Facade Pattern: Simple interface to complex multi-signal scoring
- Dependency Injection: Signal extractors injected for testability
"""

from datetime import UTC, datetime
import logging
import math
from typing import Any

from app.schemas.query import ParsedQuery
from app.services.signal_extractors import SignalExtractor, SignalExtractorFactory


logger = logging.getLogger(__name__)


# Query pattern keywords for adaptive strategy
TRENDING_KEYWORDS = frozenset(["trending", "popular", "most watched"])
RECENT_KEYWORDS = frozenset(["new", "recent", "latest", "2024", "2025"])
QUALITY_KEYWORDS = frozenset(["best", "top rated", "critically acclaimed", "masterpiece"])


class ScoringWeights:
    """
    Configuration for signal weights in composite scoring.

    Weights should sum to 1.0 for interpretability, but this
    is not enforced to allow for flexible scoring strategies.
    """

    def __init__(
        self,
        semantic_similarity: float = 0.5,
        genre_keyword_match: float = 0.2,
        popularity: float = 0.1,
        rating_quality: float = 0.1,
        recency: float = 0.1,
    ) -> None:
        """
        Initialize scoring weights.

        Default weights prioritize semantic similarity while
        considering genre match, popularity, ratings, and recency.

        Args:
            semantic_similarity: Weight for semantic vector similarity (default: 0.5)
            genre_keyword_match: Weight for genre/keyword matches (default: 0.2)
            popularity: Weight for popularity score (default: 0.1)
            rating_quality: Weight for rating quality (default: 0.1)
            recency: Weight for recency boost (default: 0.1)
        """
        self.semantic_similarity = semantic_similarity
        self.genre_keyword_match = genre_keyword_match
        self.popularity = popularity
        self.rating_quality = rating_quality
        self.recency = recency

    def get_total_weight(self) -> float:
        """Calculate total weight (should ideally be 1.0)."""
        return (
            self.semantic_similarity
            + self.genre_keyword_match
            + self.popularity
            + self.rating_quality
            + self.recency
        )

    def normalize(self) -> "ScoringWeights":
        """
        Return normalized weights that sum to 1.0.

        Returns:
            New ScoringWeights instance with normalized weights
        """
        total = self.get_total_weight()
        if total == 0:
            # Avoid division by zero
            return ScoringWeights()

        return ScoringWeights(
            semantic_similarity=self.semantic_similarity / total,
            genre_keyword_match=self.genre_keyword_match / total,
            popularity=self.popularity / total,
            rating_quality=self.rating_quality / total,
            recency=self.recency / total,
        )

    def to_dict(self) -> dict[str, float]:
        """Convert weights to dictionary."""
        return {
            "semantic_similarity": self.semantic_similarity,
            "genre_keyword_match": self.genre_keyword_match,
            "popularity": self.popularity,
            "rating_quality": self.rating_quality,
            "recency": self.recency,
        }

    @classmethod
    def from_dict(cls, weights_dict: dict[str, float]) -> "ScoringWeights":
        """Create ScoringWeights from dictionary."""
        return cls(
            semantic_similarity=weights_dict.get("semantic_similarity", 0.5),
            genre_keyword_match=weights_dict.get("genre_keyword_match", 0.2),
            popularity=weights_dict.get("popularity", 0.1),
            rating_quality=weights_dict.get("rating_quality", 0.1),
            recency=weights_dict.get("recency", 0.1),
        )

    @classmethod
    def semantic_focused(cls) -> "ScoringWeights":
        """
        Weights heavily focused on semantic similarity.

        Use when semantic understanding is most important.
        """
        return cls(
            semantic_similarity=0.7,
            genre_keyword_match=0.15,
            popularity=0.05,
            rating_quality=0.05,
            recency=0.05,
        )

    @classmethod
    def popularity_focused(cls) -> "ScoringWeights":
        """
        Weights focused on popular and highly-rated content.

        Use for "trending" or "most popular" queries.
        """
        return cls(
            semantic_similarity=0.3,
            genre_keyword_match=0.1,
            popularity=0.3,
            rating_quality=0.2,
            recency=0.1,
        )

    @classmethod
    def discovery_focused(cls) -> "ScoringWeights":
        """
        Weights focused on discovering recent quality content.

        Use for "new releases" or "recent movies" queries.
        """
        return cls(
            semantic_similarity=0.3,
            genre_keyword_match=0.2,
            popularity=0.1,
            rating_quality=0.15,
            recency=0.25,
        )

    @classmethod
    def quality_focused(cls) -> "ScoringWeights":
        """
        Weights focused on high-quality, well-rated content.

        Use for "best movies" or "critically acclaimed" queries.
        """
        return cls(
            semantic_similarity=0.35,
            genre_keyword_match=0.15,
            popularity=0.1,
            rating_quality=0.35,
            recency=0.05,
        )


class MultiSignalScoringEngine:
    """
    Multi-signal scoring engine for ranking movie candidates.

    Combines multiple signals with configurable weights to produce
    final composite scores for ranking.

    Example:
        ```python
        engine = MultiSignalScoringEngine()
        scored_candidates = engine.score_candidates(
            candidates=retrieval_results,
            parsed_query=parsed_query,
            weights=ScoringWeights.semantic_focused()
        )
        # Returns candidates with 'final_score' and 'signal_scores'
        ```
    """

    def __init__(self, extractors: dict[str, SignalExtractor] | None = None) -> None:
        """
        Initialize scoring engine.

        Args:
            extractors: Dictionary of signal extractors (optional, uses factory if None)
        """
        self.extractors = extractors or SignalExtractorFactory.create_all_extractors()

    def score_candidates(
        self,
        candidates: list[dict[str, Any]],
        parsed_query: ParsedQuery,
        weights: ScoringWeights | None = None,
        include_signal_breakdown: bool = True,
    ) -> list[dict[str, Any]]:
        """
        Score all candidates using multi-signal scoring.

        Args:
            candidates: List of movie candidates from retrieval
            parsed_query: Parsed user query with intent
            weights: Scoring weights (default: ScoringWeights())
            include_signal_breakdown: Include individual signal scores in output

        Returns:
            List of candidates with 'final_score' (and optionally 'signal_scores')
            sorted by final score in descending order
        """
        if not candidates:
            return []

        weights = weights or ScoringWeights()

        # Normalize weights to sum to 1.0
        weights = weights.normalize()

        logger.info("Scoring %d candidates with weights: %s", len(candidates), weights.to_dict())

        # Prepare context for extractors
        context = self._prepare_context(candidates)

        # Score each candidate
        scored_candidates = []
        for candidate in candidates:
            try:
                scored_candidate = self._score_single_candidate(
                    movie=candidate,
                    parsed_query=parsed_query,
                    weights=weights,
                    context=context,
                    include_breakdown=include_signal_breakdown,
                )
                scored_candidates.append(scored_candidate)
            except Exception as e:
                logger.error(
                    "Error scoring candidate %s: %s",
                    candidate.get("title", "unknown"),
                    e,
                    exc_info=True,
                )
                # Keep candidate but with low score
                candidate["final_score"] = 0.0
                if include_signal_breakdown:
                    candidate["signal_scores"] = {}
                scored_candidates.append(candidate)

        # Sort by final score (descending)
        scored_candidates.sort(key=lambda x: x.get("final_score", 0.0), reverse=True)

        logger.info(
            "Scoring complete. Top score: %.3f, Bottom score: %.3f",
            scored_candidates[0].get("final_score", 0.0),
            scored_candidates[-1].get("final_score", 0.0),
        )

        return scored_candidates

    def _score_single_candidate(
        self,
        movie: dict[str, Any],
        parsed_query: ParsedQuery,
        weights: ScoringWeights,
        context: dict[str, Any],
        include_breakdown: bool,
    ) -> dict[str, Any]:
        """
        Score a single candidate using all signals.

        Args:
            movie: Movie candidate
            parsed_query: Parsed query
            weights: Normalized scoring weights
            context: Context for extractors
            include_breakdown: Include individual signal scores

        Returns:
            Movie with 'final_score' (and optionally 'signal_scores')
        """
        signal_scores = {}

        # Extract each signal
        signal_scores["semantic_similarity"] = self.extractors["semantic_similarity"].extract(
            movie, parsed_query, context
        )

        signal_scores["genre_keyword_match"] = self.extractors["genre_keyword_match"].extract(
            movie, parsed_query, context
        )

        signal_scores["popularity"] = self.extractors["popularity"].extract(
            movie, parsed_query, context
        )

        signal_scores["rating_quality"] = self.extractors["rating_quality"].extract(
            movie, parsed_query, context
        )

        signal_scores["recency"] = self.extractors["recency"].extract(movie, parsed_query, context)

        # Calculate weighted composite score
        final_score = (
            weights.semantic_similarity * signal_scores["semantic_similarity"]
            + weights.genre_keyword_match * signal_scores["genre_keyword_match"]
            + weights.popularity * signal_scores["popularity"]
            + weights.rating_quality * signal_scores["rating_quality"]
            + weights.recency * signal_scores["recency"]
        )

        # Add scores to movie
        movie["final_score"] = final_score
        if include_breakdown:
            movie["signal_scores"] = signal_scores

        return movie

    def _prepare_context(self, candidates: list[dict[str, Any]]) -> dict[str, Any]:
        """
        Prepare context for signal extractors.

        Computes statistics across all candidates that may be useful
        for normalization (e.g., max popularity).

        Args:
            candidates: List of all candidates

        Returns:
            Context dictionary with statistics
        """
        context = {"current_year": datetime.now(UTC).year}

        # Calculate max log popularity for normalization
        if candidates:
            max_popularity = max((c.get("popularity", 0.0) for c in candidates), default=0.0)
            if max_popularity > 0:
                context["max_log_popularity"] = math.log(max_popularity + 1)

        return context


class AdaptiveScoringStrategy:
    """
    Adaptive scoring that selects weights based on query type.

    Analyzes the parsed query to determine the best scoring strategy.
    """

    @staticmethod
    def select_weights(parsed_query: ParsedQuery) -> ScoringWeights:
        """
        Select appropriate weights based on query characteristics.

        Args:
            parsed_query: Parsed user query

        Returns:
            Appropriate ScoringWeights for the query type
        """
        intent = parsed_query.intent
        query_lower = parsed_query.raw_query.lower()

        # Check for specific query patterns (ordered by priority)
        # Using frozenset for O(1) lookup performance
        if any(keyword in query_lower for keyword in TRENDING_KEYWORDS):
            logger.info("Using popularity-focused weights for trending query")
            return ScoringWeights.popularity_focused()

        if any(keyword in query_lower for keyword in RECENT_KEYWORDS):
            logger.info("Using discovery-focused weights for recent content query")
            return ScoringWeights.discovery_focused()

        if any(keyword in query_lower for keyword in QUALITY_KEYWORDS):
            logger.info("Using quality-focused weights for high-quality query")
            return ScoringWeights.quality_focused()

        # Check if reference titles are provided
        if intent.reference_titles:
            logger.info("Using semantic-focused weights for similarity query")
            return ScoringWeights.semantic_focused()

        # Default: balanced weights
        logger.info("Using default balanced weights")
        return ScoringWeights()
