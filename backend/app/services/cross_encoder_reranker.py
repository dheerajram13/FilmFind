"""
Cross-encoder reranker using FlashRank-MiniLM-L12.

Chosen from benchmark results (NDCG@5=0.910, P@5=0.960, ~64ms/query).
Loaded once at module level — subsequent requests reuse the cached model.
"""
from typing import Any

from app.utils.logger import get_logger

logger = get_logger(__name__)

_ranker = None


def _get_ranker():
    global _ranker
    if _ranker is None:
        from flashrank import Ranker
        logger.info("Loading FlashRank-MiniLM-L12 reranker …")
        _ranker = Ranker(model_name="ms-marco-MiniLM-L-12-v2")
        logger.info("FlashRank-MiniLM-L12 loaded")
    return _ranker


class CrossEncoderReRanker:
    def rerank(
        self,
        candidates: list[dict[str, Any]],
        query: str,
        top_k: int,
    ) -> list[dict[str, Any]]:
        """Rerank candidates using FlashRank cross-encoder. Falls back to original order on failure."""
        if not candidates:
            return candidates

        try:
            from flashrank import RerankRequest

            passages = [
                {"id": i, "text": c.get("overview") or c.get("plot_summary") or ""}
                for i, c in enumerate(candidates)
            ]
            request = RerankRequest(query=query, passages=passages)
            results = _get_ranker().rerank(request)

            reranked = [candidates[r["id"]] for r in results[:top_k]]
            logger.info(f"Cross-encoder reranked {len(candidates)} → top {len(reranked)}")
            return reranked

        except Exception as exc:
            logger.warning(f"Cross-encoder rerank failed, using original order: {exc}")
            return candidates[:top_k]
