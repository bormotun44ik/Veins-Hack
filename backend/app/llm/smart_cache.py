"""Smart cache with partial invalidation for /insights endpoint."""
import hashlib
import json
import sqlite3
from datetime import datetime, timezone
from typing import Any

SIGNALS_TO_TRACK = [
    "night_commits_ratio",
    "fix_revert_ratio",
    "pr_review_lag_hours",
    "bus_factor",
    "co_author_isolation",
    "weekend_activity",
    # commit_tone_delta excluded — cached static value
]

# Status boundaries — crossing 0.4 or 0.7 always invalidates cache even if delta < threshold
STATUS_BOUNDARIES = (0.4, 0.7)

TTL_HOURS = 24


def init_smart_cache(conn: sqlite3.Connection) -> None:
    """Create signal_snapshots table if not exists. Idempotent."""
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS signal_snapshots (
            person_id TEXT NOT NULL,
            signals_hash TEXT NOT NULL,
            signals_json TEXT NOT NULL,
            insight_response TEXT NOT NULL,
            model TEXT,
            created_at TEXT NOT NULL,
            PRIMARY KEY (person_id, signals_hash)
        );
        CREATE INDEX IF NOT EXISTS idx_snapshot_person
                               ON signal_snapshots(person_id);
    """)
    conn.commit()


def _bucketize(v: float, threshold: float) -> int:
    """Spec-aware bucketing.

    Within same zone (green/yellow/red) — buckets by threshold.
    On zone boundary — new bucket even if value is close.
    This prevents invalid cache hit when signal=0.39 → 0.41 (status flip).
    """
    if v < STATUS_BOUNDARIES[0]:
        zone = 0  # green
        local = v / threshold
    elif v < STATUS_BOUNDARIES[1]:
        zone = 1  # yellow
        local = (v - STATUS_BOUNDARIES[0]) / threshold
    else:
        zone = 2  # red
        local = (v - STATUS_BOUNDARIES[1]) / threshold
    return zone * 100 + int(local)


def signals_hash(signals: dict, threshold: float = 0.10) -> str:
    """Hash of bucketized signals — changes < threshold don't change hash.

    BUT: crossing status boundary (0.4 or 0.7) ALWAYS changes hash,
    even if delta < threshold — otherwise cache returns RED insight for YELLOW person.

    Examples:
      0.04 → 0,    0.13 → 1,   0.39 → 3      (green zone)
      0.41 → 100,  0.55 → 101  (yellow zone)
      0.78 → 200,  0.85 → 200  (red zone, same bucket within zone)
    """
    buckets = []
    for k in SIGNALS_TO_TRACK:
        v = float(signals.get(k, 0.0))
        bucket = _bucketize(v, threshold)
        buckets.append((k, bucket))
    payload = json.dumps(buckets, sort_keys=True)
    return hashlib.sha256(payload.encode()).hexdigest()[:16]


def get_cached_insight(
    person_id: str,
    current_signals: dict,
    conn: sqlite3.Connection,
) -> dict | None:
    """Return cached insight if signals haven't changed significantly (TTL: 24h)."""
    sig_hash = signals_hash(current_signals)
    row = conn.execute(
        """
        SELECT insight_response, model, created_at
          FROM signal_snapshots
         WHERE person_id = ? AND signals_hash = ?
           AND datetime(created_at) > datetime('now', '-24 hours')
         ORDER BY created_at DESC LIMIT 1
        """,
        (person_id, sig_hash),
    ).fetchone()
    if not row:
        return None
    try:
        return {
            "response": json.loads(row[0]),
            "model": row[1],
            "created_at": row[2],
        }
    except Exception:
        return None


def save_insight_snapshot(
    person_id: str,
    current_signals: dict,
    insight_data: dict,
    model: str,
    conn: sqlite3.Connection,
) -> None:
    """Save insight snapshot for smart cache lookup."""
    sig_hash = signals_hash(current_signals)
    conn.execute(
        """
        INSERT OR REPLACE INTO signal_snapshots
               (person_id, signals_hash, signals_json,
                insight_response, model, created_at)
               VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            person_id,
            sig_hash,
            json.dumps(current_signals),
            json.dumps(insight_data),
            model,
            datetime.now(timezone.utc).isoformat(),
        ),
    )
    conn.commit()
