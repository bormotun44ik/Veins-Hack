import sqlite3, json, logging
logger = logging.getLogger(__name__)

def compute(person_id: str, conn: sqlite3.Connection) -> float:
    try:
        rows = conn.execute(
            "SELECT payload_json FROM events WHERE type='commit'"
        ).fetchall()
        file_owners: dict = {}  # file -> set of person_ids
        for r in rows:
            p = json.loads(r[0])
            pid = p.get('person_id') or ''
            for f in p.get('files_touched', []):
                file_owners.setdefault(f, set()).add(pid)

        person_rows = conn.execute(
            "SELECT payload_json FROM events WHERE person_id=? AND type='commit'",
            (person_id,)
        ).fetchall()
        touched = set()
        for r in person_rows:
            touched.update(json.loads(r[0]).get('files_touched', []))
        if not touched:
            return 0.0
        owned = sum(1 for f in touched if len(file_owners.get(f, set())) == 1)
        return owned / len(touched)
    except Exception as e:
        logger.error(f"bus_factor error: {e}")
        return 0.0
