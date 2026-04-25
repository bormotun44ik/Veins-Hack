import asyncio
import concurrent.futures
import json
import logging
import sqlite3

import numpy as np

from app.rag.embedder import embed_text

logger = logging.getLogger(__name__)


def _cosine(a: np.ndarray, b: np.ndarray) -> float:
    na = np.linalg.norm(a)
    nb = np.linalg.norm(b)
    if na == 0 or nb == 0:
        return 0.0
    return float(np.dot(a, b) / (na * nb))


def get_relevant_chunks(
    person_id: str,
    conn: sqlite3.Connection,
    top_k: int = 8,
    query: str = "burnout signals firefighting isolation",
) -> list[dict]:
    """Sync wrapper for use from context_v2.py.

    Computes query embedding via ThreadPoolExecutor (avoids event loop conflicts),
    then does linear cosine scan over stored embeddings.
    """
    try:
        rows = conn.execute("""
            SELECT chunk_period, text, embedding, source_event_ids
              FROM embeddings WHERE person_id = ?
        """, (person_id,)).fetchall()
        if not rows:
            return []

        # Compute query embedding in isolated thread (safe from any async context)
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as ex:
            query_vec = ex.submit(asyncio.run, embed_text(query)).result()

        if query_vec.sum() == 0:
            return []

        scored = []
        for period, text, blob, src_ids in rows:
            vec = np.frombuffer(blob, dtype=np.float32).copy()  # copy: frombuffer is read-only
            score = _cosine(query_vec, vec)
            scored.append({
                "period": period,
                "text": text,
                "type": "weekly_summary",
                "relevance": round(score, 3),
                "source_event_ids": src_ids,
            })

        scored.sort(key=lambda x: -x["relevance"])
        return scored[:top_k]
    except Exception as e:
        logger.error(f"get_relevant_chunks failed: {e}")
        return []
