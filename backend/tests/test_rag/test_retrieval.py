"""Happy-path test for RAG retrieval pipeline."""
import json
import sqlite3
import numpy as np
import pytest

from app.rag.index import init_embeddings_schema
from app.rag.retrieval import get_relevant_chunks, _cosine


def _make_db():
    conn = sqlite3.connect(":memory:")
    init_embeddings_schema(conn)
    return conn


def test_cosine_identical():
    a = np.array([1.0, 0.0, 0.0], dtype=np.float32)
    assert _cosine(a, a) == pytest.approx(1.0)


def test_cosine_zeros():
    z = np.zeros(3, dtype=np.float32)
    a = np.array([1.0, 0.0, 0.0], dtype=np.float32)
    assert _cosine(z, a) == 0.0
    assert _cosine(a, z) == 0.0


def test_get_relevant_chunks_empty_db():
    conn = _make_db()
    result = get_relevant_chunks("ivan", conn, top_k=8)
    assert result == []


def test_get_relevant_chunks_returns_rows():
    """Insert a fake embedding and verify retrieval returns it."""
    conn = _make_db()

    # Insert a pre-computed embedding (dim=4096, all 0.5 — non-zero)
    vec = np.full(4096, 0.5, dtype=np.float32)
    conn.execute("""
        INSERT INTO embeddings (person_id, chunk_kind, chunk_period, text, embedding,
                                source_event_ids, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, ("ivan", "weekly_summary", "2026-W14",
          "Ivan: 5 night commits, 3 fix/revert, no co-authors",
          vec.tobytes(), json.dumps([1, 2, 3]), "2026-04-25T00:00:00"))
    conn.commit()

    # Monkeypatch embed_text to return same vector (avoid real OpenRouter call)
    import app.rag.retrieval as retrieval_mod

    original_embed = retrieval_mod.embed_text

    async def fake_embed(text, timeout=30):
        return vec.copy()

    retrieval_mod.embed_text = fake_embed
    try:
        result = get_relevant_chunks("ivan", conn, top_k=8)
        assert len(result) == 1
        assert result[0]["period"] == "2026-W14"
        assert result[0]["relevance"] == pytest.approx(1.0, abs=0.001)
        assert "Ivan" in result[0]["text"]
    finally:
        retrieval_mod.embed_text = original_embed


def test_get_relevant_chunks_top_k():
    """Returns at most top_k results."""
    conn = _make_db()
    # Insert 5 chunks
    for i in range(5):
        vec = np.random.rand(4096).astype(np.float32)
        conn.execute("""
            INSERT INTO embeddings (person_id, chunk_kind, chunk_period, text, embedding,
                                    source_event_ids, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, ("ivan", "weekly_summary", f"2026-W{10+i}", f"Week {i} summary",
              vec.tobytes(), "[]", "2026-04-25T00:00:00"))
    conn.commit()

    import app.rag.retrieval as retrieval_mod

    async def fake_embed(text, timeout=30):
        return np.ones(4096, dtype=np.float32)

    retrieval_mod.embed_text = fake_embed
    try:
        result = get_relevant_chunks("ivan", conn, top_k=3)
        assert len(result) <= 3
    finally:
        retrieval_mod.embed_text = fake_embed.__wrapped__ if hasattr(fake_embed, '__wrapped__') else fake_embed
