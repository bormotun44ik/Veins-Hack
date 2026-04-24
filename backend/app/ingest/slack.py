import json, os, logging, sqlite3
logger = logging.getLogger(__name__)

def load_slack(conn: sqlite3.Connection) -> int:
    from app.config import settings
    path = os.path.join(settings.data_dir, "mock_slack.json")
    if not os.path.exists(path):
        return 0
    with open(path) as f:
        msgs = json.load(f)
    count = 0
    for m in msgs:
        pid = m.get("person_id")
        if not pid:
            continue
        conn.execute(
            "INSERT OR IGNORE INTO events (person_id, type, timestamp, payload_json) VALUES (?,?,?,?)",
            (pid, "slack_msg", m.get("timestamp",""), json.dumps({
                "channel": m.get("channel","team-general"),
                "text": m.get("text",""),
                "reply_to": None, "thread_root": None, "mentions": [], "sentiment": None
            }))
        )
        count += 1
    conn.commit()
    return count
