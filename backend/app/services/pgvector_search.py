"""
pgvector-based vector search service for semantic movie/TV search.

Replaces FAISS with PostgreSQL pgvector extension using cosine similarity
and a pre-built HNSW index for fast approximate nearest-neighbor search.
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

    Uses the `media.embedding` VECTOR(768) column and the HNSW cosine index
    (`idx_media_embedding_hnsw`) added by the v2 migration.

    The public interface mirrors VectorSearchService so the retrieval engine
    needs only minimal changes.
    """

    def __init__(self, db: Session, dimension: int | None = None) -> None:
        """
        Args:
            db: SQLAlchemy session (injected per-request)
            dimension: Embedding dimension (default: from settings)
        """
        self.db = db
        self.dimension = dimension or settings.EMBEDDING_DIMENSION

        # Populated lazily from DB for media_type pre-filtering
        self._type_map: dict[int, str] = {}

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
            SELECT id,
                   1 - (embedding <=> :vec ::vector) AS similarity
            FROM   media
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
        Return all media IDs of a given type directly from the DB.
        Uses a simple index scan — fast for <10k rows.
        """
        sql = text("SELECT id FROM media WHERE media_type = :mt AND embedding IS NOT NULL")
        rows = self.db.execute(sql, {"mt": media_type}).fetchall()
        return {int(row[0]) for row in rows}

    # ------------------------------------------------------------------
    # Compat stubs (retrieval engine reads these)
    # ------------------------------------------------------------------

    @property
    def size(self) -> int:
        """Number of indexed vectors in DB."""
        row = self.db.execute(
            text("SELECT COUNT(*) FROM media WHERE embedding IS NOT NULL")
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
