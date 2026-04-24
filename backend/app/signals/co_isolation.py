import sqlite3, json, logging
logger = logging.getLogger(__name__)

def compute(person_id: str, conn: sqlite3.Connection) -> float:
    try:
        rows = conn.execute(
            "SELECT payload_json FROM events WHERE person_id=? AND type='commit'",
            (person_id,)
        ).fetchall()
        co_authors = set()
        for r in rows:
            co_authors.update(json.loads(r[0]).get('co_authors', []))
        unique = len(co_authors)
        max_expected = 5
        return max(0.0, 1.0 - unique / max_expected)
    except Exception as e:
        logger.error(f"co_isolation error: {e}")
        return 0.0
