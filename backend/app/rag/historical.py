import sqlite3
import logging
from typing import Any

logger = logging.getLogger(__name__)


def get_historical_signals(person_id: str, conn: sqlite3.Connection) -> dict[str, Any]:
    """Возвращает агрегированный snapshot 3-месячной давности.

    Читает таблицу historical_signals (заполняется seed_demo_v2.py из
    data/historical_signals.json).
    """
    row = conn.execute("""
        SELECT night_commits, fix_revert, tone_score,
               co_authors_count, events_count, week_start
          FROM historical_signals
         WHERE person_id = ?
         ORDER BY week_start ASC
         LIMIT 1
    """, (person_id,)).fetchone()
    if not row:
        return {}
    return {
        "night_commits_ratio": row[0] or 0.0,
        "fix_revert_ratio": row[1] or 0.0,
        "tone_score": row[2] or 0.0,
        "co_authors_avg": row[3] or 0,
        "week_start": row[5],
    }


def build_trend_narrative(person_id: str, historical: dict, current: dict,
                           name: str, role: str) -> dict:
    """Простой текстовый rendering для Opus prompt."""
    if not historical:
        return {}

    night_h = historical.get("night_commits_ratio", 0)
    fix_h = historical.get("fix_revert_ratio", 0)
    tone_h = historical.get("tone_score", 0)
    co_h = historical.get("co_authors_avg", 0)

    night_c = current.get("night_commits_ratio", 0)
    fix_c = current.get("fix_revert_ratio", 0)

    baseline = (
        f"{name} 3 months ago: "
        f"{int(night_h*100)}% night commits, "
        f"{int(fix_h*100)}% fix-revert, "
        f"{co_h:.1f} co-authors avg, tone {tone_h:+.1f}"
    )
    current_n = (
        f"{name} now: "
        f"{int(night_c*100)}% night commits, "
        f"{int(fix_c*100)}% fix-revert"
    )
    delta = (
        f"Tone {tone_h:+.1f} → ?, "
        f"night {int(night_h*100)}%→{int(night_c*100)}%, "
        f"fix {int(fix_h*100)}%→{int(fix_c*100)}%"
    )
    return {
        "baseline": baseline,
        "current": current_n,
        "delta_summary": delta,
    }
