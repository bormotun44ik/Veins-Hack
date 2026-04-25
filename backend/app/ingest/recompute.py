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

    tone_delta стратегия:
      - В кэше llm_cache есть commit_tone responses от prewarm — Sonnet sentiment
        per person. Воспроизводим логику tone_delta.compute() БЕЗ live LLM:
        читаем cached responses через cache.get_cached, парсим sentiment,
        sigmoid(baseline - recent).
      - Если в кэше пусто → tone остаётся 0.0 ("no data"), вес теряется.

    Returns {"old_score", "new_score", "recomputed": list[str]}.
    """
    from app.signals import night_commits, fix_revert, pr_lag, bus_factor, co_isolation, weekend_activity

    row = conn.execute(
        "SELECT overload_score FROM people WHERE id=?", (person_id,)
    ).fetchone()
    old_score = row["overload_score"] if row else 0.0

    cheap_signals = {
        "night_commits": night_commits,
        "fix_revert":    fix_revert,
        "pr_lag":        pr_lag,
        "bus_factor":    bus_factor,
        "co_isolation":  co_isolation,
        "weekend":       weekend_activity,
    }

    # Read cached tone_delta result if present (set by composite.update_all_people).
    # Если её нет — tone вкладывается с весом 0 (no signal, не штрафуем человека).
    tone = _get_cached_tone_delta(person_id, conn)

    total = WEIGHTS["tone_delta"] * tone
    recomputed = ["tone_delta(cached)"] if tone > 0 else []

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


def _get_cached_tone_delta(person_id: str, conn: sqlite3.Connection) -> float:
    """Read tone_delta from people.metadata_json.tone_delta_cached.

    Set by composite.update_all_people (full recompute с LLM).
    Если нет → 0.0 ("no data" semantics — синхронизация с heatmap fallback).
    """
    row = conn.execute(
        "SELECT metadata_json FROM people WHERE id=?", (person_id,)
    ).fetchone()
    if not row or not row["metadata_json"]:
        return 0.0
    try:
        meta = json.loads(row["metadata_json"])
        return float(meta.get("tone_delta_cached", 0.0))
    except Exception:
        return 0.0
