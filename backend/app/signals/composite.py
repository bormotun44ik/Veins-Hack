import sqlite3, logging
logger = logging.getLogger(__name__)

WEIGHTS = {
    "night_commits": 0.20,
    "fix_revert": 0.15,
    "tone_delta": 0.20,
    "pr_lag": 0.10,
    "bus_factor": 0.10,
    "co_isolation": 0.15,
    "weekend": 0.10,
}

def compute_overload(person_id: str, conn: sqlite3.Connection) -> float:
    from app.signals import night_commits, fix_revert, tone_delta, pr_lag, bus_factor, co_isolation, weekend_activity
    signals = {
        "night_commits": night_commits,
        "fix_revert": fix_revert,
        "tone_delta": tone_delta,
        "pr_lag": pr_lag,
        "bus_factor": bus_factor,
        "co_isolation": co_isolation,
        "weekend": weekend_activity,
    }
    total = 0.0
    for name, mod in signals.items():
        try:
            val = mod.compute(person_id, conn)
            total += WEIGHTS[name] * val
        except Exception as e:
            logger.error(f"Signal {name} failed: {e}")
    return max(0.0, min(1.0, total))

def update_all_people(conn: sqlite3.Connection) -> None:
    people = conn.execute("SELECT id FROM people").fetchall()
    for (pid,) in people:
        score = compute_overload(pid, conn)
        conn.execute("UPDATE people SET overload_score=? WHERE id=?", (score, pid))
    conn.commit()
