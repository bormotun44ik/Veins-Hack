import sqlite3, json, logging
logger = logging.getLogger(__name__)

def compute(person_id: str, conn: sqlite3.Connection) -> float:
    try:
        KEYWORDS = ('fix', 'bug', 'revert', 'hotfix', 'rollback', 'oops')
        rows = conn.execute(
            "SELECT payload_json FROM events WHERE person_id=? AND type='commit'",
            (person_id,)
        ).fetchall()
        if not rows:
            return 0.0
        count = sum(1 for r in rows if any(k in json.loads(r[0]).get('message', '').lower() for k in KEYWORDS))
        ratio = count / len(rows)
        return max(0.0, min(1.0, (ratio - 0.2) / 0.4))
    except Exception as e:
        logger.error(f"fix_revert error: {e}")
        return 0.0
