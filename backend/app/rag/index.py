import asyncio
import json
import logging
import sqlite3
from collections import defaultdict
from datetime import datetime
from typing import Any

import numpy as np

from app.rag.embedder import embed_text
from app.rag.summarizer import summarize_chunk

logger = logging.getLogger(__name__)


def init_embeddings_schema(conn: sqlite3.Connection) -> None:
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS embeddings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            person_id TEXT NOT NULL,
            chunk_kind TEXT NOT NULL,
            chunk_period TEXT,
            text TEXT NOT NULL,
            embedding BLOB NOT NULL,
            source_event_ids TEXT,
            created_at TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_emb_person ON embeddings(person_id);
    """)
    conn.commit()


def _week_iso(ts: str) -> str:
    """ISO 8601 timestamp → '2026-W14' format."""
    try:
        dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
        y, w, _ = dt.isocalendar()
        return f"{y}-W{w:02d}"
    except Exception:
        return "unknown"


_INDEX_BUILDING = False  # guard against parallel calls


async def build_index(conn: sqlite3.Connection) -> int:
    """Group events by person × week → summarize → embed → store. Returns count."""
    global _INDEX_BUILDING
    if _INDEX_BUILDING:
        logger.warning("build_index already running, skipping duplicate call")
        return 0
    _INDEX_BUILDING = True
    try:
        return await _build_index_inner(conn)
    finally:
        _INDEX_BUILDING = False


async def _build_index_inner(conn: sqlite3.Connection) -> int:
    init_embeddings_schema(conn)

    existing = conn.execute("SELECT COUNT(*) FROM embeddings").fetchone()[0]
    if existing > 0:
        logger.info(f"Embeddings index already has {existing} chunks, skipping rebuild")
        return existing

    rows = conn.execute("""
        SELECT id, person_id, type, timestamp, payload_json
          FROM events
         ORDER BY person_id, timestamp ASC
    """).fetchall()

    chunks: dict[tuple, list] = defaultdict(list)
    for eid, pid, etype, ts, payload in rows:
        week = _week_iso(ts)
        try:
            p = json.loads(payload) if payload else {}
        except Exception:
            p = {}
        chunks[(pid, week)].append({
            "id": eid, "type": etype, "timestamp": ts, "payload": p,
        })

    count = 0
    for (pid, week), evs in chunks.items():
        if len(evs) < 2:
            continue  # skip trivial chunks

        summary = await summarize_chunk(pid, week, evs)
        if not summary:
            continue

        vec = await embed_text(summary)
        if vec.sum() == 0:
            logger.warning(f"empty embedding for {pid}/{week}")
            continue

        conn.execute("""
            INSERT INTO embeddings
                   (person_id, chunk_kind, chunk_period, text, embedding,
                    source_event_ids, created_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            pid, "weekly_summary", week, summary,
            vec.tobytes(),
            json.dumps([e["id"] for e in evs]),
            datetime.utcnow().isoformat(),
        ))
        count += 1

    conn.commit()
    logger.info(f"Built {count} embedding chunks")
    return count
