import sqlite3, logging
logger = logging.getLogger(__name__)

def compute(person_id: str, conn: sqlite3.Connection) -> float:
    try:
        rows = conn.execute(
            "SELECT timestamp FROM events WHERE person_id=? AND type='commit'",
            (person_id,)
        ).fetchall()
        if len(rows) < 5:
            return 0.0
        night = 0
        for r in rows:
            ts = r[0] or ''
            try:
                h = int(ts[11:13])
                if h >= 22 or h < 6:
                    night += 1
            except Exception:
                pass
        ratio = night / len(rows)
        return min(1.0, ratio * 1.5)
    except Exception as e:
        logger.error(f"night_commits error: {e}")
        return 0.0
