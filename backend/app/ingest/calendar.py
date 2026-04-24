import json, os, logging, sqlite3
logger = logging.getLogger(__name__)

def load_calendar(conn: sqlite3.Connection) -> int:
    from app.config import settings
    path = os.path.join(settings.data_dir, "mock_calendar.json")
    if not os.path.exists(path):
        return 0
    with open(path) as f:
        mtgs = json.load(f)
    count = 0
    for m in mtgs:
        mid = m.get("meeting_id", f"M-{count}")
        conn.execute(
            "INSERT OR IGNORE INTO meetings (id, title, datetime, duration_minutes) VALUES (?,?,?,?)",
            (mid, m.get("title","Meeting"), m.get("datetime",""), m.get("duration_minutes",30))
        )
        for pid in m.get("attendees", []):
            conn.execute(
                "INSERT OR IGNORE INTO events (person_id, type, timestamp, payload_json) VALUES (?,?,?,?)",
                (pid, "meeting_attended", m.get("datetime",""), json.dumps({
                    "meeting_id": mid, "talk_ratio": 0.2, "words_spoken": 50,
                    "sentiment": 0.0, "interruptions_given": 0, "interruptions_received": 0
                }))
            )
        count += 1
    conn.commit()
    return count
