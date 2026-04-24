import sqlite3, json, logging
logger = logging.getLogger(__name__)

def compute(person_id: str, conn: sqlite3.Connection) -> float:
    try:
        rows = conn.execute(
            "SELECT payload_json FROM events WHERE person_id=? AND type='review'",
            (person_id,)
        ).fetchall()
        lags = [json.loads(r[0]).get('lag_hours', 0) for r in rows if json.loads(r[0]).get('lag_hours')]
        if not lags:
            return 0.0
        avg = sum(lags) / len(lags)
        return min(1.0, avg / 48.0)
    except Exception as e:
        logger.error(f"pr_lag error: {e}")
        return 0.0
