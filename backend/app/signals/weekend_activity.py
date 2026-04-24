import sqlite3, logging
from datetime import datetime
logger = logging.getLogger(__name__)

def compute(person_id: str, conn: sqlite3.Connection) -> float:
    try:
        rows = conn.execute(
            "SELECT timestamp FROM events WHERE person_id=? AND type='commit'",
            (person_id,)
        ).fetchall()
        if not rows:
            return 0.0
        weekend = sum(1 for r in rows if datetime.fromisoformat(r[0].replace('Z', '+00:00')).weekday() >= 5)
        return min(1.0, (weekend / len(rows)) * 2)
    except Exception as e:
        logger.error(f"weekend_activity error: {e}")
        return 0.0
