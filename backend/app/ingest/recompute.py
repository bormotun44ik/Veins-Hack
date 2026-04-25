"""
recompute.py — cheap overload recompute without LLM (for live ingest).
tone_delta is taken from cached metadata_json to avoid slow LLM call.

WEIGHTS below are synced from signals.composite WEIGHTS.
"""
import json
import logging
import sqlite3

logger = logging.getLogger(__name__)

# synced from signals.composite WEIGHTS
WEIGHTS = {
    "night_commits": 0.20,
    "fix_revert":    0.15,
    "tone_delta":    0.20,
    "pr_lag":        0.10,
    "bus_factor":    0.10,
    "co_isolation":  0.15,
    "weekend":       0.10,
}


def recompute_cheap(person_id: str, conn: sqlite3.Connection) -> dict:
    """
    Compute overload_score without tone_delta LLM call.
    Uses cached tone_delta from people.metadata_json.
    Returns {"old_score", "new_score", "recomputed": list[str]}.
    """
    from app.signals import night_commits, fix_revert, pr_lag, bus_factor, co_isolation, weekend_activity

    row = conn.execute(
        "SELECT overload_score, metadata_json FROM people WHERE id=?", (person_id,)
    ).fetchone()
    old_score = row["overload_score"] if row else 0.0

    # Get cached tone_delta — 0.0 if not available ("no data" semantics)
    meta = {}
    if row and row["metadata_json"]:
        try:
            meta = json.loads(row["metadata_json"])
        except Exception:
            pass
    tone = meta.get("tone_delta_cached", 0.0)

    cheap_signals = {
        "night_commits": night_commits,
        "fix_revert":    fix_revert,
        "pr_lag":        pr_lag,
        "bus_factor":    bus_factor,
        "co_isolation":  co_isolation,
        "weekend":       weekend_activity,
    }

    total = WEIGHTS["tone_delta"] * tone
    recomputed = []

    for name, mod in cheap_signals.items():
        try:
            val = mod.compute(person_id, conn)
            total += WEIGHTS[name] * val
            recomputed.append(name)
        except Exception as e:
            logger.error(f"Signal {name} failed for {person_id}: {e}")

    new_score = max(0.0, min(1.0, total))

    conn.execute(
        "UPDATE people SET overload_score=? WHERE id=?", (new_score, person_id)
    )
    conn.commit()

    return {
        "old_score": old_score,
        "new_score": new_score,
        "recomputed": recomputed,
    }
