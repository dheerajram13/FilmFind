"""
pgvector-based vector search service for semantic movie/TV search.

Replaces FAISS with PostgreSQL pgvector extension using cosine similarity
and a pre-built HNSW index for fast approximate nearest-neighbor search.

Queries the media_embedding table (one-to-one with media) using the HNSW
cosine index (idx_media_embedding_hnsw). Returns media_id values that callers
then use to fetch Movie or TVShow rows — no join to media needed in this layer.
"""

import logging
from typing import Any

import numpy as np
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.config import settings


logger = logging.getLogger(__name__)


class PgVectorSearchService:
    """
    pgvector-based vector search. Drop-in replacement for VectorSearchService.

    Uses the `media_embedding.embedding` VECTOR(768) column and the HNSW cosine
    index (idx_media_embedding_hnsw) added by the v5 migration.

    The public interface mirrors VectorSearchService so the retrieval engine
    needs only minimal changes. Returns (media_id, similarity) pairs.
    """

    def __init__(self, db: Session, dimension: int | None = None) -> None:
        """
        Args:
            db: SQLAlchemy session (injected per-request)
            dimension: Embedding dimension (default: from settings)
        """
        self.db = db
        self.dimension = dimension or settings.EMBEDDING_DIMENSION

    # ------------------------------------------------------------------
    # Core search
    # ------------------------------------------------------------------

    def search(
        self,
        query_embedding: np.ndarray,
        k: int = 100,
        **_kwargs,
    ) -> list[tuple[int, float]]:
        """
        Return the top-k most similar media items using cosine distance.

        Args:
            query_embedding: 1-D or 2-D numpy array of shape (768,) or (1, 768)
            k: Number of nearest neighbours to return

        Returns:
            List of (media_id, cosine_similarity) sorted descending.
            Cosine similarity = 1 - cosine_distance  (range 0-1).
        """
        vec = query_embedding.flatten().astype(np.float32)

        # pgvector expects a Python list for the literal
        vec_literal = "[" + ",".join(f"{v:.8f}" for v in vec.tolist()) + "]"

        sql = text("""
            SELECT media_id,
                   1 - (embedding <=> :vec ::vector) AS similarity
            FROM   media_embedding
            WHERE  embedding IS NOT NULL
            ORDER  BY embedding <=> :vec ::vector
            LIMIT  :k
        """)

        rows = self.db.execute(sql, {"vec": vec_literal, "k": k}).fetchall()
        results = [(int(row[0]), float(row[1])) for row in rows]
        logger.debug(f"pgvector search returned {len(results)} candidates")
        return results

    # ------------------------------------------------------------------
    # Media-type pre-filter support (used by retrieval engine)
    # ------------------------------------------------------------------

    def get_ids_by_media_type(self, media_type: str) -> set[int]:
        """
        Return all media_ids for a given type that have embeddings.

        Joins media_embedding with movies or tv_shows to filter by type.
        Uses a simple index scan — fast for <10k rows.
        """
        if media_type == "movie":
            sql = text("""
                SELECT me.media_id
                FROM media_embedding me
                JOIN movies m ON m.media_id = me.media_id
                WHERE me.embedding IS NOT NULL
            """)
        else:
            sql = text("""
                SELECT me.media_id
                FROM media_embedding me
                JOIN tv_shows t ON t.media_id = me.media_id
                WHERE me.embedding IS NOT NULL
            """)
        rows = self.db.execute(sql).fetchall()
        return {int(row[0]) for row in rows}

    # ------------------------------------------------------------------
    # Compat stubs (retrieval engine reads these)
    # ------------------------------------------------------------------

    @property
    def size(self) -> int:
        """Number of indexed vectors in DB."""
        row = self.db.execute(
            text("SELECT COUNT(*) FROM media_embedding WHERE embedding IS NOT NULL")
        ).fetchone()
        return int(row[0]) if row else 0

    @property
    def is_trained(self) -> bool:
        return True  # pgvector index is always ready

    def get_index_info(self) -> dict[str, Any]:
        return {
            "backend": "pgvector",
            "dimension": self.dimension,
            "size": self.size,
        }
