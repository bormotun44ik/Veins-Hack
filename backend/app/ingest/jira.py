import json, os, logging, sqlite3
logger = logging.getLogger(__name__)

def load_jira(conn: sqlite3.Connection) -> int:
    from app.config import settings
    path = os.path.join(settings.data_dir, "mock_jira.json")
    if not os.path.exists(path):
        return 0
    with open(path) as f:
        tasks = json.load(f)
    count = 0
    for t in tasks:
        conn.execute(
            "INSERT OR IGNORE INTO tasks (id, title, priority, status, deadline, assignee_id) VALUES (?,?,?,?,?,?)",
            (t.get("id"), t.get("title"), t.get("priority"), t.get("status"),
             t.get("deadline"), t.get("assignee_id"))
        )
        count += 1
    conn.commit()
    return count
