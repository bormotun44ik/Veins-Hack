#!/usr/bin/env python3
"""Pre-compute embeddings index on cold start.

Usage:
    # from repo root (host machine):
    python scripts/build_embeddings.py

    # or inside backend container:
    docker exec <backend> python -m app.rag.index

Environment:
    DATABASE_PATH  path to SQLite db (default: db/veins.db relative to repo root)
"""
import asyncio
import os
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
DB_PATH = os.environ.get("DATABASE_PATH", str(ROOT / "db" / "veins.db"))


async def main():
    sys.path.insert(0, str(ROOT / "backend"))
    from app.rag.index import build_index

    conn = sqlite3.connect(DB_PATH)
    try:
        count = await build_index(conn)
        if count == 0:
            # Check if already populated (idempotent skip)
            existing = conn.execute("SELECT COUNT(*) FROM embeddings").fetchone()[0]
            if existing > 0:
                print(f"✅ Already has {existing} chunks. DB: {DB_PATH}")
            else:
                print("⚠️  Built 0 chunks — no events with ≥2 per week found.")
        else:
            print(f"✅ Built {count} embedding chunks. DB: {DB_PATH}")
    finally:
        conn.close()


if __name__ == "__main__":
    asyncio.run(main())
