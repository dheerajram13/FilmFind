"""
Full data pipeline job — runs as a scheduled background task.

Stages (in order):
  1. ingest_media   — fetch new movies + TV shows from TMDB, upsert into DB
  2. generate_embeddings — generate 768-dim vectors for rows that lack them
  3. build_index    — rebuild FAISS HNSW index from all embeddings
  4. enrich_films   — LLM narrative enrichment (narrative_dna, themes, tone)
  5. score_films    — generate mood/context/craving score matrices (60-sec mode)

Each stage runs as a subprocess so failures are isolated and logs are
captured cleanly.  If a stage fails, subsequent stages are skipped and the
error is logged — the next scheduled run will pick up where it left off
because all scripts are idempotent.
"""

import subprocess
import sys
from pathlib import Path

from app.utils.logger import get_logger

logger = get_logger(__name__)

_SCRIPTS_DIR = Path(__file__).parent.parent.parent / "scripts"

_STAGES = [
    ("ingest",   _SCRIPTS_DIR / "ingest" / "ingest_media.py"),
    ("embed",    _SCRIPTS_DIR / "ml" / "generate_embeddings.py"),
    ("index",    _SCRIPTS_DIR / "ml" / "build_index.py"),
    ("enrich",   _SCRIPTS_DIR / "enrich" / "enrich_films.py"),
    ("score",    _SCRIPTS_DIR / "ml" / "score_films.py"),
]


def run_pipeline() -> dict:
    """
    Run the full ingest → embed → index → enrich → score pipeline.

    Returns a summary dict with per-stage status.
    """
    results: dict[str, str] = {}
    logger.info("Pipeline job started")

    for name, script in _STAGES:
        if not script.exists():
            logger.warning(f"Pipeline stage '{name}': script not found at {script}, skipping")
            results[name] = "skipped (script missing)"
            continue

        logger.info(f"Pipeline stage '{name}': running {script.name}")
        try:
            proc = subprocess.run(
                [sys.executable, str(script)],
                capture_output=True,
                text=True,
                timeout=3600,  # 1-hour hard cap per stage
            )
            if proc.returncode == 0:
                logger.info(f"Pipeline stage '{name}': completed OK")
                results[name] = "ok"
            else:
                logger.error(
                    f"Pipeline stage '{name}': exited {proc.returncode}\n"
                    f"stderr: {proc.stderr[-2000:]}"
                )
                results[name] = f"failed (exit {proc.returncode})"
                # Stop the chain — later stages depend on earlier ones
                break
        except subprocess.TimeoutExpired:
            logger.error(f"Pipeline stage '{name}': timed out after 1 hour")
            results[name] = "failed (timeout)"
            break
        except Exception as exc:
            logger.error(f"Pipeline stage '{name}': unexpected error: {exc}")
            results[name] = f"failed ({exc})"
            break

    logger.info(f"Pipeline job finished: {results}")
    return results
