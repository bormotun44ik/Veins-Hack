import json, logging
import sqlite3
logger = logging.getLogger(__name__)

EMAIL_TO_ID = {
    "ivan.petrov@team.dev": "ivan",
    "maria.ivanova@team.dev": "maria",
    "tom.nielsen@team.dev": "tom",
    "anna.kowalska@team.dev": "anna",
    "peter.dimitrov@team.dev": "peter",
}

PEOPLE_DATA = [
    {"id": "ivan", "name": "Ivan Petrov", "role": "Senior Backend Engineer",
     "avatar_url": "https://i.pravatar.cc/150?u=ivan", "baseline_sentiment": 0.1},
    {"id": "maria", "name": "Maria Ivanova", "role": "Tech Lead",
     "avatar_url": "https://i.pravatar.cc/150?u=maria", "baseline_sentiment": 0.6},
    {"id": "tom", "name": "Tom Nielsen", "role": "Backend Engineer",
     "avatar_url": "https://i.pravatar.cc/150?u=tom", "baseline_sentiment": 0.3},
    {"id": "anna", "name": "Anna Kowalska", "role": "Frontend Engineer",
     "avatar_url": "https://i.pravatar.cc/150?u=anna", "baseline_sentiment": 0.5},
    {"id": "peter", "name": "Peter Dimitrov", "role": "QA Engineer",
     "avatar_url": "https://i.pravatar.cc/150?u=peter", "baseline_sentiment": 0.4},
]

def _seed_people(conn: sqlite3.Connection) -> None:
    for p in PEOPLE_DATA:
        conn.execute(
            "INSERT OR IGNORE INTO people (id, name, role, avatar_url, baseline_sentiment) VALUES (?,?,?,?,?)",
            (p["id"], p["name"], p["role"], p["avatar_url"], p["baseline_sentiment"])
        )
    conn.commit()

def pull_github(conn: sqlite3.Connection) -> int:
    from app.config import settings
    _seed_people(conn)

    if settings.use_fake_github:
        return _load_fake(conn)
    return _load_live(conn)

def _load_fake(conn: sqlite3.Connection) -> int:
    import os
    from app.config import settings
    fake_path = os.path.join(settings.data_dir, "samples", "sample_events.jsonl")
    if not os.path.exists(fake_path):
        logger.error(f"sample_events.jsonl not found at {fake_path}")
        return 0
    count = 0
    with open(fake_path) as f:
        for line in f:
            e = json.loads(line.strip())
            conn.execute(
                "INSERT OR IGNORE INTO events (person_id, type, timestamp, payload_json) VALUES (?,?,?,?)",
                (e["person_id"], e["type"], e["timestamp"], json.dumps(e["payload"]))
            )
            count += 1
    conn.commit()
    return count

def _load_live(conn: sqlite3.Connection) -> int:
    from app.config import settings
    try:
        from github import Github
    except ImportError:
        logger.warning("PyGithub not installed, falling back to fake")
        return _load_fake(conn)

    if not settings.github_token:
        logger.warning("No GITHUB_TOKEN, falling back to fake")
        return _load_fake(conn)

    try:
        g = Github(settings.github_token)
        repo = g.get_repo(settings.github_repo)
        count = 0

        # Seed repo
        conn.execute("INSERT OR IGNORE INTO repos (id, name, url) VALUES (?,?,?)",
                     (repo.name, repo.full_name, repo.html_url))

        for commit in repo.get_commits()[:100]:
            author_email = commit.commit.author.email if commit.commit.author else ""
            pid = EMAIL_TO_ID.get(author_email)
            if not pid:
                continue

            files = [f.filename for f in commit.files] if commit.files else []
            payload = {
                "sha": commit.sha[:7],
                "message": commit.commit.message.split('\n')[0][:100],
                "repo_id": repo.name,
                "branch": "main",
                "co_authors": [],
                "additions": commit.stats.additions if commit.stats else 0,
                "deletions": commit.stats.deletions if commit.stats else 0,
                "files_touched": files[:10],
            }
            ts = commit.commit.author.date.isoformat() + "Z" if commit.commit.author else ""
            conn.execute(
                "INSERT OR IGNORE INTO events (person_id, type, timestamp, payload_json) VALUES (?,?,?,?)",
                (pid, "commit", ts, json.dumps(payload))
            )
            count += 1

        conn.commit()
        logger.info(f"Loaded {count} events from GitHub live")
        return count
    except Exception as e:
        logger.error(f"GitHub live failed: {e}, falling back to fake")
        return _load_fake(conn)
