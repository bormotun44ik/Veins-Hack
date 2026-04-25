#!/usr/bin/env python3
"""
prewarm_cache.py — прогревает SQLite llm_cache перед демо.

Стратегия: для каждого person из people проходит:
  1. GET /insights/{id}       → кэшируется INSIGHT_SYSTEM prompt через Opus
  2. POST /action/recognition → кэшируется recognition через Sonnet

После прогона клик на ноде в UI отдаёт insight из кэша (<50ms), а не дёргает ShadoClaw.

Usage:
    python scripts/prewarm_cache.py                  # all people
    python scripts/prewarm_cache.py ivan maria       # selected people
    BASE=http://localhost:8000 python scripts/prewarm_cache.py
"""

import os
import sys
import time
import sqlite3
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError


BASE = os.environ.get("BASE", "http://127.0.0.1:8000")
ROOT = Path(__file__).parent.parent
DB_PATH = os.environ.get("DATABASE_PATH", str(ROOT / "db" / "veins.db"))


def hit(url: str, method: str = "GET", timeout: int = 30, retries: int = 3, backoff: int = 8) -> tuple[int, str]:
    """HTTP call with retry on 503/529 (Anthropic overloaded)."""
    for attempt in range(retries):
        req = Request(url, method=method)
        try:
            with urlopen(req, timeout=timeout) as resp:
                return resp.status, resp.read().decode("utf-8", errors="replace")
        except HTTPError as e:
            body = e.read().decode("utf-8", errors="replace")
            # Retry on transient upstream errors
            if e.code in (503, 529) and attempt < retries - 1:
                wait = backoff * (attempt + 1)
                print(f"    ⏳ retry in {wait}s (HTTP {e.code} — Anthropic flaky)")
                time.sleep(wait)
                continue
            return e.code, body
        except URLError as e:
            return 0, f"URLError: {e.reason}"
    return 0, "max retries exhausted"


def list_people() -> list[str]:
    if not Path(DB_PATH).exists():
        print(f"⚠ DB not found at {DB_PATH} — seed first")
        sys.exit(1)
    conn = sqlite3.connect(DB_PATH)
    rows = conn.execute("SELECT id FROM people ORDER BY id").fetchall()
    conn.close()
    return [r[0] for r in rows]


def cache_stats() -> int:
    if not Path(DB_PATH).exists():
        return 0
    conn = sqlite3.connect(DB_PATH)
    n = conn.execute("SELECT COUNT(*) FROM llm_cache").fetchone()[0]
    conn.close()
    return n


def main() -> int:
    targets = sys.argv[1:] if len(sys.argv) > 1 else list_people()
    if not targets:
        print("No people to warm — is DB seeded?")
        return 1

    print(f"🔥 Prewarming cache for {len(targets)} people via {BASE}")
    print(f"   DB: {DB_PATH}")
    print(f"   Starting cache size: {cache_stats()} entries")
    print()

    for pid in targets:
        t0 = time.time()
        status, body = hit(f"{BASE}/insights/{pid}", timeout=60)
        dt = time.time() - t0
        if status == 200:
            print(f"  ✅ /insights/{pid}              ({dt:.1f}s)")
        else:
            print(f"  ❌ /insights/{pid} → HTTP {status}  body[:120]: {body[:120]}")
            continue

        t0 = time.time()
        status, body = hit(f"{BASE}/action/recognition/{pid}", method="POST", timeout=60)
        dt = time.time() - t0
        if status == 200:
            print(f"  ✅ /action/recognition/{pid}    ({dt:.1f}s)")
        else:
            print(f"  ❌ /action/recognition/{pid} → HTTP {status}  body[:120]: {body[:120]}")

    # Warm dashboard endpoint — это прогревает primary_reason cache
    # (хотя сейчас primary_reason heuristic, не LLM, но зато готовый ответ кешируется
    # на случай что Agent I делает polling каждые 10 сек)
    print()
    t0 = time.time()
    status, body = hit(f"{BASE}/dashboard", timeout=30)
    dt = time.time() - t0
    if status == 200:
        print(f"  ✅ /dashboard                  ({dt:.1f}s)")
    else:
        print(f"  ❌ /dashboard → HTTP {status}  body[:120]: {body[:120]}")

    print()
    print(f"✅ Done. Final cache size: {cache_stats()} entries")
    print(f"   Клики в UI теперь будут мгновенные (<50ms из кэша).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
